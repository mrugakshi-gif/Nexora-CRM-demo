"""
analytics_service.py — On-demand aggregated CRM analytics.

All metrics are computed directly from the database.
No values are hardcoded.  No artificial records are generated.
"""
from __future__ import annotations

from typing import Any
from sqlalchemy import func, case, desc
from sqlalchemy.orm import Session

from .. import models


def apply_date_filter(query: Any, model_attr: Any, start_date: str | None, end_date: str | None) -> Any:
    if start_date:
        query = query.filter(func.substr(model_attr, 1, 10) >= start_date)
    if end_date:
        query = query.filter(func.substr(model_attr, 1, 10) <= end_date)
    return query


def get_dashboard_kpis(db: Session, start_date: str | None = None, end_date: str | None = None) -> dict[str, Any]:
    """Top-level dashboard KPIs computed from the database."""

    # --- Companies ---
    # Total companies represents all non-deleted companies in the database (1,200),
    # preserving the intended definition across all selected periods.
    q_companies = db.query(func.count(models.Company.company_id)).filter(models.Company.deleted_at == None)
    total_companies = q_companies.scalar() or 0
    
    q_active_companies = db.query(func.count(models.Company.company_id)).filter(
        models.Company.account_status == "Active Customer",
        models.Company.deleted_at == None
    )
    active_companies = q_active_companies.scalar() or 0

    # --- Contacts ---
    q_contacts = db.query(func.count(models.Contact.contact_id)).filter(models.Contact.deleted_at == None)
    total_contacts = q_contacts.scalar() or 0

    # --- Leads ---
    q_leads = db.query(func.count(models.Lead.lead_id)).filter(models.Lead.deleted_at == None)
    q_leads = apply_date_filter(q_leads, models.Lead.created_at, start_date, end_date)
    total_leads = q_leads.scalar() or 0
    
    q_converted_leads = db.query(func.count(models.Lead.lead_id)).filter(
        models.Lead.lead_status == "Converted",
        models.Lead.deleted_at == None
    )
    q_converted_leads = apply_date_filter(q_converted_leads, func.coalesce(models.Lead.converted_at, models.Lead.created_at), start_date, end_date)
    converted_leads = q_converted_leads.scalar() or 0
    
    lead_conversion_rate = round(
        (converted_leads / total_leads * 100) if total_leads else 0.0, 2
    )

    # --- Opportunities ---
    # Business date for opportunities: expected_close_date for open pipeline,
    # actual_close_date for won deals, and coalesce(actual, expected) for period deal totals.
    business_date = func.coalesce(models.Opportunity.actual_close_date, models.Opportunity.expected_close_date)

    q_opps = db.query(func.count(models.Opportunity.opportunity_id)).filter(models.Opportunity.deleted_at == None)
    q_opps = apply_date_filter(q_opps, business_date, start_date, end_date)
    total_opps = q_opps.scalar() or 0
    
    q_open_opps = db.query(func.count(models.Opportunity.opportunity_id)).filter(
        models.Opportunity.close_outcome == None,
        models.Opportunity.deleted_at == None
    )
    q_open_opps = apply_date_filter(q_open_opps, models.Opportunity.expected_close_date, start_date, end_date)
    open_opps = q_open_opps.scalar() or 0
    
    q_won_opps = db.query(func.count(models.Opportunity.opportunity_id)).filter(
        models.Opportunity.close_outcome == "Won",
        models.Opportunity.deleted_at == None
    )
    q_won_opps = apply_date_filter(q_won_opps, models.Opportunity.actual_close_date, start_date, end_date)
    won_opps = q_won_opps.scalar() or 0
    
    q_pipeline = db.query(func.sum(models.Opportunity.deal_value_inr)).filter(
        models.Opportunity.close_outcome == None,
        models.Opportunity.deleted_at == None
    )
    q_pipeline = apply_date_filter(q_pipeline, models.Opportunity.expected_close_date, start_date, end_date)
    pipeline_value = q_pipeline.scalar() or 0.0

    q_weighted = db.query(func.sum(models.Opportunity.deal_value_inr * (models.Opportunity.probability_pct / 100.0))).filter(
        models.Opportunity.close_outcome == None,
        models.Opportunity.deleted_at == None
    )
    q_weighted = apply_date_filter(q_weighted, models.Opportunity.expected_close_date, start_date, end_date)
    weighted_pipeline = q_weighted.scalar() or 0.0

    q_won_rev = db.query(func.sum(models.Opportunity.deal_value_inr)).filter(
        models.Opportunity.close_outcome == "Won",
        models.Opportunity.deleted_at == None
    )
    q_won_rev = apply_date_filter(q_won_rev, models.Opportunity.actual_close_date, start_date, end_date)
    won_revenue_inr = q_won_rev.scalar() or 0.0

    # --- Customers ---
    q_customers = db.query(func.count(models.Customer.customer_id)).filter(models.Customer.deleted_at == None)
    q_customers = apply_date_filter(q_customers, models.Customer.customer_since, start_date, end_date)
    total_customers = q_customers.scalar() or 0
    
    q_active_customers = db.query(func.count(models.Customer.customer_id)).filter(
        models.Customer.customer_status == "Active",
        models.Customer.deleted_at == None
    )
    q_active_customers = apply_date_filter(q_active_customers, models.Customer.customer_since, start_date, end_date)
    active_customers = q_active_customers.scalar() or 0

    # --- Transactions ---
    q_trans = db.query(func.count(models.CustomerTransaction.transaction_id)).filter(
        models.CustomerTransaction.transaction_type != "Refund",
        models.CustomerTransaction.deleted_at == None
    )
    q_trans = apply_date_filter(q_trans, models.CustomerTransaction.transaction_date, start_date, end_date)
    total_transactions = q_trans.scalar() or 0
    
    q_revenue = db.query(func.sum(models.CustomerTransaction.amount_inr)).filter(
        models.CustomerTransaction.payment_status == "Paid",
        models.CustomerTransaction.deleted_at == None
    )
    q_revenue = apply_date_filter(q_revenue, models.CustomerTransaction.transaction_date, start_date, end_date)
    total_revenue_inr = q_revenue.scalar() or 0.0

    # --- Support ---
    q_cases = db.query(func.count(models.SupportCase.case_id)).filter(
        models.SupportCase.status.in_(["Open", "In Progress"]),
        models.SupportCase.deleted_at == None
    )
    q_cases = apply_date_filter(q_cases, models.SupportCase.opened_at, start_date, end_date)
    open_cases = q_cases.scalar() or 0

    return {
        "total_companies": total_companies,
        "active_companies": active_companies,
        "total_contacts": total_contacts,
        "total_leads": total_leads,
        "converted_leads": converted_leads,
        "lead_conversion_rate_pct": lead_conversion_rate,
        "total_opportunities": total_opps,
        "open_opportunities": open_opps,
        "won_opportunities": won_opps,
        "pipeline_value_inr": round(pipeline_value, 2),
        "weighted_pipeline_inr": round(weighted_pipeline, 2),
        "won_revenue_inr": round(won_revenue_inr, 2),
        "total_customers": total_customers,
        "active_customers": active_customers,
        "total_transactions": total_transactions,
        "total_revenue_inr": round(total_revenue_inr, 2),
        "open_support_cases": open_cases,
    }


