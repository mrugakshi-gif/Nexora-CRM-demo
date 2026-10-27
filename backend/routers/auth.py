from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session
from backend.models import User
from backend.deps import get_current_active_user, get_db
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/auth", tags=["auth"])

class UserUpdate(BaseModel):
    full_name: str

@router.get("/me")
def read_users_me(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get current logged-in user profile from the CRM database.
    This relies on the Firebase token being verified by the dependency.
    """
    from backend.rbac import get_user_effective_role
    return {
        "user_id": current_user.user_id,
        "email": current_user.email,
        "role": current_user.role,
        "effective_role": get_user_effective_role(db, current_user),
        "is_active": current_user.is_active,
        "firebase_uid": current_user.firebase_uid,
        "full_name": current_user.sales_rep.full_name if current_user.sales_rep else None,
        "created_at": current_user.created_at,
        "updated_at": current_user.updated_at
    }

@router.put("/me")
def update_users_me(
    update_data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update the current logged-in user's profile.
    """
    if current_user.sales_rep:
        current_user.sales_rep.full_name = update_data.full_name
        db.commit()
        db.refresh(current_user)

    return {
        "user_id": current_user.user_id,
        "email": current_user.email,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "firebase_uid": current_user.firebase_uid,
        "full_name": current_user.sales_rep.full_name if current_user.sales_rep else None,
        "created_at": current_user.created_at,
        "updated_at": current_user.updated_at
    }
