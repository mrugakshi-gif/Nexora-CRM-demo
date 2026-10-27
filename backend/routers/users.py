"""Users router — read-only with soft-delete filtering."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user

router = APIRouter(prefix="/api/users", tags=["users"])

@router.get("", response_model=List[schemas.UserResponse])
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=500),
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    q = db.query(models.User).filter(models.User.deleted_at == None)
    if role:
        q = q.filter(models.User.role == role)
    if is_active is not None:
        q = q.filter(models.User.is_active == is_active)
    return q.order_by(models.User.email).offset(skip).limit(limit).all()

@router.get("/{user_id}", response_model=schemas.UserResponse)
def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    obj = db.query(models.User).filter(
        models.User.user_id == user_id,
        models.User.deleted_at == None
    ).first()
    if not obj:
        raise HTTPException(status_code=404, detail="User not found")
    return obj

from pydantic import BaseModel
class EmailUpdate(BaseModel):
    email: str

@router.put("/{user_id}/email", response_model=schemas.UserResponse)
def update_user_email(
    user_id: str,
    payload: EmailUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if current_user.role not in ["Admin", "System Admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")

    obj = db.query(models.User).filter(
        models.User.user_id == user_id,
        models.User.deleted_at == None
    ).first()
    if not obj:
        raise HTTPException(status_code=404, detail="User not found")
        
    obj.email = payload.email
    db.commit()
    db.refresh(obj)
    return obj
