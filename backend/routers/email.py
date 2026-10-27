import uuid
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from .. import models
from .. import schemas
from ..database import get_db
from ..deps import get_current_active_user
from ..services.email_service import EmailService
from ..services.ai_email_generator import (
    AIEmailGenerator,
    AIProviderUnavailableError,
    AIProviderConfigError,
    is_transient_error,
)

router = APIRouter(prefix="/api", tags=["email", "settings"])

@router.get("/settings/email-preferences", response_model=schemas.UserSettingsResponse)
def get_email_preferences(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    settings = db.query(models.UserSettings).filter(models.UserSettings.user_id == current_user.user_id).first()
    if not settings:
        # Return default if not exists without saving to avoid side-effects in GET
        return schemas.UserSettingsResponse(
            setting_id=f"SET-{uuid.uuid4().hex[:8].upper()}",
            user_id=current_user.user_id,
            email_notifications=True,
            updated_at=datetime.utcnow()
        )
    return settings

@router.put("/settings/email-preferences", response_model=schemas.UserSettingsResponse)
def update_email_preferences(
    preferences: schemas.UserSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    settings = db.query(models.UserSettings).filter(models.UserSettings.user_id == current_user.user_id).first()
    if not settings:
        settings = models.UserSettings(
            setting_id=f"SET-{uuid.uuid4().hex[:8].upper()}",
            user_id=current_user.user_id,
            email_notifications=preferences.email_notifications
        )
        db.add(settings)
    else:
        settings.email_notifications = preferences.email_notifications
        
    db.commit()
    db.refresh(settings)
    return settings

@router.post("/settings/test-email")
def test_email(
    req: schemas.TestEmailRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    # Only allow explicit user action tests
    email_service = EmailService()
    success = email_service.send_email(
        db=db,
        to_email=req.recipient_email,
        subject="Nexora CRM - Test Email",
        body_text="This is a test email sent from Nexora CRM to verify the email configuration.",
        body_html="<p>This is a <b>test email</b> sent from Nexora CRM to verify the email configuration.</p>",
        email_type="Test",
        user_id=current_user.user_id
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send test email. Check server logs or email history.")
    
    return {"message": "Test email sent successfully"}

@router.get("/settings/email-history", response_model=List[schemas.EmailHistoryResponse])
def get_email_history(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    # Admin can see all, regular user sees their own tests/notifications
    if current_user.role in ["Admin", "System Admin"]:
        history = db.query(models.EmailHistory).order_by(models.EmailHistory.sent_at.desc()).limit(100).all()
    else:
        history = db.query(models.EmailHistory).filter(models.EmailHistory.user_id == current_user.user_id).order_by(models.EmailHistory.sent_at.desc()).limit(100).all()
    return history

@router.post("/email/generate", response_model=schemas.EmailGenerationResponse)
def generate_email_draft(
    req: schemas.EmailGenerationRequest,
    current_user: models.User = Depends(get_current_active_user)
):
    try:
        generator = AIEmailGenerator()
        draft = generator.generate_email(
            alert_type=req.alert_type,
            context=req.context,
            recipient_name=req.recipient_name
        )
        return schemas.EmailGenerationResponse(
            subject=draft["subject"],
            text_body=draft["text_body"],
            html_body=draft["html_body"],
            email_type=req.alert_type
        )
    except AIProviderUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The AI model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again in a moment."
        )
    except AIProviderConfigError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        if is_transient_error(e):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The AI model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again in a moment."
            )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to generate email content. Please try again.")

@router.post("/email/send-draft")
def send_email_draft(
    req: schemas.SendDraftRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    if current_user.role not in ["Admin", "System Admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")

    email_service = EmailService()
    success = email_service.send_email(
        db=db,
        to_email=req.recipient_email,
        subject=req.subject,
        body_text=req.text_body,
        body_html=req.html_body,
        email_type=req.email_type,
        user_id=current_user.user_id
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send draft email.")
    return {"message": "Draft email sent successfully"}
