from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User
from ..deps import get_current_active_user
from ..services.automation_service import run_automation

router = APIRouter(prefix="/api/automation", tags=["automation"])

@router.post("/dry-run")
def automation_dry_run(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if current_user.role not in ["Admin", "Manager"]:
        raise HTTPException(status_code=403, detail="Admin/Manager access required")
    
    try:
        results = run_automation(db, mode="DRY_RUN")
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/run")
def automation_run(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if current_user.role not in ["Admin", "System Admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        results = run_automation(db)
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from pydantic import BaseModel
from typing import Dict, Any
from ..models import SystemSettings
import json

class AutomationSettingsUpdate(BaseModel):
    enabled: bool
    mode: str
    interval_minutes: int
    test_email: str
    rules: Dict[str, bool]

@router.get("/settings")
def get_automation_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if current_user.role not in ["Admin", "System Admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
        
    settings = db.query(SystemSettings).filter(SystemSettings.setting_key == "automation_config").first()
    if settings:
        config = json.loads(settings.setting_value)
    else:
        config = {
            "enabled": False,
            "mode": "DRY_RUN",
            "interval_minutes": 60,
            "test_email": "",
            "rules": {
                "support": True,
                "leads": True,
                "opportunities": True,
                "renewals": True,
                "churn": True
            }
        }
    return {"status": "success", "data": config}

@router.post("/settings")
def update_automation_settings(
    update: AutomationSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if current_user.role not in ["Admin", "System Admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
        
    config = update.model_dump()
    settings = db.query(SystemSettings).filter(SystemSettings.setting_key == "automation_config").first()
    if settings:
        settings.setting_value = json.dumps(config)
    else:
        new_settings = SystemSettings(
            setting_key="automation_config",
            setting_value=json.dumps(config)
        )
        db.add(new_settings)
    db.commit()
    
    # Also optionally update env vars in process so main loop could pick it up
    import os
    os.environ["AUTOMATION_EMAIL_MODE"] = config["mode"]
    os.environ["AUTOMATION_ENABLED"] = str(config["enabled"]).lower()
    os.environ["AUTOMATION_INTERVAL_MINUTES"] = str(config["interval_minutes"])
    os.environ["AUTOMATION_TEST_EMAIL"] = config["test_email"]
    
    return {"status": "success"}

@router.get("/preview-candidates")
def get_preview_candidates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if current_user.role not in ["Admin", "System Admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    from ..services.automation_service import get_automation_candidates
    from ..models import Customer, Lead
    
    candidates = get_automation_candidates(db)
    users = {u.user_id: u.email for u in db.query(User).all()}
    
    previews = []
    for c in candidates:
        email = users.get(c["recipient_id"])
        
        label = "Unknown"
        if c["type"] == "High Priority Support Alert":
            customer = db.query(Customer).filter(Customer.customer_id == c["context"]["customer_id"]).first()
            comp_name = customer.company.company_name if customer and customer.company else "Unknown Company"
            label = f"{c['context']['case_id']} — {comp_name}"
            
        elif c["type"] == "Opportunity Closing Soon":
            label = f"{c['context']['opportunity_id']} — {c['context']['opportunity_name']}"
            
        elif c["type"] == "Upcoming Customer Renewal":
            customer = db.query(Customer).filter(Customer.customer_id == c["context"]["customer_id"]).first()
            comp_name = customer.company.company_name if customer and customer.company else "Unknown Company"
            label = f"{c['context']['customer_id']} — {comp_name}"
            
        elif c["type"] == "New High-Value Lead":
            lead = db.query(Lead).filter(Lead.lead_id == c["context"]["lead_id"]).first()
            comp_name = lead.company.company_name if lead and lead.company else "Unknown Company"
            label = f"{c['context']['lead_id']} — {comp_name}"
            
        elif c["type"] == "High Churn Risk Alert":
            label = f"{c['context']['customer_id']} — {c['context'].get('entity_name', 'Unknown')}"
            
        previews.append({
            "type": c["type"],
            "event_key": c["event_key"],
            "label": label,
            "recipient_email": email,
            "context": c["context"]
        })
        
    return {"status": "success", "data": previews}

class ActionTaskCreate(BaseModel):
    action_type: str
    reason: str
    customer_id: str = None
    company_id: str = None
    opportunity_id: str = None
    lead_id: str = None
    support_case_id: str = None
    trigger_email: bool = False

@router.post("/create-task")
def create_action_task(
    payload: ActionTaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    from ..models import Customer, Lead, Opportunity, SupportCase, Activity, EmailHistory
    from ..rbac import verify_assignment
    import uuid
    from datetime import datetime, timezone, timedelta
    from ..services.email_service import EmailService
    from ..services.ai_email_generator import AIEmailGenerator

    # 1. Resolve Entity & Owner
    owner_id = None
    entity_name = "Unknown"
    event_key = ""
    email_alert_type = ""
    
    if payload.action_type == "High Churn Risk" and payload.customer_id:
        cust = db.query(Customer).filter(Customer.customer_id == payload.customer_id).first()
        if not cust:
            raise HTTPException(status_code=404, detail="Customer not found")
        owner_id = cust.csm_rep_id
        entity_name = cust.company.company_name if cust.company else "Unknown"
        event_key = f"churn_{cust.customer_id}_{datetime.now().strftime('%Y-%m')}"
        email_alert_type = "High Churn Risk Alert"
        
    elif payload.action_type == "Opportunity Closing Soon" and payload.opportunity_id:
        opp = db.query(Opportunity).filter(Opportunity.opportunity_id == payload.opportunity_id).first()
        if not opp:
            raise HTTPException(status_code=404, detail="Opportunity not found")
        owner_id = opp.owner_rep_id
        entity_name = opp.opportunity_name
        event_key = f"opp_{opp.opportunity_id}_closing_{opp.expected_close_date}"
        email_alert_type = "Opportunity Closing Soon"
        
    elif payload.action_type == "High-Priority Support" and payload.support_case_id:
        case = db.query(SupportCase).filter(SupportCase.case_id == payload.support_case_id).first()
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        if case.customer and case.customer.csm_rep_id:
            owner_id = case.customer.csm_rep_id
            entity_name = case.customer.company.company_name if case.customer.company else "Unknown"
        event_key = f"support_{case.case_id}"
        email_alert_type = "High Priority Support Alert"
        
    elif payload.action_type == "New High-Value Lead" and payload.lead_id:
        lead = db.query(Lead).filter(Lead.lead_id == payload.lead_id).first()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        owner_id = lead.assigned_rep_id
        entity_name = lead.company.company_name if lead.company else "Unknown"
        event_key = f"lead_{lead.lead_id}_new"
        email_alert_type = "New High-Value Lead"
        
    else:
        raise HTTPException(status_code=400, detail="Invalid action or missing entity ID")

    # 2. Enforce RBAC
    if not owner_id:
        owner_id = current_user.rep_id
    
    if owner_id:
        if not verify_assignment(db, current_user, owner_id):
            raise HTTPException(status_code=403, detail="Not authorized to create task for this record owner")
            
    # 3. Create Activity
    now_str = datetime.now(timezone.utc).isoformat()
    due_date = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    
    desc = f"Generated via AI Action Recommendation.\nReason: {payload.reason}\n[Event: {event_key}]"
    
    existing_act = db.query(Activity).filter(Activity.description == desc).first()
    if existing_act:
        return {
            "status": "success",
            "message": "Duplicate/already-created",
            "data": {
                "activity_id": existing_act.activity_id,
                "subject": existing_act.subject,
                "owner_id": existing_act.sales_rep_id,
                "due_date": existing_act.due_date,
                "email_status": "Duplicate suppressed"
            }
        }
    
    act = Activity(
        activity_id=f"ACT-{uuid.uuid4().hex[:6].upper()}",
        activity_type="Task",
        subject=f"Follow up: {payload.reason} ({entity_name})",
        description=desc,
        activity_date=now_str,
        due_date=due_date,
        status="Planned",
        priority="High",
        customer_id=payload.customer_id,
        company_id=payload.company_id,
        opportunity_id=payload.opportunity_id,
        lead_id=payload.lead_id,
        sales_rep_id=owner_id,
        created_at=now_str,
        updated_at=now_str,
        created_by=current_user.user_id,
        updated_by=current_user.user_id
    )
    db.add(act)
    
    # 4. Optional Email Trigger (using event_key to avoid duplicates)
    email_status = "Skipped"
    if payload.trigger_email and owner_id and email_alert_type:
        existing = db.query(EmailHistory).filter(EmailHistory.id == event_key).first()
        if not existing:
            recipient = db.query(User).filter(User.rep_id == owner_id).first()
            if recipient and recipient.email and "@" in recipient.email:
                generator = AIEmailGenerator()
                context = {
                    "entity_name": entity_name,
                    "recommended_action": act.subject,
                    "reason": payload.reason
                }
                draft = generator.generate_email(
                    alert_type=email_alert_type,
                    context=context,
                    recipient_name=recipient.email.split("@")[0].capitalize()
                )
                
                email_service = EmailService()
                try:
                    email_service.send_raw_email(
                        to_email=recipient.email,
                        subject=draft["subject"],
                        body_text=draft["text_body"],
                        body_html=draft["html_body"]
                    )
                    new_draft = EmailHistory(
                        id=event_key,
                        recipient_email=recipient.email,
                        subject=draft["subject"],
                        email_type=email_alert_type,
                        status="Sent"
                    )
                    db.add(new_draft)
                    email_status = "Sent"
                except Exception as e:
                    new_draft = EmailHistory(
                        id=event_key,
                        recipient_email=recipient.email,
                        subject=draft["subject"],
                        email_type=email_alert_type,
                        status="Failed"
                    )
                    db.add(new_draft)
                    email_status = f"Failed: {str(e)}"
        else:
            email_status = "Duplicate suppressed"

    db.commit()
    db.refresh(act)
    
    return {
        "status": "success",
        "data": {
            "activity_id": act.activity_id,
            "subject": act.subject,
            "owner_id": owner_id,
            "due_date": act.due_date,
            "email_status": email_status
        }
    }