def get_lead_funnel(db: Session, start_date: str | None = None, end_date: str | None = None) -> list[dict]:
    """Lead count grouped by status."""
    q = db.query(models.Lead.lead_status, func.count(models.Lead.lead_id)).filter(models.Lead.deleted_at == None)
    q = apply_date_filter(q, models.Lead.created_at, start_date, end_date)
    rows = q.group_by(models.Lead.lead_status).all()
    return [{"status": r[0], "count": r[1]} for r in rows]


def get_opportunity_pipeline(db: Session, start_date: str | None = None, end_date: str | None = None) -> list[dict]:
    """Opportunity count and value grouped by pipeline stage."""
    q = db.query(
        models.Opportunity.pipeline_stage,
        func.count(models.Opportunity.opportunity_id),
        func.sum(models.Opportunity.deal_value_inr),
    ).filter(models.Opportunity.deleted_at == None)
    business_date = func.coalesce(models.Opportunity.actual_close_date, models.Opportunity.expected_close_date)
    q = apply_date_filter(q, business_date, start_date, end_date)
    rows = q.group_by(models.Opportunity.pipeline_stage).all()
    return [
        {
            "stage": r[0],
            "count": r[1],
            "total_value_inr": round(r[2] or 0.0, 2),
        }
        for r in rows
    ]


