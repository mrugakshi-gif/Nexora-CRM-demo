"""
Companies router — full CRUD with soft-delete and pagination.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, select, func, distinct, case

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_active_user, RoleChecker
from ..rbac import apply_rbac_filter, verify_assignment
from ..query_params import pagination_params, paginate_query, PageParams, PaginatedResponse

router = APIRouter(prefix="/api/companies", tags=["companies"])

SORT_FIELDS = {
    "company_name": models.Company.company_name,
    "created_at": models.Company.created_at,
    "city": models.Company.city,
    "state": models.Company.state,
    "industry_id": models.Company.industry_id,
    "account_status": models.Company.account_status,
}


def _now():
    return datetime.now(timezone.utc).isoformat()


@router.get("", response_model=PaginatedResponse)
def list_companies(
    state: Optional[str] = None,
    industry_id: Optional[str] = None,
    account_status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
    params: PageParams = Depends(pagination_params),
):
    q = db.query(models.Company).filter(models.Company.deleted_at == None)  # noqa: E711
    q = apply_rbac_filter(db, q, current_user, models.Company, 'account_owner_rep_id')
    if state:
        q = q.filter(models.Company.state == state)
    if industry_id:
        q = q.filter(models.Company.industry_id == industry_id)
    if account_status:
        q = q.filter(models.Company.account_status == account_status)
    if params.search:
        search_term = f"%{params.search}%"
        q = q.filter(
            or_(
                models.Company.company_name.ilike(search_term),
                models.Company.company_id.ilike(search_term),
                models.Company.state.ilike(search_term),
                models.Company.city.ilike(search_term),
                models.Company.account_status.ilike(search_term),
                models.Company.industry_id.ilike(search_term)
            )
        )
        
    # Phase 21B.1 - Dynamic Data Richness Sorting
    # Use scalar subqueries so counts do not multiply each other
    contacts_sub = select(func.count(models.Contact.contact_id)).where(models.Contact.company_id == models.Company.company_id).correlate(models.Company).scalar_subquery()
    leads_sub = select(func.count(models.Lead.lead_id)).where(models.Lead.company_id == models.Company.company_id).correlate(models.Company).scalar_subquery()
    opps_sub = select(func.count(models.Opportunity.opportunity_id)).where(models.Opportunity.company_id == models.Company.company_id).correlate(models.Company).scalar_subquery()
    cust_sub = select(func.count(models.Customer.customer_id)).where(models.Customer.company_id == models.Company.company_id).correlate(models.Company).scalar_subquery()

    txn_sub = select(func.count(models.CustomerTransaction.transaction_id))\
        .select_from(models.CustomerTransaction)\
        .join(models.Customer, models.CustomerTransaction.customer_id == models.Customer.customer_id)\
        .where(models.Customer.company_id == models.Company.company_id)\
        .correlate(models.Company).scalar_subquery()

    sup_sub = select(func.count(models.SupportCase.case_id))\
        .select_from(models.SupportCase)\
        .join(models.Customer, models.SupportCase.customer_id == models.Customer.customer_id)\
        .where(models.Customer.company_id == models.Company.company_id)\
        .correlate(models.Company).scalar_subquery()

    # FAST Activity Scalar Subqueries
    act_comp = select(func.count(models.Activity.activity_id)).where(models.Activity.company_id == models.Company.company_id).correlate(models.Company).scalar_subquery()

    act_cont = select(func.count(models.Activity.activity_id))\
        .select_from(models.Activity).join(models.Contact, models.Activity.contact_id == models.Contact.contact_id)\
        .where(models.Contact.company_id == models.Company.company_id).correlate(models.Company).scalar_subquery()

    act_lead = select(func.count(models.Activity.activity_id))\
        .select_from(models.Activity).join(models.Lead, models.Activity.lead_id == models.Lead.lead_id)\
        .where(models.Lead.company_id == models.Company.company_id).correlate(models.Company).scalar_subquery()

    act_opp = select(func.count(models.Activity.activity_id))\
        .select_from(models.Activity).join(models.Opportunity, models.Activity.opportunity_id == models.Opportunity.opportunity_id)\
        .where(models.Opportunity.company_id == models.Company.company_id).correlate(models.Company).scalar_subquery()

    act_cust = select(func.count(models.Activity.activity_id))\
        .select_from(models.Activity).join(models.Customer, models.Activity.customer_id == models.Customer.customer_id)\
        .where(models.Customer.company_id == models.Company.company_id).correlate(models.Company).scalar_subquery()

    data_richness = (
        func.coalesce(contacts_sub, 0) +
        func.coalesce(leads_sub, 0) +
        func.coalesce(opps_sub, 0) +
        func.coalesce(cust_sub, 0) +
        func.coalesce(txn_sub, 0) +
        func.coalesce(sup_sub, 0) +
        func.coalesce(act_comp, 0) +
        func.coalesce(act_cont, 0) +
        func.coalesce(act_lead, 0) +
        func.coalesce(act_opp, 0) +
        func.coalesce(act_cust, 0)
    ).label("data_richness")

    months_sub = select(func.count(distinct(func.strftime('%Y-%m', models.CustomerTransaction.transaction_date))))\
        .select_from(models.CustomerTransaction)\
        .join(models.Customer, models.CustomerTransaction.customer_id == models.Customer.customer_id)\
        .where(models.Customer.company_id == models.Company.company_id)\
        .correlate(models.Company).scalar_subquery()

    has_revenue_trend = case((months_sub >= 2, 1), else_=0).label("has_revenue_trend")

    crm_categories_present = (
        case((func.coalesce(contacts_sub, 0) > 0, 1), else_=0) +
        case((func.coalesce(leads_sub, 0) > 0, 1), else_=0) +
        case((func.coalesce(opps_sub, 0) > 0, 1), else_=0) +
        case((func.coalesce(cust_sub, 0) > 0, 1), else_=0) +
        case((func.coalesce(txn_sub, 0) > 0, 1), else_=0) +
        case((func.coalesce(sup_sub, 0) > 0, 1), else_=0) +
        case(((func.coalesce(act_comp, 0) + func.coalesce(act_cont, 0) + func.coalesce(act_lead, 0) + func.coalesce(act_opp, 0) + func.coalesce(act_cust, 0)) > 0, 1), else_=0) +
        case((months_sub >= 2, 1), else_=0)
    ).label("crm_categories_present")

    if not params.sort_by:
        q = q.order_by(
            crm_categories_present.desc(),
            data_richness.desc(),
            months_sub.desc(),
            models.Company.company_name.asc()
        )

    return paginate_query(q, params, SORT_FIELDS, schemas.CompanyResponse)


@router.get("/{company_id}", response_model=schemas.CompanyResponse)
def get_company(
    company_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    obj = db.query(models.Company).filter(
        models.Company.company_id == company_id,
        models.Company.deleted_at == None  # noqa: E711
    )
    obj = apply_rbac_filter(db, obj, current_user, models.Company, 'account_owner_rep_id').first()
    if not obj:
        raise HTTPException(status_code=404, detail="Company not found")
    return obj


@router.post("", response_model=schemas.CompanyResponse, status_code=status.HTTP_201_CREATED)
def create_company(
    data: schemas.CompanyCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    if hasattr(data, 'account_owner_rep_id') and getattr(data, 'account_owner_rep_id', None):
        if not verify_assignment(db, current_user, getattr(data, 'account_owner_rep_id')):
            raise HTTPException(status_code=403, detail='Not authorized to assign record to this rep')
    now = _now()
    obj = models.Company(
        **data.model_dump(),
        company_id=f"COMP-{uuid.uuid4().hex[:6].upper()}",
        created_at=now,
        updated_at=now,
        created_by=current_user.user_id,
        updated_by=current_user.user_id,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/{company_id}", response_model=schemas.CompanyResponse)
def update_company(
    company_id: str,
    data: schemas.CompanyUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    obj = db.query(models.Company).filter(
        models.Company.company_id == company_id,
        models.Company.deleted_at == None  # noqa: E711
    )
    obj = apply_rbac_filter(db, obj, current_user, models.Company, 'account_owner_rep_id').first()
    if not obj:
        raise HTTPException(status_code=404, detail="Company not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        if k == 'account_owner_rep_id' and v:
            if not verify_assignment(db, current_user, v):
                raise HTTPException(status_code=403, detail='Not authorized to assign record to this rep')
        setattr(obj, k, v)
    obj.updated_at = _now()
    obj.updated_by = current_user.user_id
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{company_id}", status_code=status.HTTP_200_OK)
def delete_company(
    company_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(RoleChecker(["Admin", "System Admin"])),
):
    obj = db.query(models.Company).filter(
        models.Company.company_id == company_id,
        models.Company.deleted_at == None  # noqa: E711
    )
    obj = apply_rbac_filter(db, obj, current_user, models.Company, 'account_owner_rep_id').first()
    if not obj:
        raise HTTPException(status_code=404, detail="Company not found")
    obj.deleted_at = _now()
    obj.updated_by = current_user.user_id
    db.commit()
    return {"message": "Company archived (soft-deleted)", "company_id": company_id}


@router.get("/{company_id}/contacts", response_model=list[schemas.ContactResponse])
def get_company_contacts(
    company_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """Return all non-deleted contacts for a company."""
    company = db.query(models.Company).filter(
        models.Company.company_id == company_id,
        models.Company.deleted_at == None  # noqa: E711
    )
    company = apply_rbac_filter(db, company, current_user, models.Company, 'account_owner_rep_id').first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return db.query(models.Contact).filter(
        models.Contact.company_id == company_id,
        models.Contact.deleted_at == None  # noqa: E711
    ).all()


@router.get("/{company_id}/leads", response_model=list[schemas.LeadResponse])
def get_company_leads(
    company_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """Return all non-deleted leads for a company."""
    company = db.query(models.Company).filter(
        models.Company.company_id == company_id,
        models.Company.deleted_at == None  # noqa: E711
    )
    company = apply_rbac_filter(db, company, current_user, models.Company, 'account_owner_rep_id').first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return db.query(models.Lead).filter(
        models.Lead.company_id == company_id,
        models.Lead.deleted_at == None  # noqa: E711
    ).all()


@router.get("/{company_id}/opportunities", response_model=list[schemas.OpportunityResponse])
def get_company_opportunities(
    company_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """Return all non-deleted opportunities for a company."""
    company = db.query(models.Company).filter(
        models.Company.company_id == company_id,
        models.Company.deleted_at == None  # noqa: E711
    )
    company = apply_rbac_filter(db, company, current_user, models.Company, 'account_owner_rep_id').first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return db.query(models.Opportunity).filter(
        models.Opportunity.company_id == company_id,
        models.Opportunity.deleted_at == None  # noqa: E711
    ).all()


@router.get("/all/lookup")
def lookup_companies(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """Return all companies (id and name only) for lightweight frontend lookup without pagination limits."""
    rows = db.query(models.Company.company_id, models.Company.company_name).filter(
        models.Company.deleted_at == None  # noqa: E711
    ).all()
    return [{"company_id": r.company_id, "company_name": r.company_name} for r in rows]
