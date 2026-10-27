"""Sales Reps router — read-only."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user

router = APIRouter(prefix="/api/sales_reps", tags=["sales_reps"])

@router.get("", response_model=List[schemas.SalesRepResponse])
def list_sales_reps(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=500),
    department_id: Optional[str] = None,
    territory_id: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    q = db.query(models.SalesRep)
    if department_id:
        q = q.filter(models.SalesRep.department_id == department_id)
    if territory_id:
        q = q.filter(models.SalesRep.territory_id == territory_id)
    if is_active is not None:
        q = q.filter(models.SalesRep.is_active == is_active)
    return q.order_by(models.SalesRep.full_name).offset(skip).limit(limit).all()

@router.get("/{rep_id}", response_model=schemas.SalesRepResponse)
def get_sales_rep(
    rep_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    obj = db.query(models.SalesRep).filter(models.SalesRep.rep_id == rep_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Sales Rep not found")
    return obj
