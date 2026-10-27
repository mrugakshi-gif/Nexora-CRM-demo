"""Campaigns router — read-only with soft-delete filtering."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user, get_current_active_user, RoleChecker

from ..query_params import pagination_params, paginate_query, PageParams, PaginatedResponse

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])

SORT_FIELDS = {
    "campaign_name": models.Campaign.campaign_name,
    "start_date": models.Campaign.start_date,
    "budget": models.Campaign.budget_inr,
}

@router.get("/summary", response_model=schemas.CampaignSummaryResponse)
def get_campaign_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    from sqlalchemy import func

    total_campaigns = db.query(models.Campaign).filter(models.Campaign.deleted_at == None).count()
    total_budget = db.query(func.sum(models.Campaign.budget_inr)).filter(models.Campaign.deleted_at == None).scalar() or 0.0
    
    total_engagements = db.query(models.CampaignResponse).count()
    demo_requests = db.query(models.CampaignResponse).filter(
        models.CampaignResponse.response_type == "Requested Demo"
    ).count()

    category_counts_db = db.query(
        models.Campaign.campaign_type,
        func.count(models.Campaign.campaign_id)
    ).filter(
        models.Campaign.deleted_at == None
    ).group_by(
        models.Campaign.campaign_type
    ).all()

    category_counts = [{"category": row[0], "count": row[1]} for row in category_counts_db if row[0]]

    return schemas.CampaignSummaryResponse(
        total_campaigns=total_campaigns,
        total_budget=total_budget,
        total_engagements=total_engagements,
        demo_requests=demo_requests,
        category_counts=category_counts
    )

@router.get("", response_model=PaginatedResponse)
def list_campaigns(
    campaign_type: Optional[str] = None,
    target_industry_id: Optional[str] = None,
    owner_department_id: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    params: PageParams = Depends(pagination_params),
):
    q = db.query(models.Campaign).filter(models.Campaign.deleted_at == None)
    if campaign_type:
        q = q.filter(models.Campaign.campaign_type == campaign_type)
    if target_industry_id:
        q = q.filter(models.Campaign.target_industry_id == target_industry_id)
    if owner_department_id:
        q = q.filter(models.Campaign.owner_department_id == owner_department_id)
    if search:
        q = q.filter(models.Campaign.campaign_name.ilike(f"%{search}%"))
        
    return paginate_query(q, params, SORT_FIELDS, schemas.CampaignResponse)

@router.get("/{campaign_id}", response_model=schemas.CampaignResponse)
def get_campaign(
    campaign_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    obj = db.query(models.Campaign).filter(
        models.Campaign.campaign_id == campaign_id,
        models.Campaign.deleted_at == None
    ).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return obj


@router.post("", response_model=schemas.CampaignResponse, status_code=status.HTTP_201_CREATED)
def create_campaign(
    data: schemas.CampaignCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    from ..services.domain_services import create_campaign as ds_create_campaign
    return ds_create_campaign(db, data, current_user)


@router.put("/{campaign_id}", response_model=schemas.CampaignResponse)
def update_campaign(
    campaign_id: str,
    data: schemas.CampaignUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    from ..services.domain_services import update_campaign as ds_update_campaign
    return ds_update_campaign(db, campaign_id, data, current_user)


@router.delete("/{campaign_id}", status_code=status.HTTP_200_OK)
def delete_campaign(
    campaign_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(RoleChecker(["Admin", "System Admin"])),
):
    from ..services.domain_services import soft_delete_campaign
    soft_delete_campaign(db, campaign_id)
    return {"message": "Campaign archived", "campaign_id": campaign_id}