def get_revenue_by_month(db: Session, start_date: str | None = None, end_date: str | None = None) -> list[dict]:
    """Monthly aggregated revenue from paid transactions."""
    q = db.query(
        func.substr(models.CustomerTransaction.transaction_date, 1, 7).label("month"),
        func.sum(models.CustomerTransaction.amount_inr).label("revenue"),
    ).filter(
        models.CustomerTransaction.payment_status == "Paid",
        models.CustomerTransaction.deleted_at == None,
    )
    q = apply_date_filter(q, models.CustomerTransaction.transaction_date, start_date, end_date)
    rows = q.group_by("month").order_by("month").all()
    return [{"month": r[0], "revenue_inr": round(r[1] or 0.0, 2)} for r in rows]


def get_support_summary(db: Session, start_date: str | None = None, end_date: str | None = None) -> dict:
    """Support case counts by status and average satisfaction score."""
    q_total = db.query(func.count(models.SupportCase.case_id)).filter(models.SupportCase.deleted_at == None)
    q_total = apply_date_filter(q_total, models.SupportCase.opened_at, start_date, end_date)
    total = q_total.scalar() or 0
    
    q_avg = db.query(func.avg(models.SupportCase.satisfaction_score)).filter(
        models.SupportCase.satisfaction_score != None,
        models.SupportCase.deleted_at == None,
    )
    q_avg = apply_date_filter(q_avg, models.SupportCase.opened_at, start_date, end_date)
    avg_score = q_avg.scalar()
    
    q_status = db.query(models.SupportCase.status, func.count(models.SupportCase.case_id)).filter(
        models.SupportCase.deleted_at == None
    )
    q_status = apply_date_filter(q_status, models.SupportCase.opened_at, start_date, end_date)
    by_status = q_status.group_by(models.SupportCase.status).all()
    
    return {
        "total_cases": total,
        "avg_satisfaction_score": round(avg_score, 2) if avg_score else None,
        "by_status": [{"status": r[0], "count": r[1]} for r in by_status],
    }


def get_top_customers(db: Session, start_date: str | None = None, end_date: str | None = None, limit: int = 5) -> list[dict]:
    """Top customers by revenue from paid transactions."""
    q = db.query(
        models.Customer.customer_id,
        models.Company.company_id,
        models.Company.company_name,
        func.sum(models.CustomerTransaction.amount_inr).label("revenue")
    ).join(
        models.Customer, models.CustomerTransaction.customer_id == models.Customer.customer_id
    ).join(
        models.Company, models.Customer.company_id == models.Company.company_id
    ).filter(
        models.CustomerTransaction.payment_status == "Paid",
        models.CustomerTransaction.deleted_at == None
    )
    q = apply_date_filter(q, models.CustomerTransaction.transaction_date, start_date, end_date)
    rows = q.group_by(
        models.Customer.customer_id, models.Company.company_id, models.Company.company_name
    ).order_by(
        desc("revenue")
    ).limit(limit).all()
    
    return [{"customer_id": r[0], "company_id": r[1], "company_name": r[2], "revenue_inr": round(r[3] or 0.0, 2)} for r in rows]


def get_top_products(db: Session, start_date: str | None = None, end_date: str | None = None, limit: int = 5) -> list[dict]:
    """Top products by deal value from won opportunities.
    This aggregates line items from OpportunityProducts linked to Closed Won Opportunities.
    """
    q = db.query(
        models.Product.product_id,
        models.Product.product_name,
        func.sum(models.OpportunityProduct.line_total_inr).label("revenue")
    ).join(
        models.OpportunityProduct, models.Product.product_id == models.OpportunityProduct.product_id
    ).join(
        models.Opportunity, models.OpportunityProduct.opportunity_id == models.Opportunity.opportunity_id
    ).filter(
        models.Opportunity.close_outcome == "Won",
        models.Opportunity.deleted_at == None,
        models.Product.deleted_at == None
    )
    q = apply_date_filter(q, models.Opportunity.actual_close_date, start_date, end_date)
    rows = q.group_by(
        models.Product.product_id, models.Product.product_name
    ).order_by(
        desc("revenue")
    ).limit(limit).all()
    return [{"product_id": r[0], "product_name": r[1], "revenue_inr": round(r[2] or 0.0, 2)} for r in rows]

def get_companies_by_state(db: Session, start_date: str | None = None, end_date: str | None = None) -> list[dict]:
    """Companies grouped by state."""
    q = db.query(
        models.Company.state,
        func.count(models.Company.company_id)
    ).filter(models.Company.deleted_at == None)
    q = apply_date_filter(q, models.Company.created_at, start_date, end_date)
    rows = q.group_by(models.Company.state).all()
    return [{"state": r[0] or 'Unknown', "count": r[1]} for r in rows]

