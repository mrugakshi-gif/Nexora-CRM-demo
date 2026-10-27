"""Contacts router — full CRUD with soft-delete and pagination."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_active_user, RoleChecker
from ..query_params import pagination_params, paginate_query, PageParams, PaginatedResponse

router = APIRouter(prefix="/api/contacts", tags=["contacts"])

SORT_FIELDS = {
    "full_name": models.Contact.full_name,
    "created_at": models.Contact.created_at,
    "job_title": models.Contact.job_title,
}

def _now():
    return datetime.now(timezone.utc).isoformat()


@router.get("", response_model=PaginatedResponse)
def list_contacts(
    company_id: Optional[str] = None,
    is_decision_maker: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
    params: PageParams = Depends(pagination_params),
):
    q = db.query(models.Contact).filter(models.Contact.deleted_at == None)  # noqa: E711
    if company_id:
        q = q.filter(models.Contact.company_id == company_id)
    if is_decision_maker is not None:
        q = q.filter(models.Contact.is_decision_maker == is_decision_maker)
    if params.search:
        q = q.filter(models.Contact.full_name.ilike(f"%{params.search}%"))
    return paginate_query(q, params, SORT_FIELDS, schemas.ContactResponse)


@router.get("/{contact_id}", response_model=schemas.ContactResponse)
def get_contact(
    contact_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    obj = db.query(models.Contact).filter(
        models.Contact.contact_id == contact_id,
        models.Contact.deleted_at == None
    ).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Contact not found")
    return obj


@router.post("", response_model=schemas.ContactResponse, status_code=status.HTTP_201_CREATED)
def create_contact(
    data: schemas.ContactCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    company = db.query(models.Company).filter(
        models.Company.company_id == data.company_id,
        models.Company.deleted_at == None  # noqa: E711
    ).first()
    if not company:
        raise HTTPException(status_code=422, detail=f"Company {data.company_id} not found")
    now = _now()
    obj = models.Contact(
        **data.model_dump(),
        contact_id=f"CONT-{uuid.uuid4().hex[:6].upper()}",
        created_at=now,
        updated_at=now,
        created_by=current_user.user_id,
        updated_by=current_user.user_id,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/{contact_id}", response_model=schemas.ContactResponse)
def update_contact(
    contact_id: str,
    data: schemas.ContactUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    obj = db.query(models.Contact).filter(
        models.Contact.contact_id == contact_id,
        models.Contact.deleted_at == None  # noqa: E711
    ).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Contact not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    obj.updated_at = _now()
    obj.updated_by = current_user.user_id
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{contact_id}", status_code=status.HTTP_200_OK)
def delete_contact(
    contact_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(RoleChecker(["Admin", "System Admin"])),
):
    obj = db.query(models.Contact).filter(
        models.Contact.contact_id == contact_id,
        models.Contact.deleted_at == None  # noqa: E711
    ).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Contact not found")
    obj.deleted_at = _now()
    obj.updated_by = current_user.user_id
    db.commit()
    return {"message": "Contact archived", "contact_id": contact_id}
