from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from .. import models
from ..database import get_db
from ..deps import get_current_active_user

router = APIRouter(prefix="/api/search", tags=["search"])

@router.get("")
@router.get("/")
def global_search(
    q: str = Query(..., min_length=2),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """
    Global search across multiple entities.
    Enforces RBAC where applicable.
    """
    results = []
    
    # 1. Companies
    companies = db.query(models.Company).filter(
        models.Company.deleted_at == None,
        models.Company.company_name.ilike(f"%{q}%")
    ).limit(5).all()
    for c in companies:
        results.append({
            "type": "Company",
            "id": c.company_id,
            "title": c.company_name,
            "subtitle": c.industry or "Company"
        })
        
    # 2. Contacts
    contacts = db.query(models.Contact).filter(
        models.Contact.deleted_at == None,
        or_(
            models.Contact.full_name.ilike(f"%{q}%"),
            models.Contact.email.ilike(f"%{q}%")
        )
    ).limit(5).all()
    for c in contacts:
        results.append({
            "type": "Contact",
            "id": c.contact_id,
            "title": c.full_name,
            "subtitle": f"{c.job_title + ' · ' if c.job_title else ''}{c.email}"
        })
        
    # 3. Customers
    customers = db.query(models.Customer).filter(
        models.Customer.deleted_at == None,
        models.Customer.company_name.ilike(f"%{q}%")
    ).limit(5).all()
    for c in customers:
        results.append({
            "type": "Customer",
            "id": c.customer_id,
            "title": c.company_name,
            "subtitle": c.customer_status
        })

    # 4. Leads (if role is admin or sales)
    if current_user.role.lower() in ["admin", "sales"]:
        leads = db.query(models.Lead).filter(
            models.Lead.deleted_at == None,
            or_(
                models.Lead.company_name.ilike(f"%{q}%"),
                models.Lead.email.ilike(f"%{q}%")
            )
        ).limit(5).all()
        for l in leads:
            results.append({
                "type": "Lead",
                "id": l.lead_id,
                "title": f"{l.company_name}",
                "subtitle": l.email or l.lead_status
            })
            
    # 5. Opportunities (if role is admin or sales)
    if current_user.role.lower() in ["admin", "sales"]:
        opps = db.query(models.Opportunity).filter(
            models.Opportunity.deleted_at == None,
            models.Opportunity.opportunity_name.ilike(f"%{q}%")
        ).limit(5).all()
        for o in opps:
            results.append({
                "type": "Opportunity",
                "id": o.opportunity_id,
                "title": o.opportunity_name,
                "subtitle": f"Stage: {o.pipeline_stage}"
            })

    # 6. Products
    products = db.query(models.Product).filter(
        models.Product.deleted_at == None,
        models.Product.product_name.ilike(f"%{q}%")
    ).limit(5).all()
    for p in products:
        results.append({
            "type": "Product",
            "id": p.product_id,
            "title": p.product_name,
            "subtitle": p.category or "Product"
        })

    # 7. Transactions
    if current_user.role.lower() in ["admin", "sales"]:
        transactions = db.query(models.CustomerTransaction).filter(
            or_(
                models.CustomerTransaction.transaction_id.ilike(f"%{q}%"),
                models.CustomerTransaction.payment_method.ilike(f"%{q}%")
            )
        ).limit(5).all()
        for t in transactions:
            results.append({
                "type": "Transaction",
                "id": t.transaction_id,
                "title": t.transaction_id,
                "subtitle": f"Status: {t.transaction_status}"
            })

    # 8. Activities / Tasks
    activities = db.query(models.Activity).filter(
        or_(
            models.Activity.activity_type.ilike(f"%{q}%"),
            models.Activity.notes.ilike(f"%{q}%")
        )
    ).limit(5).all()
    for a in activities:
        results.append({
            "type": "Activity",
            "id": a.activity_id,
            "title": a.activity_type,
            "subtitle": (a.notes[:50] + "...") if a.notes else a.status
        })

    # 9. Campaigns (if role is admin or marketing)
    if current_user.role.lower() in ["admin", "marketing"]:
        campaigns = db.query(models.Campaign).filter(
            models.Campaign.deleted_at == None,
            models.Campaign.campaign_name.ilike(f"%{q}%")
        ).limit(5).all()
        for c in campaigns:
            results.append({
                "type": "Campaign",
                "id": c.campaign_id,
                "title": c.campaign_name,
                "subtitle": f"Status: {c.status}"
            })

    # 10. Support Cases
    support_cases = db.query(models.SupportCase).filter(
        models.SupportCase.deleted_at == None,
        or_(
            models.SupportCase.subject.ilike(f"%{q}%"),
            models.SupportCase.case_id.ilike(f"%{q}%")
        )
    ).limit(5).all()
    for s in support_cases:
        results.append({
            "type": "Support Case",
            "id": s.case_id,
            "title": s.subject or s.case_id,
            "subtitle": f"Status: {s.status} | Priority: {s.priority}"
        })

    return {"results": results}
