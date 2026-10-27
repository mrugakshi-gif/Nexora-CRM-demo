"""Opportunities router — full CRUD with soft-delete, pagination, and stage-transition workflow."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_active_user, RoleChecker
from ..rbac import apply_rbac_filter, verify_assignment
from ..query_params import pagination_params, paginate_query, PageParams, PaginatedResponse
from ..services.opportunity_service import (
    transition_stage,
    add_product,
    remove_product,
    PIPELINE_STAGES,
)

router = APIRouter(prefix="/api/opportunities", tags=["opportunities"])

SORT_FIELDS = {
    "created_at": models.Opportunity.created_at,
    "deal_value_inr": models.Opportunity.deal_value_inr,
    "probability_pct": models.Opportunity.probability_pct,
    "expected_close_date": models.Opportunity.expected_close_date,
}


def _now():
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Pydantic request bodies
# ---------------------------------------------------------------------------

class StageTransitionRequest(BaseModel):
    new_stage: str
    close_outcome: Optional[str] = None
    loss_reason: Optional[str] = None


class AddProductRequest(BaseModel):
    product_id: str
    quantity: int
    unit_price_inr: float
    discount_pct: float = 0.0


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

@router.get("", response_model=PaginatedResponse)
def list_opportunities(
    pipeline_stage: Optional[str] = None,
    owner_rep_id: Optional[str] = None,
    company_id: Optional[str] = None,
    close_outcome: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
    params: PageParams = Depends(pagination_params),
):
    q = db.query(models.Opportunity).filter(models.Opportunity.deleted_at == None)  # noqa: E711
    q = apply_rbac_filter(db, q, current_user, models.Opportunity, 'owner_rep_id')
    if pipeline_stage:
        if "," in pipeline_stage:
            q = q.filter(models.Opportunity.pipeline_stage.in_(pipeline_stage.split(",")))
        else:
            q = q.filter(models.Opportunity.pipeline_stage == pipeline_stage)
    if owner_rep_id:
        q = q.filter(models.Opportunity.owner_rep_id == owner_rep_id)
    if company_id:
        q = q.filter(models.Opportunity.company_id == company_id)
    if close_outcome:
        q = q.filter(models.Opportunity.close_outcome == close_outcome)
    if params.search:
        q = q.filter(models.Opportunity.opportunity_name.ilike(f"%{params.search}%"))
    return paginate_query(q, params, SORT_FIELDS, schemas.OpportunityResponse)


@router.get("/{opportunity_id}", response_model=schemas.OpportunityResponse)
def get_opportunity(
    opportunity_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    obj = db.query(models.Opportunity).filter(
        models.Opportunity.opportunity_id == opportunity_id,
        models.Opportunity.deleted_at == None  # noqa: E711
    )
    obj = apply_rbac_filter(db, obj, current_user, models.Opportunity, 'owner_rep_id').first()
    if not obj:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return obj


@router.post("", response_model=schemas.OpportunityResponse, status_code=status.HTTP_201_CREATED)
def create_opportunity(
    data: schemas.OpportunityCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    company = db.query(models.Company).filter(
        models.Company.company_id == data.company_id,
        models.Company.deleted_at == None  # noqa: E711
    ).first()
    if not company:
        raise HTTPException(status_code=422, detail=f"Company {data.company_id} not found")
    if data.pipeline_stage not in PIPELINE_STAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid pipeline_stage. Allowed: {PIPELINE_STAGES}"
        )
    if hasattr(data, 'owner_rep_id') and getattr(data, 'owner_rep_id', None):
        if not verify_assignment(db, current_user, getattr(data, 'owner_rep_id')):
            raise HTTPException(status_code=403, detail='Not authorized to assign record to this rep')
    now = _now()
    obj = models.Opportunity(
        **data.model_dump(),
        opportunity_id=f"OPP-{uuid.uuid4().hex[:6].upper()}",
        created_at=now,
        updated_at=now,
        created_by=current_user.user_id,
        updated_by=current_user.user_id,
    )
    db.add(obj)
    # Create initial stage history
    db.add(models.OpportunityStageHistory(
        history_id=f"OSH-{uuid.uuid4().hex[:8].upper()}",
        opportunity_id=obj.opportunity_id,
        stage_from=None,
        stage_to=obj.pipeline_stage,
        changed_at=now,
    ))
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/{opportunity_id}", response_model=schemas.OpportunityResponse)
def update_opportunity(
    opportunity_id: str,
    data: schemas.OpportunityUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    obj = db.query(models.Opportunity).filter(
        models.Opportunity.opportunity_id == opportunity_id,
        models.Opportunity.deleted_at == None  # noqa: E711
    )
    obj = apply_rbac_filter(db, obj, current_user, models.Opportunity, 'owner_rep_id').first()
    if not obj:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        if k == 'owner_rep_id' and v:
            if not verify_assignment(db, current_user, v):
                raise HTTPException(status_code=403, detail='Not authorized to assign record to this rep')
        setattr(obj, k, v)
    obj.updated_at = _now()
    obj.updated_by = current_user.user_id
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{opportunity_id}", status_code=status.HTTP_200_OK)
def delete_opportunity(
    opportunity_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(RoleChecker(["Admin", "System Admin"])),
):
    obj = db.query(models.Opportunity).filter(
        models.Opportunity.opportunity_id == opportunity_id,
        models.Opportunity.deleted_at == None  # noqa: E711
    )
    obj = apply_rbac_filter(db, obj, current_user, models.Opportunity, 'owner_rep_id').first()
    if not obj:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    obj.deleted_at = _now()
    obj.updated_by = current_user.user_id
    db.commit()
    return {"message": "Opportunity archived", "opportunity_id": opportunity_id}


# ---------------------------------------------------------------------------
# History & Products
# ---------------------------------------------------------------------------

@router.get("/{opportunity_id}/history", response_model=list[schemas.OpportunityStageHistoryResponse])
def get_opportunity_history(
    opportunity_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    opp = db.query(models.Opportunity).filter(
        models.Opportunity.opportunity_id == opportunity_id
    )
    opp = apply_rbac_filter(db, opp, current_user, models.Opportunity, 'owner_rep_id').first()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return (
        db.query(models.OpportunityStageHistory)
        .filter(models.OpportunityStageHistory.opportunity_id == opportunity_id)
        .order_by(models.OpportunityStageHistory.changed_at)
        .all()
    )


@router.get("/{opportunity_id}/products", response_model=list[schemas.OpportunityProductResponse])
def get_opportunity_products(
    opportunity_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    opp = db.query(models.Opportunity).filter(
        models.Opportunity.opportunity_id == opportunity_id
    )
    opp = apply_rbac_filter(db, opp, current_user, models.Opportunity, 'owner_rep_id').first()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return (
        db.query(models.OpportunityProduct)
        .filter(models.OpportunityProduct.opportunity_id == opportunity_id)
        .all()
    )


# ---------------------------------------------------------------------------
# Business Logic endpoints
# ---------------------------------------------------------------------------

@router.post("/{opportunity_id}/stage-transition", status_code=status.HTTP_200_OK)
def stage_transition(
    opportunity_id: str,
    body: StageTransitionRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """Transition opportunity to a new pipeline stage with validation and history."""
    return transition_stage(
        db=db,
        opportunity_id=opportunity_id,
        new_stage=body.new_stage,
        close_outcome=body.close_outcome,
        loss_reason=body.loss_reason,
    )


@router.post("/{opportunity_id}/products", response_model=schemas.OpportunityProductResponse,
             status_code=status.HTTP_201_CREATED)
def add_opportunity_product(
    opportunity_id: str,
    body: AddProductRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """Add a product line item and calculate line_total_inr."""
    return add_product(
        db=db,
        opportunity_id=opportunity_id,
        product_id=body.product_id,
        quantity=body.quantity,
        unit_price_inr=body.unit_price_inr,
        discount_pct=body.discount_pct,
    )


@router.delete("/products/{opportunity_product_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_opportunity_product(
    opportunity_product_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(RoleChecker(["Admin", "System Admin"])),
):
    """Remove a product line item from an opportunity."""
    remove_product(db=db, opportunity_product_id=opportunity_product_id)


@router.get("/{opportunity_id}/health", response_model=schemas.DealHealthResponse)
def get_opportunity_deal_health(
    opportunity_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """Retrieve dedicated deal risk and health assessment for this opportunity."""
    from ..services.health_service import calculate_deal_health
    try:
        return calculate_deal_health(db, opportunity_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

