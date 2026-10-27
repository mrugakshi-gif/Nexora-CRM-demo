"""Lookups router — lightweight unpaginated endpoints for dropdowns."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, List, Any

from .. import models
from ..database import get_db
from ..deps import get_current_active_user

router = APIRouter(prefix="/api/lookups", tags=["lookups"])


@router.get("", response_model=Dict[str, List[Dict[str, Any]]])
def get_all_lookups(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """
    Returns lightweight ID and Name pairs for all major entities.
    Used for frontend dropdowns to avoid large paginated requests and 422 limits.
    """
    lookups = {}

    # Companies
    companies = db.query(models.Company.company_id, models.Company.company_name).filter(
        models.Company.deleted_at == None
    ).all()
    lookups["companies"] = [{"id": r.company_id, "name": r.company_name} for r in companies]

    # Customers
    customers = db.query(
        models.Customer.customer_id,
        models.Company.company_name
    ).join(models.Company).filter(
        models.Customer.deleted_at == None,
        models.Company.deleted_at == None
    ).all()
    lookups["customers"] = [{"id": r.customer_id, "name": r.company_name} for r in customers]

    # Contacts
    contacts = db.query(models.Contact.contact_id, models.Contact.full_name).filter(
        models.Contact.deleted_at == None
    ).all()
    lookups["contacts"] = [{"id": r.contact_id, "name": r.full_name} for r in contacts]

    # Leads
    leads = db.query(models.Lead.lead_id, models.Company.company_name).outerjoin(
        models.Company, models.Lead.company_id == models.Company.company_id
    ).filter(
        models.Lead.deleted_at == None
    ).all()
    lookups["leads"] = [{"id": r.lead_id, "name": f"Lead for {r.company_name}" if r.company_name else r.lead_id} for r in leads]

    # Opportunities
    opps = db.query(models.Opportunity.opportunity_id, models.Opportunity.opportunity_name).filter(
        models.Opportunity.deleted_at == None
    ).all()
    lookups["opportunities"] = [{"id": r.opportunity_id, "name": r.opportunity_name} for r in opps]

    # Sales Reps
    reps = db.query(models.SalesRep.rep_id, models.SalesRep.full_name).all()
    lookups["sales_reps"] = [{"id": r.rep_id, "name": r.full_name} for r in reps]

    # Campaigns
    campaigns = db.query(models.Campaign.campaign_id, models.Campaign.campaign_name).filter(
        models.Campaign.deleted_at == None
    ).all()
    lookups["campaigns"] = [{"id": r.campaign_id, "name": r.campaign_name} for r in campaigns]

    # Products
    products = db.query(models.Product.product_id, models.Product.product_name).filter(
        models.Product.deleted_at == None
    ).all()
    lookups["products"] = [{"id": r.product_id, "name": r.product_name} for r in products]

    return lookups
