from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional

from .. import models
from ..database import get_db
from ..deps import get_current_active_user

router = APIRouter(prefix="/api/compare", tags=["compare"])

@router.get("/customers")
def compare_customers(
    ids: str = Query(..., description="Comma separated customer IDs"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    id_list = [i.strip() for i in ids.split(",") if i.strip()]
    if not id_list:
        return {}
        
    customers = db.query(models.Customer).filter(
        models.Customer.customer_id.in_(id_list),
        models.Customer.deleted_at == None
    ).all()
    
    result = {}
    for c in customers:
        # Transactions
        txns = db.query(func.sum(models.CustomerTransaction.amount_inr), func.count(models.CustomerTransaction.transaction_id)).filter(
            models.CustomerTransaction.customer_id == c.customer_id,
            models.CustomerTransaction.payment_status == 'Paid',
            models.CustomerTransaction.deleted_at == None
        ).first()
        rev = txns[0] or 0
        orders = txns[1] or 0
        
        # Support cases
        cases = db.query(func.count(models.SupportCase.case_id)).filter(
            models.SupportCase.customer_id == c.customer_id,
            models.SupportCase.deleted_at == None
        ).scalar() or 0
        
        result[c.customer_id] = {
            "customer_name": c.company.company_name if c.company else "Unknown",
            "customer_since": c.customer_since,
            "customer_status": c.customer_status,
            "customer_tier": c.customer_tier,
            "contract_type": c.contract_type,
            "renewal_date": c.renewal_date,
            "total_revenue": rev,
            "total_orders": orders,
            "support_cases": cases,
            "csm_name": c.csm_rep.full_name if c.csm_rep else "Unassigned"
        }
    return result

@router.get("/leads")
def compare_leads(
    ids: str = Query(..., description="Comma separated lead IDs"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    id_list = [i.strip() for i in ids.split(",") if i.strip()]
    if not id_list:
        return {}
        
    leads = db.query(models.Lead).filter(
        models.Lead.lead_id.in_(id_list),
        models.Lead.deleted_at == None
    ).all()
    
    result = {}
    for l in leads:
        # Activities
        acts = db.query(func.count(models.Activity.activity_id)).filter(
            models.Activity.lead_id == l.lead_id,
            models.Activity.deleted_at == None
        ).scalar() or 0
        
        result[l.lead_id] = {
            "lead_name": l.contact.full_name if l.contact else (l.company.company_name if l.company else "Unknown"),
            "lead_status": l.lead_status,
            "estimated_budget_inr": l.estimated_budget_inr,
            "company_size_at_lead_time": l.company_size_at_lead_time,
            "lead_source": l.lead_source.source_name if l.lead_source else "Unknown",
            "campaign": l.campaign.campaign_name if l.campaign else "None",
            "industry_interest": l.industry_interest.industry_name if l.industry_interest else "None",
            "assigned_rep": l.assigned_rep.full_name if l.assigned_rep else "Unassigned",
            "activity_count": acts
        }
    return result

@router.get("/products")
def compare_products(
    ids: str = Query(..., description="Comma separated product IDs"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    id_list = [i.strip() for i in ids.split(",") if i.strip()]
    if not id_list:
        return {}
        
    products = db.query(models.Product).filter(
        models.Product.product_id.in_(id_list),
        models.Product.deleted_at == None
    ).all()
    
    result = {}
    for p in products:
        stats = db.query(
            func.sum(models.OpportunityProduct.line_total_inr),
            func.sum(models.OpportunityProduct.quantity),
            func.avg(models.OpportunityProduct.discount_pct),
            func.count(models.OpportunityProduct.opportunity_product_id)
        ).filter(
            models.OpportunityProduct.product_id == p.product_id
        ).first()
        
        result[p.product_id] = {
            "product_name": p.product_name,
            "product_category": p.product_category,
            "pricing_model": p.pricing_model,
            "list_price_inr": p.list_price_inr,
            "is_active": p.is_active,
            "pipeline_value": stats[0] or 0,
            "units_sold": stats[1] or 0,
            "avg_discount": stats[2] or 0,
            "opportunity_count": stats[3] or 0
        }
    return result

@router.get("/top-leads")
def get_top_leads_by_activity(db: Session = Depends(get_db)):
    """Get top 3 leads by activity count from the complete dataset."""
    leads = db.query(
        models.Lead.lead_id,
        func.count(models.Activity.activity_id).label('activity_count')
    ).outerjoin(
        models.Activity, models.Lead.lead_id == models.Activity.lead_id
    ).filter(
        models.Lead.deleted_at == None,
        models.Activity.deleted_at == None
    ).group_by(models.Lead.lead_id).order_by(func.count(models.Activity.activity_id).desc()).limit(3).all()
    
    # We return them in the same format as if we fetched them by id, so the frontend can use them
    # Wait, if we return lead objects, it's easier.
    
    lead_ids = [l.lead_id for l in leads]
    if not lead_ids:
        return []
        
    top_leads = db.query(models.Lead).filter(models.Lead.lead_id.in_(lead_ids)).all()
    # maintain order
    lead_map = {l.lead_id: l for l in top_leads}
    
    result = []
    for l_id, count in leads:
        if l_id in lead_map:
            result.append(lead_map[l_id])
            
    return result
