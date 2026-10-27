from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from ..models import Customer, User, Activity
from .health_service import calculate_account_health
from .health_service_summary import apply_rbac_filter
from .health_service import get_date_range_from_period
from backend.intelligence_schemas import ActionItem, IntelligenceResponse

def get_retention_recommendations(db: Session, current_user: User, period: str = "this_year"):
    recommendations = []
    
    # 1. Get all RBAC accessible customers
    customers_query = db.query(Customer).filter(Customer.customer_status == "Active")
    customers_query = apply_rbac_filter(customers_query, Customer, current_user)
    customers = customers_query.all()
    
    today = datetime.utcnow()
    
    for customer in customers:
        # We need the full metrics from calculate_account_health
        health_data = calculate_account_health(db, customer.customer_id, period)
        
        signals = []
        metrics = health_data.metrics
        
        # 1. High Churn (>= 0.50)
        churn_prob = metrics.get("churn_probability")
        if churn_prob is not None and churn_prob >= 0.50:
            signals.append(f"Churn probability: {(churn_prob*100):.1f}%")
            
        # 2. Account Health Risk (< 60)
        score = health_data.score
        if score < 60:
            signals.append(f"Account Health: {health_data.status.value}")
            
        # 3. Upcoming Renewal (<= 90 days)
        if customer.renewal_date:
            try:
                # Format is likely YYYY-MM-DD
                renewal_date = datetime.strptime(customer.renewal_date, "%Y-%m-%d")
                days_to_renewal = (renewal_date - today).days
                if 0 <= days_to_renewal <= 90:
                    signals.append(f"Renewal: {days_to_renewal} days")
            except ValueError:
                pass
                
        # 4. Transaction Inactivity
        # The health calculation looks at transactions in the last 180 days by default (or specific period)
        # We can just check the transaction_volume metric
        txn_vol = metrics.get("transaction_volume")
        if txn_vol is not None and txn_vol == 0:
            signals.append("Recent transaction activity: No recent activity")
            
        # 5. Support Burden
        # elevated open/high-priority support cases
        # calculate_account_health drops score by 15 for each high priority open case.
        # We can check open_cases metric
        open_cases = metrics.get("open_cases", 0)
        if open_cases > 0:
            signals.append(f"Support burden: {open_cases} open cases")
            
        # Check if >= 2 signals
        if len(signals) >= 2:
            priority = "High" if len(signals) >= 3 or score < 40 else "Medium"
            
            recs = ActionItem(
                customer_id=customer.customer_id,
                entity_name=health_data.entity_name,
                action="Schedule retention review",
                priority=priority,
                reasons=signals,
                supporting_metrics={
                    "churn_probability": churn_prob,
                    "account_health": score,
                    "renewal_days": days_to_renewal if 'days_to_renewal' in locals() and customer.renewal_date else None,
                    "transaction_volume": txn_vol,
                    "open_cases": open_cases
                }
            )
            recommendations.append(recs)
            
    # Now check the period mode
    mode = "actions_taken" if period == "last_month" else "next_best_action"
    
    if mode == "next_best_action":
        def sort_key(r):
            priority_val = 0 if r.priority == "High" else 1 if r.priority == "Medium" else 2
            score = r.supporting_metrics.get("account_health", 100) if r.supporting_metrics else 100
            churn = r.supporting_metrics.get("churn_probability") or 0.0
            return (priority_val, score, -churn)
            
        recommendations.sort(key=sort_key)
        return IntelligenceResponse(mode=mode, actions=recommendations)
        
    # actions_taken mode
    start_date, end_date = get_date_range_from_period(period)
    actions_taken = []
    
    # We only care about activities for the recommended customers
    target_customer_ids = [r.customer_id for r in recommendations]
    
    # Pre-fetch activities for these customers
    activities_query = db.query(Activity).filter(
        Activity.customer_id.in_(target_customer_ids),
        Activity.activity_date >= start_date,
        Activity.activity_date <= end_date
    ).order_by(Activity.activity_date.desc())
    
    activities = activities_query.all()
    
    # Group activities by customer_id
    from collections import defaultdict
    cust_activities = defaultdict(list)
    for act in activities:
        cust_activities[act.customer_id].append(act)
        
    for rec in recommendations:
        cust_id = rec.customer_id
        if cust_activities[cust_id]:
            # Use most recent activity
            act = cust_activities[cust_id][0]
            actions_taken.append(ActionItem(
                customer_id=cust_id,
                entity_name=rec.entity_name,
                activity_id=act.activity_id,
                activity_type=act.activity_type,
                activity_date=act.activity_date,
                subject=act.subject,
                description=act.description
            ))
        else:
            # Fallback when no activity
            actions_taken.append(ActionItem(
                customer_id=cust_id,
                entity_name=rec.entity_name,
                action="No recorded action in this period."
            ))
            
    return IntelligenceResponse(mode=mode, actions=actions_taken)
