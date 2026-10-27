"""Activities router — full CRUD with soft-delete, pagination, and completion workflow."""
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
from ..services.domain_services import complete_activity, soft_delete_activity

router = APIRouter(prefix="/api/activities", tags=["activities"])

SORT_FIELDS = {
    "activity_date": models.Activity.activity_date,
    "created_at": models.Activity.created_at,
    "due_date": models.Activity.due_date,
    "priority": models.Activity.priority,
}


def _now():
    return datetime.now(timezone.utc).isoformat()


@router.get("", response_model=PaginatedResponse)
def list_activities(
    sales_rep_id: Optional[str] = None,
    lead_id: Optional[str] = None,
    company_id: Optional[str] = None,
    contact_id: Optional[str] = None,
    opportunity_id: Optional[str] = None,
    customer_id: Optional[str] = None,
    activity_type: Optional[str] = None,
    year: Optional[str] = None,
    status_: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
    params: PageParams = Depends(pagination_params),
):
    q = db.query(models.Activity).filter(models.Activity.deleted_at == None)  # noqa: E711
    q = apply_rbac_filter(db, q, current_user, models.Activity, 'sales_rep_id')
    if sales_rep_id:
        q = q.filter(models.Activity.sales_rep_id == sales_rep_id)
    if lead_id:
        q = q.filter(models.Activity.lead_id == lead_id)
    if company_id:
        q = q.filter(models.Activity.company_id == company_id)
    if contact_id:
        q = q.filter(models.Activity.contact_id == contact_id)
    if opportunity_id:
        q = q.filter(models.Activity.opportunity_id == opportunity_id)
    if customer_id:
        q = q.filter(models.Activity.customer_id == customer_id)
    if status_:
        q = q.filter(models.Activity.status == status_)
    if activity_type:
        q = q.filter(models.Activity.activity_type == activity_type)
    if year:
        q = q.filter(models.Activity.activity_date.startswith(year))
    if params.search:
        q = q.filter(models.Activity.subject.ilike(f"%{params.search}%"))
    return paginate_query(q, params, SORT_FIELDS, schemas.ActivityResponse)


@router.get("/summary", response_model=schemas.ActivitySummary)
def get_activity_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    from sqlalchemy import func
    from datetime import date
    
    base_q = db.query(models.Activity).filter(models.Activity.deleted_at == None)
    base_q = apply_rbac_filter(db, base_q, current_user, models.Activity, 'sales_rep_id')
    
    total_act = base_q.count()
    completed_act = base_q.filter(models.Activity.status == "Completed").count()
    pending_act = base_q.filter(models.Activity.status.in_(["Pending", "In Progress", "Planned"])).count()
    
    today_str = date.today().isoformat()
    overdue_act = base_q.filter(
        models.Activity.due_date < today_str,
        models.Activity.status != "Completed"
    ).count()
    
    counts = db.query(
        models.Activity.activity_type,
        func.count(models.Activity.activity_id)
    ).filter(models.Activity.deleted_at == None).group_by(models.Activity.activity_type).all()
    
    category_counts = [{"category": row[0], "count": row[1]} for row in counts]
    
    dates_q = db.query(models.Activity.activity_date).filter(models.Activity.deleted_at == None)
    dates_q = apply_rbac_filter(db, dates_q, current_user, models.Activity, 'sales_rep_id').distinct().all()
    years = sorted(list(set([d[0][:4] for d in dates_q if d[0]])), reverse=True)
    
    return schemas.ActivitySummary(
        total_activities=total_act,
        completed_activities=completed_act,
        pending_activities=pending_act,
        overdue_activities=overdue_act,
        category_counts=category_counts,
        years=years
    )


@router.get("/{activity_id}", response_model=schemas.ActivityResponse)
def get_activity(
    activity_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    obj = db.query(models.Activity).filter(
        models.Activity.activity_id == activity_id,
        models.Activity.deleted_at == None  # noqa: E711
    )
    obj = apply_rbac_filter(db, obj, current_user, models.Activity, 'sales_rep_id').first()
    if not obj:
        raise HTTPException(status_code=404, detail="Activity not found")
    return obj


@router.post("", response_model=schemas.ActivityResponse, status_code=status.HTTP_201_CREATED)
def create_activity(
    data: schemas.ActivityCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    if hasattr(data, 'sales_rep_id') and getattr(data, 'sales_rep_id', None):
        if not verify_assignment(db, current_user, getattr(data, 'sales_rep_id')):
            raise HTTPException(status_code=403, detail='Not authorized to assign record to this rep')
    now = _now()
    d = data.model_dump()
    if not d.get("sales_rep_id"):
        if current_user.rep_id:
            d["sales_rep_id"] = current_user.rep_id
        else:
            raise HTTPException(status_code=422, detail="sales_rep_id is required")
    obj = models.Activity(
        **d,
        activity_id=f"ACT-{uuid.uuid4().hex[:6].upper()}",
        created_at=now,
        updated_at=now,
        created_by=current_user.user_id,
        updated_by=current_user.user_id,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/{activity_id}", response_model=schemas.ActivityResponse)
def update_activity(
    activity_id: str,
    data: schemas.ActivityUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    obj = db.query(models.Activity).filter(
        models.Activity.activity_id == activity_id,
        models.Activity.deleted_at == None  # noqa: E711
    )
    obj = apply_rbac_filter(db, obj, current_user, models.Activity, 'sales_rep_id').first()
    if not obj:
        raise HTTPException(status_code=404, detail="Activity not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        if k == 'sales_rep_id' and v:
            if not verify_assignment(db, current_user, v):
                raise HTTPException(status_code=403, detail='Not authorized to assign record to this rep')
        setattr(obj, k, v)
    if data.status == "Completed" and not obj.completed_at:
        obj.completed_at = _now()
    obj.updated_at = _now()
    obj.updated_by = current_user.user_id
    db.commit()
    db.refresh(obj)
    return obj


@router.post("/{activity_id}/complete", response_model=schemas.ActivityResponse)
def complete_activity_endpoint(
    activity_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """Mark an activity as Completed."""
    return complete_activity(db, activity_id)


@router.delete("/{activity_id}", status_code=status.HTTP_200_OK)
def delete_activity(
    activity_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(RoleChecker(["Admin", "System Admin"])),
):
    soft_delete_activity(db, activity_id)
    return {"message": "Activity archived", "activity_id": activity_id}
