from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, text
import datetime

from .. import models
from ..database import get_db
from ..deps import get_current_active_user
from ..services.intelligence_service import get_retention_recommendations
from ..rbac import apply_rbac_filter

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

@router.get("")
def get_notifications(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    notifications = []
    today = datetime.datetime.utcnow()
    today_str = today.strftime("%Y-%m-%d")
    next_7_days = (today + datetime.timedelta(days=7)).strftime("%Y-%m-%d")
    next_30_days = (today + datetime.timedelta(days=30)).strftime("%Y-%m-%d")

    # 1. High/Urgent Support Cases
    support_q = db.query(models.SupportCase).filter(
        models.SupportCase.deleted_at == None,
        models.SupportCase.status.in_(["Open", "In Progress"]),
        models.SupportCase.priority.in_(["High", "Urgent"])
    )
    support_q = support_q.join(models.Customer)
    support_q = apply_rbac_filter(db, support_q, current_user, models.Customer, "csm_rep_id")
    urgent_cases = support_q.limit(10).all()
    for c in urgent_cases:
        notifications.append({
            "id": f"support_{c.case_id}",
            "type": "support",
            "title": f"{c.priority} Priority Case",
            "message": c.case_type or f"Case #{c.case_id}",
            "link": "/support",
            "timestamp": c.opened_at,
            "priority": 3 if c.priority == "Urgent" else 2
        })

    # 2. Leads Needing Follow-up (New status)
    lead_q = db.query(models.Lead).filter(
        models.Lead.deleted_at == None,
        models.Lead.lead_status == "New"
    )
    lead_q = apply_rbac_filter(db, lead_q, current_user, models.Lead, "assigned_rep_id")
    leads = lead_q.limit(10).all()
    for l in leads:
        notifications.append({
            "id": f"lead_{l.lead_id}",
            "type": "lead",
            "title": "New Lead Follow-up",
            "message": "Lead needs initial contact",
            "link": "/leads",
            "timestamp": l.created_at,
            "priority": 2
        })

    # 3. Opportunities Closing Soon
    opp_q = db.query(models.Opportunity).filter(
        models.Opportunity.deleted_at == None,
        models.Opportunity.pipeline_stage.notin_(["Closed Won", "Closed Lost"]),
        models.Opportunity.expected_close_date >= today_str,
        models.Opportunity.expected_close_date <= next_7_days
    )
    opp_q = apply_rbac_filter(db, opp_q, current_user, models.Opportunity, "owner_rep_id")
    opps = opp_q.limit(10).all()
    for o in opps:
        notifications.append({
            "id": f"opp_{o.opportunity_id}",
            "type": "opportunity",
            "title": "Closing Soon",
            "message": f"{o.opportunity_name} expected to close on {o.expected_close_date}",
            "link": f"/opportunities/{o.opportunity_id}",
            "timestamp": today_str,
            "priority": 2
        })

    # 4. Customer Renewals
    cust_q = db.query(models.Customer).filter(
        models.Customer.deleted_at == None,
        models.Customer.customer_status == "Active",
        models.Customer.renewal_date >= today_str,
        models.Customer.renewal_date <= next_30_days
    )
    cust_q = apply_rbac_filter(db, cust_q, current_user, models.Customer, "csm_rep_id")
    renewals = cust_q.limit(10).all()
    for c in renewals:
        company_name = c.company.company_name if c.company else "Customer"
        notifications.append({
            "id": f"renewal_{c.customer_id}",
            "type": "renewal",
            "title": "Upcoming Renewal",
            "message": f"{company_name} renews on {c.renewal_date}",
            "link": f"/customers/{c.customer_id}",
            "timestamp": today_str,
            "priority": 1
        })

    # 5. High Churn Risk (AI Recommendations)
    # get_retention_recommendations already applies RBAC
    try:
        intel_res = get_retention_recommendations(db, current_user, "next_best_action")
        for rec in intel_res.actions:
            if rec.priority == "High":
                notifications.append({
                    "id": f"churn_{rec.customer_id}",
                    "type": "churn",
                    "title": "High Churn Risk",
                    "message": f"{rec.entity_name} needs attention",
                    "link": f"/customers/{rec.customer_id}",
                    "timestamp": today_str,
                    "priority": 3
                })
    except Exception as e:
        # If churn prediction fails, just skip it gracefully
        print(f"Error fetching churn recommendations for notifications: {e}")

    # Sort primarily by priority (descending), then by timestamp (descending)
    # Using timestamp string directly works since YYYY-MM-DD formats sort lexicographically
    notifications.sort(key=lambda x: (x.get("priority", 0), x.get("timestamp", "")), reverse=True)
    
    return {"notifications": notifications[:10]}
