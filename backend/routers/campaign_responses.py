"""Campaign Responses router — read-only."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user

router = APIRouter(prefix="/api/campaign_responses", tags=["campaign_responses"])

@router.get("", response_model=List[schemas.CampaignResponseItem])
def list_campaign_responses(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=500),
    campaign_id: Optional[str] = None,
    contact_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    q = db.query(models.CampaignResponse)
    if campaign_id:
        q = q.filter(models.CampaignResponse.campaign_id == campaign_id)
    if contact_id:
        q = q.filter(models.CampaignResponse.contact_id == contact_id)
    return q.order_by(models.CampaignResponse.response_date.desc()).offset(skip).limit(limit).all()
