import datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, text
from backend.models import SupportCase, Customer, Lead, Opportunity, User, EmailHistory, UserSettings
from backend.services.intelligence_service import get_retention_recommendations
from backend.services.ai_email_generator import AIEmailGenerator

def check_email_preference(db: Session, user_id: str) -> bool:
    settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
    if settings and settings.preferences:
        # Default to True if not explicitly set to false
        return settings.preferences.get("emailNotifications", True)
    return True

def get_automation_candidates(db: Session):
    candidates = []
    today = datetime.datetime.utcnow()
    today_str = today.strftime("%Y-%m-%d")
    next_7_days = (today + datetime.timedelta(days=7)).strftime("%Y-%m-%d")
    next_30_days = (today + datetime.timedelta(days=30)).strftime("%Y-%m-%d")

    # 1. High/Urgent Support Cases
    support_q = db.query(SupportCase, Customer).join(Customer).filter(
        SupportCase.deleted_at == None,
        SupportCase.status.in_(["Open", "In Progress"]),
        SupportCase.priority.in_(["High", "Urgent"])
    ).all()
    for case, customer in support_q:
        if customer.csm_rep_id:
            event_key = f"support_{case.case_id}"
            candidates.append({
                "type": "High Priority Support Alert",
                "recipient_id": customer.csm_rep_id,
                "event_key": event_key,
                "context": {
                    "case_id": case.case_id,
                    "case_type": case.case_type,
                    "priority": case.priority,
                    "status": case.status,
                    "customer_id": customer.customer_id
                }
            })

    # 2. Leads Needing Follow-up
    lead_q = db.query(Lead).filter(
        Lead.deleted_at == None,
        Lead.lead_status == "New"
    ).all()
    for l in lead_q:
        if l.assigned_rep_id:
            event_key = f"lead_{l.lead_id}_new"
            candidates.append({
                "type": "New High-Value Lead",
                "recipient_id": l.assigned_rep_id,
                "event_key": event_key,
                "context": {
                    "lead_id": l.lead_id,
                    "lead_source": l.lead_source.value if hasattr(l.lead_source, 'value') else str(l.lead_source),
                    "company_id": l.company_id
                }
            })

    # 3. Opportunities Closing Soon
    opp_q = db.query(Opportunity).filter(
        Opportunity.deleted_at == None,
        Opportunity.pipeline_stage.notin_(["Closed Won", "Closed Lost"]),
        Opportunity.expected_close_date >= today_str,
        Opportunity.expected_close_date <= next_7_days
    ).all()
    for o in opp_q:
        if o.owner_rep_id:
            event_key = f"opp_{o.opportunity_id}_closing_{o.expected_close_date}"
            candidates.append({
                "type": "Opportunity Closing Soon",
                "recipient_id": o.owner_rep_id,
                "event_key": event_key,
                "context": {
                    "opportunity_id": o.opportunity_id,
                    "opportunity_name": o.opportunity_name,
                    "expected_close_date": o.expected_close_date,
                    "pipeline_stage": o.pipeline_stage
                }
            })

    # 4. Customer Renewals
    cust_q = db.query(Customer).filter(
        Customer.deleted_at == None,
        Customer.customer_status == "Active",
        Customer.renewal_date >= today_str,
        Customer.renewal_date <= next_30_days
    ).all()
    for c in cust_q:
        if c.csm_rep_id:
            event_key = f"renewal_{c.customer_id}_{c.renewal_date}"
            candidates.append({
                "type": "Upcoming Customer Renewal",
                "recipient_id": c.csm_rep_id,
                "event_key": event_key,
                "context": {
                    "customer_id": c.customer_id,
                    "customer_status": c.customer_status,
                    "renewal_date": c.renewal_date
                }
            })

    # 5. High Churn Risk
    # We will get recommendations for an admin user to bypass RBAC and get all, or just use a dummy user with role Admin
    admin_user = db.query(User).filter(User.role == "Admin").first()
    if admin_user:
        try:
            intel_res = get_retention_recommendations(db, admin_user, "next_best_action")
            for rec in intel_res.actions:
                if rec.priority == "High":
                    c = db.query(Customer).filter(Customer.customer_id == rec.customer_id).first()
                    if c and c.csm_rep_id:
                        period = today.strftime("%Y-%m")
                        event_key = f"churn_{c.customer_id}_{period}"
                        candidates.append({
                            "type": "High Churn Risk Alert",
                            "recipient_id": c.csm_rep_id,
                            "event_key": event_key,
                            "context": {
                                "customer_id": rec.customer_id,
                                "entity_name": rec.entity_name,
                                "recommended_action": rec.action
                            }
                        })
        except Exception as e:
            print(f"Error fetching churn recommendations: {e}")

    return candidates

def run_automation(db: Session, mode: str = None):
    import os
    from backend.services.email_service import EmailService
    
    if mode is None:
        mode = os.getenv("AUTOMATION_EMAIL_MODE", "DRY_RUN")
        
    candidates = get_automation_candidates(db)[:5]
    results = {
        "detected": len(candidates),
        "skipped_duplicates": 0,
        "skipped_preferences": 0,
        "skipped_invalid_email": 0,
        "generated": 0,
        "sent": 0,
        "failed": 0,
        "drafts": []
    }
    
    generator = AIEmailGenerator()
    email_service = EmailService()

    for cand in candidates:
        try:
            event_key = cand["event_key"]
            recipient_id = cand["recipient_id"]
            
            # Deduplication check using EmailHistory.id = event_key
            existing = db.query(EmailHistory).filter(EmailHistory.id == event_key).first()
            if existing:
                results["skipped_duplicates"] += 1
                continue
                
            # recipient_id here is actually rep_id for all current candidates.
            recipient = db.query(User).filter(User.rep_id == recipient_id).first()
            if not recipient:
                results["failed"] += 1
                continue
                
            if not recipient.email or "@" not in recipient.email or "example" in recipient.email.lower() or "placeholder" in recipient.email.lower():
                results["skipped_invalid_email"] += 1
                continue
                
            # Preference check
            if not check_email_preference(db, recipient.user_id):
                results["skipped_preferences"] += 1
                continue
                
            # Generate Draft
            draft = generator.generate_email(
                alert_type=cand["type"],
                context=cand["context"],
                recipient_name=recipient.email.split("@")[0].capitalize()
            )
            results["generated"] += 1
            
            new_draft = EmailHistory(
                id=event_key,
                recipient_email=recipient.email,
                subject=draft["subject"],
                email_type=cand["type"],
                status="Draft"
            )
            db.add(new_draft)
            db.commit()
            
            if mode == "SEND":
                # Send real email
                try:
                    email_service.send_raw_email(
                        to_email=recipient.email,
                        subject=draft["subject"],
                        body_text=draft["text_body"],
                        body_html=draft["html_body"]
                    )
                    new_draft.status = "Sent"
                    db.commit()
                    results["sent"] += 1
                except Exception as e:
                    new_draft.status = "Failed"
                    new_draft.error_message = str(e)
                    db.commit()
                    results["failed"] += 1
                    
            results["drafts"].append({
                "event_key": event_key,
                "trigger_type": cand["type"],
                "recipient_email": recipient.email,
                "subject": draft["subject"],
                "status": new_draft.status
            })
            
        except Exception as e:
            print(f"Error processing candidate {cand.get('event_key')}: {e}")
            db.rollback()
            results["failed"] += 1
            continue
            
    return results
