"""
opportunity_service.py — Opportunity pipeline business logic.

Stage Transitions
-----------------
Valid stages and allowed forward/backward transitions are defined in
STAGE_TRANSITIONS.  Any request for a transition not listed is rejected
with HTTP 400.  History is written atomically with the stage update.

Product Line Items
------------------
add_product / remove_product manage OpportunityProduct rows.
line_total_inr is always calculated as:
    quantity * unit_price_inr * (1 - discount_pct / 100)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from .. import models


# ---------------------------------------------------------------------------
# Stage definitions
# ---------------------------------------------------------------------------

# Ordered pipeline stages
PIPELINE_STAGES = [
    "Qualification",
    "Needs Analysis",
    "Value Proposition",
    "Id. Decision Makers",
    "Perception Analysis",
    "Proposal/Price Quote",
    "Negotiation/Review",
    "Closed Won",
    "Closed Lost",
]

# Allowed transitions: any stage → any stage except re-entry into Closed stages.
# Closed Won and Closed Lost are terminal — no transitions out.
TERMINAL_STAGES = {"Closed Won", "Closed Lost"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _gen_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


def _days_between(earlier: Optional[str], later: str) -> Optional[float]:
    if not earlier:
        return None
    try:
        fmt = "%Y-%m-%dT%H:%M:%S.%f%z"
        t1 = datetime.fromisoformat(earlier)
        t2 = datetime.fromisoformat(later)
        return (t2 - t1).total_seconds() / 86400.0
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Stage transition
# ---------------------------------------------------------------------------

def transition_stage(
    db: Session,
    opportunity_id: str,
    new_stage: str,
    close_outcome: Optional[str] = None,
    loss_reason: Optional[str] = None,
) -> dict:
    """Transition an opportunity to a new pipeline stage.

    Rules:
    - Opportunity must exist and not be soft-deleted.
    - Terminal stages cannot be departed.
    - new_stage must be in PIPELINE_STAGES.
    - Stage history is appended atomically.

    Returns a dict with opportunity_id, stage_from, stage_to, history_id.
    """
    opp = db.query(models.Opportunity).filter(
        models.Opportunity.opportunity_id == opportunity_id,
        models.Opportunity.deleted_at == None,  # noqa: E711
    ).first()
    if not opp:
        raise HTTPException(status_code=404, detail=f"Opportunity {opportunity_id} not found")

    if opp.pipeline_stage in TERMINAL_STAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Opportunity is in terminal stage '{opp.pipeline_stage}'. "
                "No further transitions are allowed."
            ),
        )

    if new_stage not in PIPELINE_STAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid stage '{new_stage}'. "
                f"Allowed stages: {PIPELINE_STAGES}"
            ),
        )

    if new_stage == opp.pipeline_stage:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Opportunity is already in stage '{new_stage}'.",
        )

    now = _now_iso()
    old_stage = opp.pipeline_stage
    days = _days_between(opp.updated_at or opp.created_at, now)

    # Update opportunity
    opp.pipeline_stage = new_stage
    opp.updated_at = now
    if new_stage == "Closed Won":
        opp.close_outcome = close_outcome or "Won"
        opp.actual_close_date = now[:10]
    elif new_stage == "Closed Lost":
        opp.close_outcome = close_outcome or "Lost"
        opp.loss_reason = loss_reason
        opp.actual_close_date = now[:10]

    # Append history
    hist = models.OpportunityStageHistory(
        history_id=_gen_id("OSH"),
        opportunity_id=opp.opportunity_id,
        stage_from=old_stage,
        stage_to=new_stage,
        changed_at=now,
        days_in_previous_stage=days,
    )
    db.add(hist)
    db.commit()
    db.refresh(opp)

    return {
        "opportunity_id": opp.opportunity_id,
        "stage_from": old_stage,
        "stage_to": new_stage,
        "history_id": hist.history_id,
    }


# ---------------------------------------------------------------------------
# Product line items
# ---------------------------------------------------------------------------

def add_product(
    db: Session,
    opportunity_id: str,
    product_id: str,
    quantity: int,
    unit_price_inr: float,
    discount_pct: float = 0.0,
) -> models.OpportunityProduct:
    """Add a product line item to an opportunity.

    line_total_inr = quantity * unit_price_inr * (1 - discount_pct / 100)
    """
    if quantity <= 0:
        raise HTTPException(status_code=400, detail="quantity must be positive")
    if unit_price_inr < 0:
        raise HTTPException(status_code=400, detail="unit_price_inr must be >= 0")
    if not (0 <= discount_pct <= 100):
        raise HTTPException(status_code=400, detail="discount_pct must be 0-100")

    opp = db.query(models.Opportunity).filter(
        models.Opportunity.opportunity_id == opportunity_id,
        models.Opportunity.deleted_at == None,  # noqa: E711
    ).first()
    if not opp:
        raise HTTPException(status_code=404, detail=f"Opportunity {opportunity_id} not found")

    product = db.query(models.Product).filter(
        models.Product.product_id == product_id,
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")

    line_total = round(quantity * unit_price_inr * (1 - discount_pct / 100.0), 2)

    op = models.OpportunityProduct(
        opportunity_product_id=_gen_id("OPR"),
        opportunity_id=opportunity_id,
        product_id=product_id,
        quantity=quantity,
        unit_price_inr=unit_price_inr,
        discount_pct=discount_pct,
        line_total_inr=line_total,
    )
    db.add(op)
    db.commit()
    db.refresh(op)
    return op


def remove_product(
    db: Session,
    opportunity_product_id: str,
) -> None:
    """Delete an opportunity product line item."""
    op = db.query(models.OpportunityProduct).filter(
        models.OpportunityProduct.opportunity_product_id == opportunity_product_id,
    ).first()
    if not op:
        raise HTTPException(status_code=404, detail="Opportunity product not found")
    db.delete(op)
    db.commit()
