from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import Tool, StructuredTool
from sqlalchemy.orm import Session
import os

from .ai_tools import CrmTools, get_ml_tools
from .rag import get_rag_retriever

def check_llm_health() -> dict:
    """Check health of Google Gemini LLM."""
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return {"configured": False, "status": "unavailable", "message": "GOOGLE_API_KEY missing"}

    try:
        model_name = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite")
        llm = ChatGoogleGenerativeAI(model=model_name, temperature=0, max_retries=3, timeout=60)
        return {"configured": True, "status": "available", "message": "LLM initialized"}
    except Exception as e:
        return {"configured": True, "status": "error", "message": str(e)}

_llm_cache = None

def reset_llm_cache():
    """Resets the cached LLM instance."""
    global _llm_cache
    _llm_cache = None

def get_llm():
    """Initializes the LLM if API key is present."""
    global _llm_cache
    if _llm_cache is not None:
        return _llm_cache

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("Warning: GOOGLE_API_KEY is not set. Google GenAI will not be available.")
        return None
    try:
        # Use configured Gemini model (defaults to gemini-3.1-flash-lite)
        model_name = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite")
        _llm_cache = ChatGoogleGenerativeAI(model=model_name, temperature=0, max_retries=3, timeout=60)
        return _llm_cache
    except Exception as e:
        print(f"Warning: Could not initialize Google GenAI. Error: {e}")
        return None

def is_transient_error(e: Exception) -> bool:
    """Check if an exception represents a transient upstream availability or capacity error."""
    code = getattr(e, "code", None)
    if code in (503, 429):
        return True
    status = str(getattr(e, "status", "")).upper()
    if status in ("UNAVAILABLE", "RESOURCE_EXHAUSTED"):
        return True
    if getattr(e, "is_retryable", False):
        return True

    err_msg = str(e).lower()
    transient_indicators = [
        "503",
        "unavailable",
        "high demand",
        "spikes in demand",
        "temporarily",
        "resource exhausted",
        "resourceexhausted",
        "429",
        "rate limit",
        "too many requests",
        "overloaded",
    ]
    return any(indicator in err_msg for indicator in transient_indicators)

def get_authorized_company_ids(session: Session, user_id: str, role: str):
    """Determines which companies a user is allowed to access."""
    if role in ["Admin", "System Admin", "Manager", "Sales Manager"]:
        return None  # None signifies no filter (all companies allowed)

    from . import models
    user = session.query(models.User).filter(models.User.user_id == user_id).first()
    rep_id = user.rep_id if user else None

    # Find companies tied to the user via their activities
    activities = session.query(models.Activity).filter(models.Activity.sales_rep_id == rep_id).all() if rep_id else []
    company_ids = {a.company_id for a in activities if a.company_id}

    # Optionally, check documents they uploaded
    docs = session.query(models.CompanyDocument).filter(models.CompanyDocument.uploaded_by == user_id).all()
    company_ids.update({d.company_id for d in docs if d.company_id})

    return list(company_ids) if company_ids else ["NO_ACCESS_DUMMY_ID"]

