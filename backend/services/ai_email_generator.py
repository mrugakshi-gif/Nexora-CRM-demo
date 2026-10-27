import json
import logging
import re
import time
from langchain_core.messages import SystemMessage, HumanMessage
from ..ai_agent import get_llm, is_transient_error

logger = logging.getLogger(__name__)


class AIProviderUnavailableError(Exception):
    """Raised when the AI provider is temporarily unavailable (e.g., 503 high demand / rate limits)."""
    pass


class AIProviderConfigError(Exception):
    """Raised when the AI provider is not configured or API key is missing."""
    pass


class AIEmailGenerator:
    def __init__(self):
        pass

    def generate_email(
        self,
        alert_type: str,
        context: dict,
        recipient_name: str = None,
        max_retries: int = 2,
        retry_delay: float = 1.0
    ) -> dict:
        """
        Generates an email draft using Gemini based on structured context.
        Returns a dict with 'subject', 'text_body', and 'html_body'.
        Implements bounded retry with backoff for transient upstream errors.
        """
        llm = get_llm()
        if not llm:
            raise AIProviderConfigError("LLM is not configured or unavailable.")

        system_prompt = (
            "You are a professional enterprise CRM AI assistant. Your task is to generate a concise, "
            "professional email draft based strictly on the provided context.\n"
            "CRITICAL RULES:\n"
            "1. Output valid JSON only, with exactly three keys: 'subject', 'text_body', and 'html_body'.\n"
            "2. Never invent names, values, dates, reasons, recommendations, or CRM facts.\n"
            "3. Use only the supplied CRM/ML context.\n"
            "4. Be concise and professional.\n"
            "5. Clearly avoid claiming an action happened unless the supplied context confirms it.\n"
            "6. The 'html_body' should use basic HTML tags like <p>, <b>, <ul>, etc."
        )

        user_content = f"Alert Type: {alert_type}\n"
        if recipient_name:
            user_content += f"Recipient Name: {recipient_name}\n"
        user_content += f"Context: {json.dumps(context, indent=2)}\n"

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_content)
        ]

        response = None
        for attempt in range(max_retries + 1):
            try:
                response = llm.invoke(messages)
                break
            except Exception as e:
                if is_transient_error(e):
                    if attempt < max_retries:
                        backoff = retry_delay * (attempt + 1)
                        logger.warning(
                            "Transient AI provider error on attempt %d/%d (%s). Retrying in %.1fs...",
                            attempt + 1, max_retries + 1, e, backoff
                        )
                        time.sleep(backoff)
                        continue
                    else:
                        logger.error("AI provider unavailable after %d attempts: %s", max_retries + 1, e)
                        raise AIProviderUnavailableError(
                            "The AI model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again in a moment."
                        ) from e
                # Non-transient error: do not retry
                raise Exception(f"Failed to generate email content: {e}") from e

        try:
            raw_content = response.content
            if isinstance(raw_content, list):
                parts = []
                for block in raw_content:
                    if isinstance(block, dict) and "text" in block:
                        parts.append(block["text"])
                    elif isinstance(block, str):
                        parts.append(block)
                content = " ".join(parts).strip() if parts else str(raw_content)
            else:
                content = str(raw_content).strip()

            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            try:
                parsed = json.loads(content)
            except json.JSONDecodeError as e:
                match = re.search(r'\{.*\}', content, re.DOTALL)
                if match:
                    try:
                        parsed = json.loads(match.group(0))
                    except Exception:
                        raise Exception(f"Failed to parse JSON: {e}. Raw content: {content}")
                else:
                    raise Exception(f"Failed to parse JSON: {e}. Raw content: {content}")

            return {
                "subject": parsed.get("subject", "Automated Alert"),
                "text_body": parsed.get("text_body", ""),
                "html_body": parsed.get("html_body", "")
            }
        except Exception as e:
            if isinstance(e, (AIProviderUnavailableError, AIProviderConfigError)):
                raise
            raise Exception(f"Failed to parse generated email content: {e}") from e
