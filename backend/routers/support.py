"""Support Cases router — full CRUD with soft-delete, pagination, and status workflow."""
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import func
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_active_user, RoleChecker
from ..rbac import apply_rbac_filter, verify_assignment
from ..query_params import pagination_params, paginate_query, PageParams, PaginatedResponse
from ..services.domain_services import update_support_case_status, soft_delete_support_case

router = APIRouter(prefix="/api/support", tags=["support"])

SORT_FIELDS = {
    "opened_at": models.SupportCase.opened_at,
    "priority": models.SupportCase.priority,
    "status": models.SupportCase.status,
}


def _now():
    return datetime.now(timezone.utc).isoformat()


@router.get("/summary", response_model=schemas.SupportSummaryResponse)
def get_support_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    base_query = db.query(models.SupportCase).filter(models.SupportCase.deleted_at == None)

    total_cases = base_query.count()

    # Count exact real statuses from DB
    open_cases = base_query.filter(models.SupportCase.status.in_(["Open", "In Progress", "Escalated"])).count()
    resolved_cases_count = base_query.filter(models.SupportCase.status.in_(["Resolved", "Closed"])).count()
    high_priority_cases = base_query.filter(models.SupportCase.priority.in_(["High", "Critical"])).count()

    # Avg resolution hours (rough approximation: resolved_at - opened_at if present)
    resolved_cases = base_query.filter(models.SupportCase.status == "Resolved").all()
    total_hours = 0.0
    total_satisfaction = 0.0
    satisfaction_count = 0
    
    for c in resolved_cases:
        if c.resolved_at and c.opened_at:
            try:
                # Need to handle 'Z'
                r_at = datetime.fromisoformat(c.resolved_at.replace("Z", "+00:00"))
                o_at = datetime.fromisoformat(c.opened_at.replace("Z", "+00:00"))
                diff = (r_at - o_at).total_seconds() / 3600.0
                total_hours += diff
            except Exception:
                pass
        
        if c.satisfaction_score is not None:
            total_satisfaction += c.satisfaction_score
            satisfaction_count += 1

    avg_resolution_hours = total_hours / len(resolved_cases) if resolved_cases else 0.0
    avg_satisfaction = total_satisfaction / satisfaction_count if satisfaction_count > 0 else 0.0

    # Category counts (by status)
    status_counts = db.query(
        models.SupportCase.status, 
        func.count(models.SupportCase.case_id)
    ).filter(models.SupportCase.deleted_at == None).group_by(models.SupportCase.status).all()

    category_counts = [{"category": row[0], "count": row[1]} for row in status_counts]

    return {
        "total_cases": total_cases,
        "open_cases": open_cases,
        "resolved_cases": resolved_cases_count,
        "high_priority_cases": high_priority_cases,
        "avg_resolution_hours": avg_resolution_hours,
        "avg_satisfaction": avg_satisfaction,
        "category_counts": category_counts
    }


@router.get("", response_model=PaginatedResponse)
def list_support_cases(
    customer_id: Optional[str] = None,
    status_: Optional[str] = Query(None, alias="status"),
    priority: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
    params: PageParams = Depends(pagination_params),
):
    q = db.query(models.SupportCase).filter(models.SupportCase.deleted_at == None)  # noqa: E711
    q = q.join(models.Customer, models.SupportCase.customer_id == models.Customer.customer_id)
    q = apply_rbac_filter(db, q, current_user, models.Customer, 'csm_rep_id')
    if customer_id:
        q = q.filter(models.SupportCase.customer_id == customer_id)
    if status_:
        q = q.filter(models.SupportCase.status == status_)
    if priority:
        q = q.filter(models.SupportCase.priority == priority)
    
    if params.search:
        search_term = f"%{params.search}%"
        # Join through Customer -> Company so we can search by company name.
        # Use outerjoin to avoid dropping cases with no customer/company record.
        q = (
            q
            .outerjoin(models.Customer, models.SupportCase.customer_id == models.Customer.customer_id)
            .outerjoin(models.Company, models.Customer.company_id == models.Company.company_id)
            .filter(
                models.SupportCase.case_id.ilike(search_term)
                | models.SupportCase.customer_id.ilike(search_term)
                | models.SupportCase.case_type.ilike(search_term)
                | models.SupportCase.status.ilike(search_term)
                | models.Company.company_name.ilike(search_term)
            )
        )
    return paginate_query(q, params, SORT_FIELDS, schemas.SupportCaseResponse)


@router.get("/{case_id}", response_model=schemas.SupportCaseResponse)
def get_support_case(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    obj = db.query(models.SupportCase).filter(
        models.SupportCase.case_id == case_id,
        models.SupportCase.deleted_at == None  # noqa: E711
    )
    obj = obj.join(models.Customer, models.SupportCase.customer_id == models.Customer.customer_id)
    obj = apply_rbac_filter(db, obj, current_user, models.Customer, 'csm_rep_id').first()
    if not obj:
        raise HTTPException(status_code=404, detail="Support case not found")
    return obj


@router.post("", response_model=schemas.SupportCaseResponse, status_code=status.HTTP_201_CREATED)
def create_support_case(
    data: schemas.SupportCaseCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    if getattr(data, 'customer_id', None):
        cust = apply_rbac_filter(db, db.query(models.Customer), current_user, models.Customer, 'csm_rep_id').filter(models.Customer.customer_id == data.customer_id).first()
        if not cust:
            raise HTTPException(status_code=403, detail='Not authorized for this customer')
    now = _now()
    obj = models.SupportCase(
        **data.model_dump(),
        case_id=f"CASE-{uuid.uuid4().hex[:6].upper()}",
        updated_at=now,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/{case_id}", response_model=schemas.SupportCaseResponse)
def update_support_case(
    case_id: str,
    data: schemas.SupportCaseUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    obj = db.query(models.SupportCase).filter(
        models.SupportCase.case_id == case_id,
        models.SupportCase.deleted_at == None  # noqa: E711
    )
    obj = obj.join(models.Customer, models.SupportCase.customer_id == models.Customer.customer_id)
    obj = apply_rbac_filter(db, obj, current_user, models.Customer, 'csm_rep_id').first()
    if not obj:
        raise HTTPException(status_code=404, detail="Support case not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        if k == 'customer_id' and v:
            cust = apply_rbac_filter(db, db.query(models.Customer), current_user, models.Customer, 'csm_rep_id').filter(models.Customer.customer_id == v).first()
            if not cust:
                raise HTTPException(status_code=403, detail='Not authorized for this customer')
        setattr(obj, k, v)
    obj.updated_at = _now()
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/{case_id}/status", response_model=schemas.SupportCaseResponse)
def change_support_case_status(
    case_id: str,
    new_status: str,
    satisfaction_score: Optional[float] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """Update case status using validated workflow."""
    return update_support_case_status(db, case_id, new_status, satisfaction_score)


@router.delete("/{case_id}", status_code=status.HTTP_200_OK)
def delete_support_case(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(RoleChecker(["Admin", "System Admin"])),
):
    soft_delete_support_case(db, case_id)
    return {"message": "Support case archived", "case_id": case_id}
