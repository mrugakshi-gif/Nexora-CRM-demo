import pandas as pd
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from .database import SessionLocal
from langchain_core.tools import tool
import joblib
import os

from . import models

# Paths to ML models (adjust as needed based on actual structure)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, "ml_models", "models")

class CrmTools:
    def __init__(self, user_id: str, role: str):
        self.user_id = user_id
        self.role = role
        with SessionLocal() as session:
            user = session.query(models.User).filter(models.User.user_id == user_id).first()
            self.rep_id = user.rep_id if user else None

    def _apply_role_filter(self, session, query, model, rep_field: str = "assigned_rep_id"):
        # If Admin or Manager, they can see all. Otherwise, restrict to the rep's ID.
        if self.role not in ["Admin", "Manager", "Sales Manager", "System Admin"]:
            if self.rep_id:
                query = query.filter(getattr(model, rep_field) == self.rep_id)
            else:
                # If they have no rep_id but are not an admin/manager, they should see nothing
                query = query.filter(getattr(model, rep_field) == "NO_REP_ID_DUMMY")
        return query

    def _apply_sorting_and_limit(self, query, model, limit, sort_field, sort_dir, allowed_fields):
        try:
            limit_val = int(limit) if limit else 50
            limit_val = min(limit_val, 50)
        except (ValueError, TypeError):
            limit_val = 50

        if sort_field and sort_field in allowed_fields:
            column = getattr(model, sort_field, None)
            if column is not None:
                if sort_dir and sort_dir.lower() == "asc":
                    query = query.order_by(column.asc())
                else:
                    query = query.order_by(column.desc())
        
        return query.limit(limit_val)


    def get_leads(self, status: Optional[str] = None, limit: Optional[int] = 50, sort_field: Optional[str] = None, sort_dir: Optional[str] = "desc") -> str:
        """
        Fetch leads from the CRM database.
        Optionally filter by lead status (e.g., 'New', 'Qualified', 'Negotiation').
        Returns a JSON-formatted string of leads with source attribution.
        """
        if status in ("{}", "None", "null", ""):
            status = None

        with SessionLocal() as session:
            query = session.query(models.Lead)
            query = self._apply_role_filter(session, query, models.Lead, "assigned_rep_id")

            if status:
                query = query.filter(models.Lead.lead_status == status)

            allowed = {"created_at", "estimated_budget_inr", "first_contacted_at"}
            query = self._apply_sorting_and_limit(query, models.Lead, limit, sort_field, sort_dir, allowed)
            leads = query.all()
            if not leads:
                return "I cannot find this information in the CRM or company documents."

            results = [
                {"id": l.lead_id, "company_id": l.company_id, "status": l.lead_status, "rep_id": l.assigned_rep_id}
                for l in leads
            ]
            return f"[Source: CRM Leads Table]\n{results}"

    def get_activities(self, status: Optional[str] = None, priority: Optional[str] = None, limit: Optional[int] = 50, sort_field: Optional[str] = None, sort_dir: Optional[str] = "desc") -> str:
        """
        Fetch activities (Tasks, Calls, Meetings) from the CRM database.
        Optionally filter by status (e.g., 'Completed', 'Pending') or priority (e.g., 'High', 'Medium').
        Returns a JSON-formatted string of activities with source attribution.
        """
        with SessionLocal() as session:
            query = session.query(models.Activity)
            query = self._apply_role_filter(session, query, models.Activity, "sales_rep_id")

            if status:
                query = query.filter(models.Activity.status == status)
            if priority:
                query = query.filter(models.Activity.priority == priority)

            allowed = {"activity_date", "due_date", "created_at"}
            query = self._apply_sorting_and_limit(query, models.Activity, limit, sort_field, sort_dir, allowed)
            activities = query.all()
            if not activities:
                return "I cannot find this information in the CRM or company documents."

            results = [
                {"id": a.activity_id, "type": a.activity_type, "subject": a.subject, "status": a.status, "priority": a.priority}
                for a in activities
            ]
            return f"[Source: CRM Activities Table]\n{results}"

    def get_companies(self, industry_id: Optional[str] = None, limit: Optional[int] = 50, sort_field: Optional[str] = None, sort_dir: Optional[str] = "desc") -> str:
        """
        Fetch companies from the CRM database.
        Optionally filter by industry_id.
        """
        if industry_id in ("{}", "None", "null", ""):
            industry_id = None
            
        with SessionLocal() as session:
            query = session.query(models.Company)
            if industry_id:
                query = query.filter(models.Company.industry_id == industry_id)

            allowed = {"created_at", "updated_at", "company_name", "founded_year"}
            query = self._apply_sorting_and_limit(query, models.Company, limit, sort_field, sort_dir, allowed)
            companies = query.all()
            if not companies:
                return "I cannot find this information in the CRM or company documents."

            results = [
                {"id": c.company_id, "name": c.company_name, "industry": c.industry_id, "status": c.account_status}
                for c in companies
            ]
            return f"[Source: CRM Companies Table]\n{results}"

    def get_contacts(self, company_id: Optional[str] = None, limit: Optional[int] = 50, sort_field: Optional[str] = None, sort_dir: Optional[str] = "desc") -> str:
        """
        Fetch contacts from the CRM database.
        Optionally filter by company_id.
        """
        with SessionLocal() as session:
            query = session.query(models.Contact)
            if company_id:
                query = query.filter(models.Contact.company_id == company_id)

            allowed = {"created_at", "full_name"}
            query = self._apply_sorting_and_limit(query, models.Contact, limit, sort_field, sort_dir, allowed)
            contacts = query.all()
            if not contacts:
                return "I cannot find this information in the CRM or company documents."

            results = [
                {"id": c.contact_id, "name": c.full_name, "email": c.email, "company_id": c.company_id}
                for c in contacts
            ]
            return f"[Source: CRM Contacts Table]\n{results}"

    def get_opportunities(self, stage: Optional[str] = None, limit: Optional[int] = 50, sort_field: Optional[str] = None, sort_dir: Optional[str] = "desc") -> str:
        """
        Fetch opportunities from the CRM database.
        Optionally filter by pipeline_stage.
        """
        if stage in ("{}", "None", "null", ""):
            stage = None
            
        if stage:
            s_lower = stage.lower()
            if "won" in s_lower:
                stage = "Closed Won"
            elif "lost" in s_lower:
                stage = "Closed Lost"

        with SessionLocal() as session:
            query = session.query(models.Opportunity)
            query = self._apply_role_filter(session, query, models.Opportunity, "owner_rep_id")

            if stage:
                query = query.filter(models.Opportunity.pipeline_stage == stage)

            allowed = {"deal_value_inr", "probability_pct", "expected_close_date", "created_at"}
            query = self._apply_sorting_and_limit(query, models.Opportunity, limit, sort_field, sort_dir, allowed)
            opportunities = query.all()
            if not opportunities:
                return "I cannot find this information in the CRM or company documents."

            results = [
                {"id": o.opportunity_id, "stage": o.pipeline_stage, "value": o.deal_value_inr, "prob": o.probability_pct, "owner_id": o.owner_rep_id}
                for o in opportunities
            ]
            return f"[Source: CRM Opportunities Table]\n{results}"

    def get_customers(self, customer_id: Optional[str] = None, company_id: Optional[str] = None, customer_status: Optional[str] = None, customer_tier: Optional[str] = None, contract_type: Optional[str] = None, csm_rep_id: Optional[str] = None, limit: Optional[int] = 50, sort_field: Optional[str] = None, sort_dir: Optional[str] = "desc") -> str:
        """Fetch customers from the CRM database."""
        with SessionLocal() as session:
            query = session.query(models.Customer)
            query = self._apply_role_filter(session, query, models.Customer, "csm_rep_id")

            if customer_id:
                query = query.filter(models.Customer.customer_id == customer_id)
            if company_id:
                query = query.filter(models.Customer.company_id == company_id)
            if customer_status:
                query = query.filter(models.Customer.customer_status == customer_status)
            if customer_tier:
                query = query.filter(models.Customer.customer_tier == customer_tier)
            if contract_type:
                query = query.filter(models.Customer.contract_type == contract_type)
            if csm_rep_id:
                query = query.filter(models.Customer.csm_rep_id == csm_rep_id)

            allowed = {"customer_since", "created_at"}
            query = self._apply_sorting_and_limit(query, models.Customer, limit, sort_field, sort_dir, allowed)
            customers = query.all()
            if not customers:
                return "I cannot find this information in the CRM or company documents."

            results = [
                {"id": c.customer_id, "company_id": c.company_id, "status": c.customer_status, "tier": c.customer_tier, "contract": c.contract_type, "csm_rep": c.csm_rep_id, "renewal_date": c.renewal_date, "source": f"[Source: CRM Customers Record ID: {c.customer_id}]"}
                for c in customers
            ]
            return f"[Source: CRM Customers Table]\n{results}"

    def get_transactions(self, transaction_id: Optional[str] = None, customer_id: Optional[str] = None, opportunity_id: Optional[str] = None, transaction_type: Optional[str] = None, payment_status: Optional[str] = None, limit: Optional[int] = 50, sort_field: Optional[str] = None, sort_dir: Optional[str] = "desc") -> str:
        """Fetch transactions from the CRM database."""
        with SessionLocal() as session:
            query = session.query(models.CustomerTransaction).join(models.Customer, models.CustomerTransaction.customer_id == models.Customer.customer_id)
            query = self._apply_role_filter(session, query, models.Customer, "csm_rep_id")

            if transaction_id:
                query = query.filter(models.CustomerTransaction.transaction_id == transaction_id)
            if customer_id:
                query = query.filter(models.CustomerTransaction.customer_id == customer_id)
            if opportunity_id:
                query = query.filter(models.CustomerTransaction.opportunity_id == opportunity_id)
            if transaction_type:
                query = query.filter(models.CustomerTransaction.transaction_type == transaction_type)
            if payment_status:
                query = query.filter(models.CustomerTransaction.payment_status == payment_status)

            allowed = {"transaction_date", "amount_inr"}
            query = self._apply_sorting_and_limit(query, models.CustomerTransaction, limit, sort_field, sort_dir, allowed)
            transactions = query.all()
            if not transactions:
                return "I cannot find this information in the CRM or company documents."

            results = [
                {"id": t.transaction_id, "customer_id": t.customer_id, "opportunity_id": t.opportunity_id, "date": t.transaction_date, "type": t.transaction_type, "amount": t.amount_inr, "status": t.payment_status, "source": f"[Source: CRM CustomerTransactions Record ID: {t.transaction_id}]"}
                for t in transactions
            ]
            return f"[Source: CRM CustomerTransactions Table]\n{results}"

    def get_support_cases(self, case_id: Optional[str] = None, customer_id: Optional[str] = None, contact_id: Optional[str] = None, case_type: Optional[str] = None, priority: Optional[str] = None, status: Optional[str] = None, limit: Optional[int] = 50, sort_field: Optional[str] = None, sort_dir: Optional[str] = "desc") -> str:
        """Fetch support cases from the CRM database."""
        with SessionLocal() as session:
            query = session.query(models.SupportCase).join(models.Customer, models.SupportCase.customer_id == models.Customer.customer_id)
            query = self._apply_role_filter(session, query, models.Customer, "csm_rep_id")

            if case_id:
                query = query.filter(models.SupportCase.case_id == case_id)
            if customer_id:
                query = query.filter(models.SupportCase.customer_id == customer_id)
            if contact_id:
                query = query.filter(models.SupportCase.contact_id == contact_id)
            if case_type:
                query = query.filter(models.SupportCase.case_type == case_type)
            if priority:
                query = query.filter(models.SupportCase.priority == priority)
            if status:
                query = query.filter(models.SupportCase.status == status)

            allowed = {"opened_at", "satisfaction_score"}
            query = self._apply_sorting_and_limit(query, models.SupportCase, limit, sort_field, sort_dir, allowed)
            cases = query.all()
            if not cases:
                return "I cannot find this information in the CRM or company documents."

            results = [
                {"id": c.case_id, "customer_id": c.customer_id, "contact_id": c.contact_id, "type": c.case_type, "priority": c.priority, "status": c.status, "opened_at": c.opened_at, "resolved_at": c.resolved_at, "source": f"[Source: CRM SupportCases Record ID: {c.case_id}]"}
                for c in cases
            ]
            return f"[Source: CRM SupportCases Table]\n{results}"



    def get_customer_revenue(self, dummy: Optional[str] = None) -> str:
        """Fetch customers aggregated by revenue (paid transaction amount)."""
        from sqlalchemy import func
        with SessionLocal() as session:
            # Note: _apply_role_filter expects a model; here we filter Customer
            query = session.query(
                models.Customer.customer_id,
                models.Company.company_name,
                func.sum(models.CustomerTransaction.amount_inr).label("revenue"),
                func.count(models.CustomerTransaction.transaction_id).label("tx_count")
            ).join(
                models.CustomerTransaction, models.Customer.customer_id == models.CustomerTransaction.customer_id
            ).join(
                models.Company, models.Customer.company_id == models.Company.company_id
            )
            
            # Optionally apply role filtering on the customer
            if self.role not in ["Admin", "Manager", "Sales Manager", "System Admin"]:
                if self.rep_id:
                    query = query.filter(models.Customer.csm_rep_id == self.rep_id)
                else:
                    query = query.filter(models.Customer.csm_rep_id == "NO_REP_ID_DUMMY")

            # Only count paid or successful transactions as revenue
            query = query.filter(models.CustomerTransaction.payment_status == "Paid")
            
            results = query.group_by(
                models.Customer.customer_id, models.Company.company_name
            ).order_by(func.sum(models.CustomerTransaction.amount_inr).desc()).limit(10).all()
            
            if not results:
                return "I cannot find this information in the CRM."
                
            formatted = [
                {"customer_id": r.customer_id, "company_name": r.company_name, "revenue": r.revenue, "transaction_count": r.tx_count, "source": "[Source: CustomerTransactions]"}
                for r in results
            ]
            return f"[Source: CRM CustomerTransactions Table]\n{formatted}"

    def get_product_revenue(self, dummy: Optional[str] = None) -> str:
        """Fetch products aggregated by revenue (from closed-won opportunities) and units sold."""
        from sqlalchemy import func
        with SessionLocal() as session:
            query = session.query(
                models.Product.product_name,
                func.sum(models.OpportunityProduct.line_total_inr).label("revenue"),
                func.sum(models.OpportunityProduct.quantity).label("units")
            ).join(
                models.OpportunityProduct, models.Product.product_id == models.OpportunityProduct.product_id
            ).join(
                models.Opportunity, models.OpportunityProduct.opportunity_id == models.Opportunity.opportunity_id
            ).filter(
                models.Opportunity.pipeline_stage == "Closed Won"
            )
            
            # Apply role filtering on the opportunity
            if self.role not in ["Admin", "Manager", "Sales Manager", "System Admin"]:
                if self.rep_id:
                    query = query.filter(models.Opportunity.owner_rep_id == self.rep_id)
                else:
                    query = query.filter(models.Opportunity.owner_rep_id == "NO_REP_ID_DUMMY")

            results = query.group_by(
                models.Product.product_name
            ).order_by(func.sum(models.OpportunityProduct.line_total_inr).desc()).limit(10).all()
            
            if not results:
                return "I cannot find this information in the CRM."
                
            formatted = [
                {"product_name": r.product_name, "revenue": r.revenue, "units": r.units, "source": "[Source: OpportunityProducts]"}
                for r in results
            ]
            return f"[Source: CRM OpportunityProducts Table]\n{formatted}"