def process_chat_query(query: str, session: Session, user_id: str, role: str, chat_session_id: str = None) -> str:
    """
    Processes a user query by routing it through the LLM with access to CRM tools,
    ML prediction tools, and RAG.

    IMPORTANT: This function creates its own dedicated database session for all AI
    tool operations. The caller's `session` is only used for reading chat history
    (which is already committed and safe to read). This isolation prevents
    sqlite3.InterfaceError: bad parameter or other API misuse, which occurs when
    the HTTP handler's committed session is shared with LangGraph's tool execution
    context across different connection states.
    """
    from .database import SessionLocal

    llm = get_llm()

    if not llm:
        return "I am unable to process your request at this time. The AI model is not configured properly."

    # Read chat history from the caller's session (read-only, already committed — safe)
    history_messages = []
    if chat_session_id:
        from . import models
        db_messages = session.query(models.ChatMessage).filter(
            models.ChatMessage.session_id == chat_session_id
        ).order_by(models.ChatMessage.created_at.asc()).all()[-20:]
        for msg in db_messages:
            history_messages.append({"role": msg.role, "content": msg.content})
    if not history_messages:
        history_messages = [{"role": "user", "content": query}]

    # Open a DEDICATED session for all AI tool database access.
    # This session is completely independent from the HTTP handler's session,
    # eliminating cross-context SQLite connection state corruption.
    ai_db = SessionLocal()
    try:
        # 1. Initialize CRM Tools with the dedicated AI session
        crm_tools = CrmTools(user_id, role)

        # 2. Get RAG Retriever Tool with Authorization
        allowed_company_ids = get_authorized_company_ids(ai_db, user_id, role)

        if isinstance(allowed_company_ids, list):
            allowed_company_ids.append("general")
        retriever = get_rag_retriever(company_ids=allowed_company_ids)

        _rag_cache = {}
        def rag_search(query_str: str) -> str:
            if query_str in _rag_cache:
                return _rag_cache[query_str]

            if not retriever:
                return "I cannot find this information in the company documents. RAG is not initialized."
            docs = retriever.invoke(query_str)
            if not docs:
                res = "I cannot find this information in the company documents."
                _rag_cache[query_str] = res
                return res
            result = ""
            for d in docs:
                result += f"[Source: Document {d.metadata.get('source', 'Unknown')}, Chunk {d.metadata.get('chunk', '?')}]\n"
                result += f"{d.page_content}\n\n"

            _rag_cache[query_str] = result
            return result

        # 3. Define all tools (all closures capture ai_db, not the handler session)
        ml_tools = get_ml_tools(user_id, role)
        crm_tools_list = [
            StructuredTool.from_function(
                name="GetLeads",
                func=crm_tools.get_leads,
                description="Fetch leads. Optionally provide status, limit, sort_field ('created_at', 'estimated_budget_inr'), and sort_dir.",
            ),
            StructuredTool.from_function(
                name="GetActivities",
                func=crm_tools.get_activities,
                description="Fetch activities. Optionally provide status, priority, limit, sort_field ('activity_date', 'due_date', 'created_at'), and sort_dir.",
            ),
            StructuredTool.from_function(
                name="GetCompanies",
                func=crm_tools.get_companies,
                description="Fetch companies. Optionally provide industry_id, limit, sort_field ('created_at', 'updated_at', 'company_name'), and sort_dir.",
            ),
            StructuredTool.from_function(
                name="GetContacts",
                func=crm_tools.get_contacts,
                description="Fetch contacts. Optionally provide company_id, limit, sort_field ('created_at', 'full_name'), and sort_dir.",
            ),
            StructuredTool.from_function(
                name="GetOpportunities",
                func=crm_tools.get_opportunities,
                description="Fetch opportunities. Optionally provide stage, limit, sort_field ('deal_value_inr', 'probability_pct', 'expected_close_date', 'created_at'), and sort_dir.",
            ),
            StructuredTool.from_function(
                name="GetCustomers",
                func=crm_tools.get_customers,
                description="Fetch customers. Optionally provide filters, limit, sort_field ('customer_since', 'created_at'), and sort_dir.",
            ),
            StructuredTool.from_function(
                name="GetTransactions",
                func=crm_tools.get_transactions,
                description="Fetch transactions. Optionally provide filters, limit, sort_field ('transaction_date', 'amount_inr'), and sort_dir.",
            ),
            StructuredTool.from_function(
                name="GetSupportCases",
                func=crm_tools.get_support_cases,
                description="Fetch support cases. Optionally provide filters, limit, sort_field ('opened_at', 'satisfaction_score'), and sort_dir.",
            ),
            StructuredTool.from_function(
                name="GetCustomerRevenue",
                func=crm_tools.get_customer_revenue,
                description="Fetch top customers aggregated by their total revenue (from paid transactions). Useful for 'top customers by revenue'.",
            ),
            StructuredTool.from_function(
                name="GetProductRevenue",
                func=crm_tools.get_product_revenue,
                description="Fetch top products aggregated by their total revenue (from closed-won opportunities) and units sold. Useful for 'top products' or 'product revenue'.",
            ),
        ]
        rag_tool = Tool(
            name="CompanyDocumentSearch",
            func=rag_search,
            description=(
                "Search company documents for relevant information. "
                "If results are not relevant, do NOT keep rephrasing/searching indefinitely. "
                "Allow at most ONE alternative search query for the same user question. "
                "After that, use the available evidence and explicitly state when the requested information was not found."
            ),
        )

        import re
        lower_query = query.strip().lower()

        # 1. Deterministic Fast Path for Greetings
        greetings_regex = r'^(hi|hello|hey|greetings|good morning|good afternoon|good evening|how are you|who are you|what can you do|help)\s*[.!?]*$'
        is_greeting = bool(re.match(greetings_regex, lower_query))

        # 2. Intent-based Routing
        needs_ml = bool(re.search(r'\b(predict|score|churn|convert|conversion|segment|segmentation|forecast|forecasting|top leads?|risk)\b', lower_query))
        needs_rag = bool(re.search(r'\b(document|docs?|knowledge|policy|handbook|guidelines?|manual|about the company)\b', lower_query))
        needs_crm = bool(re.search(r'\b(leads?|customers?|contacts?|activit(y|ies)|compan(y|ies)|opportunit(y|ies)|transactions?|revenue|support|cases?|pipeline|won|lost)\b', lower_query))

        # Determine tools to bind based on query intent
        if is_greeting:
            tools = []
        else:
            intents_matched = sum([needs_ml, needs_rag, needs_crm])
            if intents_matched == 1:
                if needs_ml:
                    tools = ml_tools + crm_tools_list  # ML might need CRM retrieval first
                elif needs_rag:
                    tools = [rag_tool]
                elif needs_crm:
                    tools = crm_tools_list
            else:
                # Fallback to full agent
                tools = crm_tools_list + ml_tools + [rag_tool]

        system_prompt = (
            "You are an AI-Powered Enterprise CRM Assistant. "
            "You have access to structured CRM data, experimental ML models, and unstructured company documents. "
            "CRITICAL RULES: "
            "1. Never invent or fabricate information. If a tool returns no data, explicitly state 'I cannot find this information'. "
            "2. Always append the source attribution provided by the tools (e.g., [Source: CRM Leads Table], [Source: Document X]). "
            "3. You must use the tools to answer questions. Do not guess. "
            "4. If a query is ambiguous, such as asking for 'top customers' without specifying a metric, do NOT guess a metric or invent a tier ranking. You MUST ask for clarification: 'Do you mean top customers by revenue, transaction value, opportunities, or another metric?'\n"
            "5. For document searches, make the initial search. If the result is insufficient, ONE alternative search is allowed. "
            "Never perform more than 2 CompanyDocumentSearch calls for one user question. "
            "If the requested information is still not found, say so clearly rather than continuing to search or guessing. "
            "Never fabricate missing information.\n"
            "6. When summarizing or listing retrieved records subject to a limit, do NOT claim that this limit is the global total count in the system (e.g., do not say 'There are currently 50 Closed Won opportunities'). Instead, clearly phrase it as 'Here are the [limit] most recent opportunities'. For queries asking for 'recent' items, ALWAYS set sort_field='created_at' and sort_dir='desc'."
        )

        # 5. Execute Agent with bounded retry for transient upstream errors
        from langchain.agents import create_agent
        import time

        agent = create_agent(model=llm, tools=tools, system_prompt=system_prompt)

        max_chat_retries = 2
        retry_delay = 1.0
        response = None
        for attempt in range(max_chat_retries + 1):
            try:
                response = agent.invoke({"messages": history_messages})
                break
            except Exception as e:
                if is_transient_error(e):
                    if attempt < max_chat_retries:
                        backoff = retry_delay * (attempt + 1)
                        time.sleep(backoff)
                        continue
                    else:
                        return "The AI assistant is temporarily unavailable due to high demand. Spikes in demand are usually temporary. Please try again in a moment."
                raise

        # Grab the final string from the agent response
        if "messages" in response and len(response["messages"]) > 0:
            final_content = response["messages"][-1].content
            # New Gemini SDK may return structured content blocks (list of dicts)
            # instead of a plain string — extract the text.
            if isinstance(final_content, list):
                parts = []
                for block in final_content:
                    if isinstance(block, dict) and "text" in block:
                        parts.append(block["text"])
                    elif isinstance(block, str):
                        parts.append(block)
                return " ".join(parts).strip() if parts else str(final_content)
            return str(final_content)
        return str(response)

    except Exception as e:
        if is_transient_error(e):
            return "The AI assistant is temporarily unavailable due to high demand. Spikes in demand are usually temporary. Please try again in a moment."
        return "An error occurred while processing your request. Please try again."
    finally:
        # Always close the dedicated AI session, regardless of success or failure
        ai_db.close()
