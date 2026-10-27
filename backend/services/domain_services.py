"""Lightweight service stubs for transaction, campaign, activity, and support domains."""
from __future__ import annotations

from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy.orm import Session
from .. import models


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# transaction_service
# ---------------------------------------------------------------------------

def soft_delete_transaction(db: Session, transaction_id: str) -> None:
    tx = db.query(models.CustomerTransaction).filter(
        models.CustomerTransaction.transaction_id == transaction_id,
        models.CustomerTransaction.deleted_at == None,  # noqa: E711
    ).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    tx.deleted_at = _now_iso()
    db.commit()


# ---------------------------------------------------------------------------
# campaign_service
# ---------------------------------------------------------------------------
import uuid
from .. import schemas

def create_campaign(db: Session, data: schemas.CampaignCreate, user: models.User) -> models.Campaign:
    # Foreign key validations
    if data.target_industry_id:
        ind = db.query(models.Industry).filter(models.Industry.industry_id == data.target_industry_id).first()
        if not ind:
            raise HTTPException(status_code=400, detail="Invalid target_industry_id")
    dept = db.query(models.Department).filter(models.Department.department_id == data.owner_department_id).first()
    if not dept:
        raise HTTPException(status_code=400, detail="Invalid owner_department_id")
        
    now = _now_iso()
    obj = models.Campaign(
        **data.model_dump(),
        campaign_id=f"CAMP-{uuid.uuid4().hex[:6].upper()}",
        updated_at=now,
        created_by=user.user_id,
        updated_by=user.user_id,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_campaign(db: Session, campaign_id: str, data: schemas.CampaignUpdate, user: models.User) -> models.Campaign:
    obj = db.query(models.Campaign).filter(
        models.Campaign.campaign_id == campaign_id,
        models.Campaign.deleted_at == None,  # noqa: E711
    ).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    if data.target_industry_id is not None:
        ind = db.query(models.Industry).filter(models.Industry.industry_id == data.target_industry_id).first()
        if not ind:
            raise HTTPException(status_code=400, detail="Invalid target_industry_id")
    if data.owner_department_id is not None:
        dept = db.query(models.Department).filter(models.Department.department_id == data.owner_department_id).first()
        if not dept:
            raise HTTPException(status_code=400, detail="Invalid owner_department_id")

    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
        
    obj.updated_at = _now_iso()
    obj.updated_by = user.user_id
    db.commit()
    db.refresh(obj)
    return obj


def soft_delete_campaign(db: Session, campaign_id: str) -> None:
    obj = db.query(models.Campaign).filter(
        models.Campaign.campaign_id == campaign_id,
        models.Campaign.deleted_at == None,  # noqa: E711
    ).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Campaign not found")
    obj.deleted_at = _now_iso()
    db.commit()


# ---------------------------------------------------------------------------
# activity_service
# ---------------------------------------------------------------------------

def complete_activity(db: Session, activity_id: str) -> models.Activity:
    act = db.query(models.Activity).filter(
        models.Activity.activity_id == activity_id,
        models.Activity.deleted_at == None,  # noqa: E711
    ).first()
    if not act:
        raise HTTPException(status_code=404, detail="Activity not found")
    now = _now_iso()
    act.status = "Completed"
    act.completed_at = now
    act.updated_at = now
    db.commit()
    db.refresh(act)
    return act


def soft_delete_activity(db: Session, activity_id: str) -> None:
    act = db.query(models.Activity).filter(
        models.Activity.activity_id == activity_id,
        models.Activity.deleted_at == None,  # noqa: E711
    ).first()
    if not act:
        raise HTTPException(status_code=404, detail="Activity not found")
    act.deleted_at = _now_iso()
    db.commit()


# ---------------------------------------------------------------------------
# support_service
# ---------------------------------------------------------------------------

SUPPORT_STATUSES = ["Open", "In Progress", "Resolved", "Closed", "Escalated"]


def update_support_case_status(
    db: Session, case_id: str, new_status: str, satisfaction_score: float | None = None
) -> models.SupportCase:
    if new_status not in SUPPORT_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{new_status}'. Allowed: {SUPPORT_STATUSES}",
        )
    case = db.query(models.SupportCase).filter(
        models.SupportCase.case_id == case_id,
        models.SupportCase.deleted_at == None,  # noqa: E711
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Support case not found")
    now = _now_iso()
    case.status = new_status
    case.updated_at = now
    if new_status in ("Resolved", "Closed"):
        case.resolved_at = case.resolved_at or now
    if satisfaction_score is not None:
        if not (1.0 <= satisfaction_score <= 5.0):
            raise HTTPException(status_code=400, detail="satisfaction_score must be 1–5")
        case.satisfaction_score = satisfaction_score
    db.commit()
    db.refresh(case)
    return case


def soft_delete_support_case(db: Session, case_id: str) -> None:
    case = db.query(models.SupportCase).filter(
        models.SupportCase.case_id == case_id,
        models.SupportCase.deleted_at == None,  # noqa: E711
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Support case not found")
    case.deleted_at = _now_iso()
    db.commit()
