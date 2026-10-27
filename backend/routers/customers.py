"""Customers router — full CRUD with soft-delete, pagination, and 360-view."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_active_user, RoleChecker
from ..rbac import apply_rbac_filter, verify_assignment
from ..query_params import pagination_params, paginate_query, PageParams, PaginatedResponse
from ..services.customer_service import get_customer_360

router = APIRouter(prefix="/api/customers", tags=["customers"])

SORT_FIELDS = {
    "customer_since": models.Customer.customer_since,
    "customer_tier": models.Customer.customer_tier,
    "customer_status": models.Customer.customer_status,
}


def _now():
    return datetime.now(timezone.utc).isoformat()


@router.get("", response_model=PaginatedResponse)
def list_customers(
    company_id: Optional[str] = None,
    customer_status: Optional[str] = None,
    csm_rep_id: Optional[str] = None,
    customer_tier: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
    params: PageParams = Depends(pagination_params),
):
    q = db.query(models.Customer).filter(models.Customer.deleted_at == None)  # noqa: E711
    q = apply_rbac_filter(db, q, current_user, models.Customer, 'csm_rep_id')
    if company_id:
        q = q.filter(models.Customer.company_id == company_id)
    if customer_status:
        q = q.filter(models.Customer.customer_status == customer_status)
    if csm_rep_id:
        q = q.filter(models.Customer.csm_rep_id == csm_rep_id)
    if customer_tier:
        q = q.filter(models.Customer.customer_tier == customer_tier)
    if params.search:
        q = q.join(models.Company, isouter=True).filter(
            models.Company.company_name.ilike(f"%{params.search}%")
        )
    return paginate_query(q, params, SORT_FIELDS, schemas.CustomerResponse)


@router.get("/statuses/list")
def get_customer_statuses(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """Return distinct customer_status values."""
    rows = db.query(models.Customer.customer_status).distinct().filter(
        models.Customer.deleted_at == None  # noqa: E711
    ).all()
    # rows is a list of tuples like [('Active',), ('At Risk',)]
    statuses = [r[0] for r in rows if r[0]]
    return sorted(statuses)

@router.get("/stats")
def get_customer_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """Return KPI stats for customers."""
    total = db.query(func.count(models.Customer.customer_id)).filter(models.Customer.deleted_at == None).scalar() or 0
    active = db.query(func.count(models.Customer.customer_id)).filter(
        models.Customer.deleted_at == None,
        models.Customer.customer_status == 'Active'
    ).scalar() or 0
    at_risk = db.query(func.count(models.Customer.customer_id)).filter(
        models.Customer.deleted_at == None,
        models.Customer.customer_status == 'At Risk'
    ).scalar() or 0
    churned = db.query(func.count(models.Customer.customer_id)).filter(
        models.Customer.deleted_at == None,
        models.Customer.customer_status == 'Paused'
    ).scalar() or 0
    
    return {
        "total": total,
        "active": active,
        "atRisk": at_risk,
        "churned": churned
    }


@router.get("/all/lookup")
def lookup_customers(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """Return all customers (id and name) for lightweight frontend lookup."""
    # Since customer name might be the company name, we return company_name
    rows = db.query(
        models.Customer.customer_id,
        models.Company.company_name
    ).join(models.Company).filter(
        models.Customer.deleted_at == None, # noqa: E711
        models.Company.deleted_at == None   # noqa: E711
    ).all()
    return [{"customer_id": r.customer_id, "customer_name": r.company_name} for r in rows]


# ── Wildcard routes come AFTER all static paths ──────────────────────────────

@router.get("/{customer_id}", response_model=schemas.CustomerResponse)
def get_customer(
    customer_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    obj = db.query(models.Customer).filter(
        models.Customer.customer_id == customer_id,
        models.Customer.deleted_at == None  # noqa: E711
    )
    obj = apply_rbac_filter(db, obj, current_user, models.Customer, 'csm_rep_id').first()
    if not obj:
        raise HTTPException(status_code=404, detail="Customer not found")
    return obj


@router.get("/{customer_id}/360")
def get_customer_360_view(
    customer_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """Return a 360-degree summary of a customer."""
    return get_customer_360(db, customer_id)


@router.post("", response_model=schemas.CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer(
    data: schemas.CustomerCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    company = db.query(models.Company).filter(
        models.Company.company_id == data.company_id,
        models.Company.deleted_at == None  # noqa: E711
    ).first()
    if not company:
        raise HTTPException(status_code=422, detail="Company not found")
    opp = db.query(models.Opportunity).filter(
        models.Opportunity.opportunity_id == data.originating_opportunity_id
    ).first()
    if not opp:
        raise HTTPException(status_code=422, detail="Opportunity not found")
    if hasattr(data, 'csm_rep_id') and getattr(data, 'csm_rep_id', None):
        if not verify_assignment(db, current_user, getattr(data, 'csm_rep_id')):
            raise HTTPException(status_code=403, detail='Not authorized to assign record to this rep')
    now = _now()
    obj = models.Customer(
        **data.model_dump(),
        customer_id=f"CUST-{uuid.uuid4().hex[:6].upper()}",
        updated_at=now,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/{customer_id}", response_model=schemas.CustomerResponse)
def update_customer(
    customer_id: str,
    data: schemas.CustomerUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    obj = db.query(models.Customer).filter(
        models.Customer.customer_id == customer_id,
        models.Customer.deleted_at == None  # noqa: E711
    )
    obj = apply_rbac_filter(db, obj, current_user, models.Customer, 'csm_rep_id').first()
    if not obj:
        raise HTTPException(status_code=404, detail="Customer not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        if k == 'csm_rep_id' and v:
            if not verify_assignment(db, current_user, v):
                raise HTTPException(status_code=403, detail='Not authorized to assign record to this rep')
        setattr(obj, k, v)
    obj.updated_at = _now()
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{customer_id}", status_code=status.HTTP_200_OK)
def delete_customer(
    customer_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(RoleChecker(["Admin", "System Admin"])),
):
    obj = db.query(models.Customer).filter(
        models.Customer.customer_id == customer_id,
        models.Customer.deleted_at == None  # noqa: E711
    )
    obj = apply_rbac_filter(db, obj, current_user, models.Customer, 'csm_rep_id').first()
    if not obj:
        raise HTTPException(status_code=404, detail="Customer not found")
    obj.deleted_at = _now()
    db.commit()
    return {"message": "Customer archived", "customer_id": customer_id}
