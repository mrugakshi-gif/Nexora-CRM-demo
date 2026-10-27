"""
deps.py — Shared FastAPI dependencies: DB session, JWT-based authentication,
and role-based access control.

Authentication mode is controlled by CRM_AUTH_MODE env var:
  - demo  : any active user in the DB can authenticate using CRM_DEMO_PASSWORD
             (bcrypt-hashed at startup). This mode is ONLY for dev/demo.
  - strict: reserved for production — requires real password_hash in DB row.
             (Not yet implemented; login rejects if mode is 'strict' and
              password_hash is NULL.)

NEVER hardcode CRM_DEMO_PASSWORD in source code.
"""
import os
import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from . import models
from .database import get_db

logger = logging.getLogger(__name__)

# We leave tokenUrl for swagger UI even if we don't handle local login
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="dummy")

# ---------------------------------------------------------------------------
# Auth-mode helpers
# ---------------------------------------------------------------------------

AUTH_MODE = os.getenv("CRM_AUTH_MODE", "demo").lower()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    """Verify Firebase ID token and return the associated CRM User row."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Import firebase_admin inside function to avoid circular imports if any,
    # but top level is also fine. We'll use firebase_admin.auth
    from firebase_admin import auth
    
    try:
        decoded_token = auth.verify_id_token(token)
        print(f"DEBUG: Token verified. UID: {decoded_token.get('uid')}")
    except Exception as e:
        print(f"DEBUG: Token validation failed exactly: {repr(e)}")
        raise credentials_exception
        
    uid = decoded_token.get("uid")
    email = decoded_token.get("email")
    email_verified = decoded_token.get("email_verified", False)
    
    if not uid:
        raise credentials_exception


    # First attempt: find by firebase_uid
    user = db.query(models.User).filter(
        models.User.firebase_uid == uid,
        models.User.deleted_at == None,  # noqa: E711
    ).first()
    
    if user:
        return user
        
    # Second attempt: map by email if email is verified
    if not email or not email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Firebase user must have a verified email to link account."
        )
        
    user_by_email = db.query(models.User).filter(
        models.User.email == email,
        models.User.deleted_at == None,  # noqa: E711
    ).first()
    
    if not user_by_email:
        logger.warning("CRM account not found for email: %s", email)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"CRM account not found for this email: {email}"
        )
        
    # Check if this CRM user is ALREADY linked to a different Firebase UID
    if user_by_email.firebase_uid is not None and user_by_email.firebase_uid != uid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conflicting mapping: CRM account already linked to another Firebase UID."
        )
        
    # Link accounts
    user_by_email.firebase_uid = uid
    db.commit()
    db.refresh(user_by_email)
    
    return user_by_email


def get_current_active_user(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


class RoleChecker:
    """Dependency factory for role-based access control.

    Usage:
        @router.delete("/{id}", dependencies=[Depends(RoleChecker(["admin"]))])
    """
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = [r.lower() for r in allowed_roles]

    def __call__(self, current_user: models.User = Depends(get_current_active_user)):
        if current_user.role.lower() not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted for your role",
            )
        return current_user
