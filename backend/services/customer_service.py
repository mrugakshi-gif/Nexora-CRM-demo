"""
customer_service.py — Customer lifecycle helpers.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .. import models


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_customer_360(db: Session, customer_id: str) -> dict:
    """Return a 360-degree view of a customer."""
    customer = db.query(models.Customer).filter(
        models.Customer.customer_id == customer_id,
        models.Customer.deleted_at == None,  # noqa: E711
    ).first()
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")

    transactions = (
        db.query(models.CustomerTransaction)
        .filter(
            models.CustomerTransaction.customer_id == customer_id,
            models.CustomerTransaction.deleted_at == None,  # noqa: E711
        )
        .order_by(models.CustomerTransaction.transaction_date.desc())
        .limit(20)
        .all()
    )
    support_cases = (
        db.query(models.SupportCase)
        .filter(
            models.SupportCase.customer_id == customer_id,
            models.SupportCase.deleted_at == None,  # noqa: E711
        )
        .order_by(models.SupportCase.opened_at.desc())
        .limit(20)
        .all()
    )
    activities = (
        db.query(models.Activity)
        .filter(
            models.Activity.customer_id == customer_id,
            models.Activity.deleted_at == None,  # noqa: E711
        )
        .order_by(models.Activity.activity_date.desc())
        .limit(20)
        .all()
    )

    return {
        "customer_id": customer.customer_id,
        "company_id": customer.company_id,
        "customer_since": customer.customer_since,
        "customer_status": customer.customer_status,
        "customer_tier": customer.customer_tier,
        "contract_type": customer.contract_type,
        "renewal_date": customer.renewal_date,
        "csm_rep_id": customer.csm_rep_id,
        "transactions_count": len(transactions),
        "support_cases_count": len(support_cases),
        "activities_count": len(activities),
        "transactions": transactions,
        "support_cases": support_cases,
        "activities": activities,
    }


def soft_delete_customer(db: Session, customer_id: str) -> None:
    customer = db.query(models.Customer).filter(
        models.Customer.customer_id == customer_id,
        models.Customer.deleted_at == None,  # noqa: E711
    ).first()
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
    customer.deleted_at = _now_iso()
    db.commit()
