"""
lead_service.py — Lead lifecycle business logic.

Lead Conversion Workflow
------------------------
Conversion is executed atomically (single transaction).  Steps:

1. Validate the lead exists and is not already converted/deleted.
2. Look up the related Company by lead.company_id — always reuse it
   (companies are created at account-open time, not during conversion).
3. Look up the related Contact by lead.contact_id if present — reuse.
4. Optionally create an Opportunity if the conversion request asks for it.
   source_lead_id is preserved on the Opportunity.
5. Update lead_status → 'Converted' and set converted_at.
6. Append a LeadStatusHistory record.
7. Commit all changes in one atomic block.

What is NOT done:
- No CustomerTransaction is created (conversion ≠ revenue event).
- No Customer record is created (that happens after a deal closes).
- No new Company or Contact is force-created; they must already exist.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from .. import models


# ---------------------------------------------------------------------------
# Allowed lead statuses (ordered loosely by pipeline stage)
# ---------------------------------------------------------------------------

LEAD_STATUSES = [
    "New",
    "Contacted",
    "Qualified",
    "Proposal Sent",
    "Negotiation",
    "Converted",
    "Lost",
    "Disqualified",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _gen_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


# ---------------------------------------------------------------------------
# Status update with history
# ---------------------------------------------------------------------------

def update_lead_status(
    db: Session,
    lead: models.Lead,
    new_status: str,
    changed_by_rep_id: Optional[str] = None,
) -> models.LeadStatusHistory:
    """Update lead status and append a history record.

    Caller is responsible for db.commit().
    """
    if new_status not in LEAD_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid lead status '{new_status}'. Allowed: {LEAD_STATUSES}",
        )
    old_status = lead.lead_status
    now = _now_iso()
    lead.lead_status = new_status
    lead.updated_at = now

    history = models.LeadStatusHistory(
        history_id=_gen_id("LSH"),
        lead_id=lead.lead_id,
        status_from=old_status,
        status_to=new_status,
        changed_at=now,
        changed_by_rep_id=changed_by_rep_id,
    )
    db.add(history)
    return history


# ---------------------------------------------------------------------------
# Lead conversion
# ---------------------------------------------------------------------------

def convert_lead(
    db: Session,
    lead_id: str,
    create_opportunity: bool = True,
    opportunity_name: Optional[str] = None,
    owner_rep_id: Optional[str] = None,
    deal_value_inr: float = 0.0,
    changed_by_rep_id: Optional[str] = None,
) -> dict:
    """Convert a lead atomically.

    Returns a summary dict:
      {
          "lead_id": ...,
          "company_id": ...,
          "contact_id": ... or None,
          "opportunity_id": ... or None,
          "lead_status": "Converted",
          "history_id": ...
      }
    """
    # --- 1. Fetch and validate lead ---
    lead = db.query(models.Lead).filter(
        models.Lead.lead_id == lead_id,
        models.Lead.deleted_at == None,  # noqa: E711
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail=f"Lead {lead_id} not found")
    if lead.lead_status == "Converted":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Lead {lead_id} is already converted",
        )

    # --- 2. Verify company exists ---
    company = db.query(models.Company).filter(
        models.Company.company_id == lead.company_id,
        models.Company.deleted_at == None,  # noqa: E711
    ).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Company {lead.company_id} not found. Cannot convert lead.",
        )

    # --- 3. Verify contact exists if referenced ---
    contact_id = lead.contact_id
    if contact_id:
        contact = db.query(models.Contact).filter(
            models.Contact.contact_id == contact_id,
            models.Contact.deleted_at == None,  # noqa: E711
        ).first()
        if not contact:
            contact_id = None  # contact may have been soft-deleted; safe to proceed

    # --- 4. Optionally create Opportunity ---
    opp = None
    now = _now_iso()
    if create_opportunity:
        effective_owner = owner_rep_id or lead.assigned_rep_id
        if not effective_owner:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="owner_rep_id is required when creating an opportunity",
            )
        opp = models.Opportunity(
            opportunity_id=_gen_id("OPP"),
            company_id=lead.company_id,
            primary_contact_id=contact_id,
            source_lead_id=lead.lead_id,       # preserve link to original lead
            owner_rep_id=effective_owner,
            opportunity_name=opportunity_name or f"Opportunity from {lead.lead_id}",
            pipeline_stage="Qualification",
            deal_value_inr=deal_value_inr,
            probability_pct=20.0,
            created_at=now,
        )
        db.add(opp)

        # Create initial stage-history entry
        stage_hist = models.OpportunityStageHistory(
            history_id=_gen_id("OSH"),
            opportunity_id=opp.opportunity_id,
            stage_from=None,
            stage_to="Qualification",
            changed_at=now,
        )
        db.add(stage_hist)

    # --- 5 & 6. Update lead status → Converted + set converted_at ---
    history = update_lead_status(db, lead, "Converted", changed_by_rep_id)
    lead.converted_at = now

    # --- 7. Commit ---
    db.commit()
    db.refresh(lead)

    return {
        "lead_id": lead.lead_id,
        "company_id": lead.company_id,
        "contact_id": contact_id,
        "opportunity_id": opp.opportunity_id if opp else None,
        "lead_status": lead.lead_status,
        "history_id": history.history_id,
    }
