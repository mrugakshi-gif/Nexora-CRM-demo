"""Leads router — full CRUD with soft-delete, pagination, and conversion workflow."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_active_user, RoleChecker
from ..rbac import apply_rbac_filter, verify_assignment
from ..query_params import pagination_params, paginate_query, PageParams, PaginatedResponse
from ..services.lead_service import convert_lead, update_lead_status, LEAD_STATUSES

router = APIRouter(prefix="/api/leads", tags=["leads"])

SORT_FIELDS = {
    "created_at": models.Lead.created_at,
    "lead_status": models.Lead.lead_status,
    "estimated_budget_inr": models.Lead.estimated_budget_inr,
}


def _now():
    return datetime.now(timezone.utc).isoformat()


@router.get("", response_model=PaginatedResponse)
def list_leads(
    lead_status: Optional[str] = None,
    assigned_rep_id: Optional[str] = None,
    company_id: Optional[str] = None,
    lead_source_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
    params: PageParams = Depends(pagination_params),
):
    q = db.query(models.Lead).filter(models.Lead.deleted_at == None)  # noqa: E711
    q = apply_rbac_filter(db, q, current_user, models.Lead, 'assigned_rep_id')
    if lead_status:
        if "," in lead_status:
            q = q.filter(models.Lead.lead_status.in_(lead_status.split(",")))
        else:
            q = q.filter(models.Lead.lead_status == lead_status)
    if assigned_rep_id:
        q = q.filter(models.Lead.assigned_rep_id == assigned_rep_id)
    if company_id:
        q = q.filter(models.Lead.company_id == company_id)
    if lead_source_id:
        q = q.filter(models.Lead.lead_source_id == lead_source_id)
    if params.search:
        q = q.join(models.Company, isouter=True).filter(
            models.Company.company_name.ilike(f"%{params.search}%")
        )
    return paginate_query(q, params, SORT_FIELDS, schemas.LeadResponse)


@router.get("/{lead_id}", response_model=schemas.LeadResponse)
def get_lead(
    lead_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    obj = db.query(models.Lead).filter(
        models.Lead.lead_id == lead_id,
        models.Lead.deleted_at == None  # noqa: E711
    )
    obj = apply_rbac_filter(db, obj, current_user, models.Lead, 'assigned_rep_id').first()
    if not obj:
        raise HTTPException(status_code=404, detail="Lead not found")
    return obj


@router.post("", response_model=schemas.LeadResponse, status_code=status.HTTP_201_CREATED)
def create_lead(
    data: schemas.LeadCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    company = db.query(models.Company).filter(
        models.Company.company_id == data.company_id,
        models.Company.deleted_at == None  # noqa: E711
    ).first()
    if not company:
        raise HTTPException(status_code=422, detail=f"Company {data.company_id} not found")
    if hasattr(data, 'assigned_rep_id') and getattr(data, 'assigned_rep_id', None):
        if not verify_assignment(db, current_user, getattr(data, 'assigned_rep_id')):
            raise HTTPException(status_code=403, detail='Not authorized to assign record to this rep')
    now = _now()
    obj = models.Lead(
        **data.model_dump(),
        lead_id=f"LEAD-{uuid.uuid4().hex[:6].upper()}",
        created_at=now,
        updated_at=now,
        created_by=current_user.user_id,
        updated_by=current_user.user_id,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/{lead_id}", response_model=schemas.LeadResponse)
def update_lead(
    lead_id: str,
    data: schemas.LeadUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    obj = db.query(models.Lead).filter(
        models.Lead.lead_id == lead_id,
        models.Lead.deleted_at == None  # noqa: E711
    )
    obj = apply_rbac_filter(db, obj, current_user, models.Lead, 'assigned_rep_id').first()
    if not obj:
        raise HTTPException(status_code=404, detail="Lead not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        if k == 'assigned_rep_id' and v:
            if not verify_assignment(db, current_user, v):
                raise HTTPException(status_code=403, detail='Not authorized to assign record to this rep')
        setattr(obj, k, v)
    obj.updated_at = _now()
    obj.updated_by = current_user.user_id
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{lead_id}", status_code=status.HTTP_200_OK)
def delete_lead(
    lead_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(RoleChecker(["Admin", "System Admin"])),
):
    obj = db.query(models.Lead).filter(
        models.Lead.lead_id == lead_id,
        models.Lead.deleted_at == None  # noqa: E711
    )
    obj = apply_rbac_filter(db, obj, current_user, models.Lead, 'assigned_rep_id').first()
    if not obj:
        raise HTTPException(status_code=404, detail="Lead not found")
    obj.deleted_at = _now()
    obj.updated_by = current_user.user_id
    db.commit()
    return {"message": "Lead archived", "lead_id": lead_id}


@router.get("/{lead_id}/history", response_model=list[schemas.LeadStatusHistoryResponse])
def get_lead_history(
    lead_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    lead = db.query(models.Lead).filter(models.Lead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return (
        db.query(models.LeadStatusHistory)
        .filter(models.LeadStatusHistory.lead_id == lead_id)
        .order_by(models.LeadStatusHistory.changed_at)
        .all()
    )


@router.post("/{lead_id}/convert", status_code=status.HTTP_200_OK)
def convert_lead_endpoint(
    lead_id: str,
    create_opportunity: bool = True,
    opportunity_name: Optional[str] = None,
    owner_rep_id: Optional[str] = None,
    deal_value_inr: float = 0.0,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """Convert a lead atomically.

    Creates an Opportunity (if create_opportunity=True) and updates lead status
    to Converted.  Does NOT create a transaction or customer record.
    """
    return convert_lead(
        db=db,
        lead_id=lead_id,
        create_opportunity=create_opportunity,
        opportunity_name=opportunity_name,
        owner_rep_id=owner_rep_id,
        deal_value_inr=deal_value_inr,
        changed_by_rep_id=current_user.rep_id,
    )


@router.patch("/{lead_id}/status", status_code=status.HTTP_200_OK)
def change_lead_status(
    lead_id: str,
    new_status: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """Update lead status and append a history record."""
    query = db.query(models.Lead).filter(
        models.Lead.lead_id == lead_id,
        models.Lead.deleted_at == None  # noqa: E711
    )
    lead = apply_rbac_filter(db, query, current_user, models.Lead, 'assigned_rep_id').first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    history = update_lead_status(db, lead, new_status, current_user.rep_id)
    db.commit()
    return {"lead_id": lead_id, "new_status": new_status, "history_id": history.history_id}