# ML Tools (designed to be bound to LangChain)

def get_ml_tools(user_id: str, role: str) -> list:
    """Factory to generate ML tools equipped with request-scoped DB session and auth context."""
    crm_tools = CrmTools(user_id, role)

    def _check_lead_auth(session, lead_id: str):
        query = session.query(models.Lead).filter(models.Lead.lead_id == lead_id)
        # Apply same role filter as CRM list_leads
        query = crm_tools._apply_role_filter(session, query, models.Lead, "assigned_rep_id")
        return query.first()

    def _check_customer_auth(session, customer_id: str):
        query = session.query(models.Customer).filter(models.Customer.customer_id == customer_id)
        # Apply same role filter as CRM customers
        query = crm_tools._apply_role_filter(session, query, models.Customer, "csm_rep_id")
        return query.first()

    @tool
    def predict_lead_score(lead_id: str) -> str:
        """
        Predicts the lead score for a given lead ID.
        Use this when asked about the score, quality, or rating of a specific lead.
        """
        with SessionLocal() as session:
            if not _check_lead_auth(session, lead_id):
                return "{\"status\": \"error\", \"message\": \"Unauthorized or lead not found. You do not have access to this lead.\"}"
            try:
                from .ml.prediction import prediction_service
                res = prediction_service.predict_lead_scoring(session, lead_id)
                return res.model_dump_json()
            except Exception as e:
                return f"{{\"status\": \"error\", \"message\": \"Lead score prediction is currently unavailable: {e}\"}}"

    @tool
    def predict_churn(customer_id: str) -> str:
        """
        Predicts the likelihood of customer churn for a given customer ID.
        Use this when asked if a customer is at risk of leaving or churning.
        """
        with SessionLocal() as session:
            if not _check_customer_auth(session, customer_id):
                return "{\"status\": \"error\", \"message\": \"Unauthorized or customer not found. You do not have access to this customer.\"}"
            try:
                from .ml.prediction import prediction_service
                res = prediction_service.predict_customer_churn(session, customer_id)
                return res.model_dump_json()
            except Exception as e:
                return f"{{\"status\": \"error\", \"message\": \"Churn prediction is currently unavailable: {e}\"}}"

    @tool
    def predict_lead_conversion(lead_id: str) -> str:
        """
        Predicts if a lead will convert into an opportunity.
        Use this when asked about conversion probability or likelihood to convert.
        """
        with SessionLocal() as session:
            if not _check_lead_auth(session, lead_id):
                return "{\"status\": \"error\", \"message\": \"Unauthorized or lead not found. You do not have access to this lead.\"}"
            try:
                from .ml.prediction import prediction_service
                res = prediction_service.predict_lead_conversion(session, lead_id)
                return res.model_dump_json()
            except Exception as e:
                return f"{{\"status\": \"error\", \"message\": \"Lead conversion prediction is currently unavailable: {e}\"}}"

    @tool
    def customer_segmentation(customer_id: str) -> str:
        """
        Retrieves the customer segment cluster assignment for a company.
        Use this when asked which group, segment, or cluster a customer belongs to.
        """
        with SessionLocal() as session:
            if not _check_customer_auth(session, customer_id):
                return "{\"status\": \"error\", \"message\": \"Unauthorized or customer not found. You do not have access to this customer.\"}"
            try:
                from .ml.prediction import prediction_service
                res = prediction_service.predict_customer_segmentation(session, customer_id)
                return res.model_dump_json()
            except Exception as e:
                return f"{{\"status\": \"error\", \"message\": \"Segmentation is currently unavailable: {e}\"}}"

    @tool
    def sales_forecasting() -> str:
        """
        Forecasts sales and revenue for the business based on the current pipeline.
        Use this when asked about total forecasted sales or revenue predictions.
        """
        with SessionLocal() as session:
            try:
                from .ml.prediction import prediction_service
                res = prediction_service.predict_sales_forecast(session)
                return res.model_dump_json()
            except Exception as e:
                return f"{{\"status\": \"error\", \"message\": \"Sales forecasting is currently unavailable: {e}\"}}"

    @tool
    def get_top_leads(limit: int = 5) -> str:
        """
        Retrieves ranked aggregate leads ordered by lead score.
        Use this when the user asks for 'top leads by score' or 'best leads'.
        Returns a maximum of 5 top leads by default, up to the specified limit.
        """
        with SessionLocal() as session:
            try:
                from .ml.prediction import prediction_service
                class MockUser:
                    def __init__(self):
                        self.role = role
                        self.user_id = user_id
                res = prediction_service.predict_aggregate_leads(session, MockUser())
                # Return only top `limit` leads
                try:
                    limit_val = int(limit)
                except:
                    limit_val = 5
                top_leads = res.top_leads[:limit_val]
                return f"[Source: ML Aggregate Leads]\n" + str([l.model_dump() for l in top_leads])
            except Exception as e:
                return f"{{\"status\": \"error\", \"message\": \"Aggregate leads are currently unavailable: {e}\"}}"

    return [
        predict_lead_score,
        predict_churn,
        predict_lead_conversion,
        customer_segmentation,
        sales_forecasting,
        get_top_leads
    ]
