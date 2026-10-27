from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..models import Customer, Company, Product, User
from .health_service import calculate_account_health, calculate_company_health, calculate_product_health
from ..schemas import HealthStatus, RiskEntity

def apply_rbac_filter(query, model, current_user: User):
    if current_user.role in ["Admin", "System Admin", "Manager", "Sales Manager"]:
        return query
    if model == Customer:
        return query.filter(Customer.csm_rep_id == current_user.user_id)
    if model == Company:
        return query.filter(Company.account_owner_rep_id == current_user.user_id)
    return query

def _aggregate_health(db: Session, items: List[Any], calc_func, id_attr: str, period: str = "all_time") -> Dict[str, Any]:
    total_evaluated = len(items)
    if total_evaluated == 0:
        return {
            "average_score": None,
            "status": HealthStatus.UNKNOWN,
            "total_evaluated": 0,
            "healthy_count": 0,
            "at_risk_count": 0,
            "critical_count": 0,
            "unknown_count": 0,
            "health_distribution": {"HEALTHY": 0, "AT_RISK": 0, "CRITICAL": 0, "UNKNOWN": 0},
            "insights": [{"insight": "No accessible records found.", "type": "neutral"}],
            "risk_entities": [],
            "insufficient_data": True
        }

    valid_scores = []
    distribution = {"HEALTHY": 0, "AT_RISK": 0, "CRITICAL": 0, "UNKNOWN": 0}
    
    risk_entities_pool = []
    
    for item in items:
        item_id = getattr(item, id_attr)
        res = calc_func(db, item_id, period=period)
        
        dist_key = res.status.name
        if dist_key not in distribution:
            distribution[dist_key] = 0
        distribution[dist_key] += 1
        
        if res.status != HealthStatus.UNKNOWN and not res.insufficient_data:
            valid_scores.append(res.score)
            
            if res.status in (HealthStatus.AT_RISK, HealthStatus.CRITICAL):
                key_signal = "Low engagement" # default
                if res.insights:
                    # Pick the most negative insight
                    negatives = [i for i in res.insights if i.type == "negative"]
                    if negatives:
                        key_signal = negatives[0].insight
                
                risk_entities_pool.append(RiskEntity(
                    id=item_id,
                    name=res.entity_name or item_id,
                    score=res.score,
                    status=res.status,
                    key_signal=key_signal
                ))
    
    # Sort risk entities by score ascending (lowest health first) and take top 5
    risk_entities_pool.sort(key=lambda r: r.score)
    risk_entities_list = risk_entities_pool[:5]
    
    if not valid_scores:
        return {
            "average_score": None,
            "status": HealthStatus.UNKNOWN,
            "total_evaluated": total_evaluated,
            "healthy_count": distribution.get("HEALTHY", 0),
            "at_risk_count": distribution.get("AT_RISK", 0),
            "critical_count": distribution.get("CRITICAL", 0),
            "unknown_count": distribution.get("UNKNOWN", 0),
            "health_distribution": distribution,
            "insights": [{"insight": "All evaluated records had insufficient data.", "type": "neutral"}],
            "risk_entities": [],
            "insufficient_data": True
        }
        
    avg_score = round(sum(valid_scores) / len(valid_scores), 1)
    
    if avg_score >= 70:
        overall_status = HealthStatus.HEALTHY
        msg = f"Overall health is strong. {distribution.get('HEALTHY', 0)} out of {total_evaluated} records are healthy."
    elif avg_score >= 40:
        overall_status = HealthStatus.AT_RISK
        msg = f"Overall health is at risk. Attention needed for {distribution.get('AT_RISK', 0)} records."
    else:
        overall_status = HealthStatus.CRITICAL
        msg = f"Overall health is critical. {distribution.get('CRITICAL', 0)} records require immediate intervention."
        
    return {
        "average_score": avg_score,
        "status": overall_status,
        "total_evaluated": total_evaluated,
        "healthy_count": distribution.get("HEALTHY", 0),
        "at_risk_count": distribution.get("AT_RISK", 0),
        "critical_count": distribution.get("CRITICAL", 0),
        "unknown_count": distribution.get("UNKNOWN", 0),
        "health_distribution": distribution,
        "insights": [{"insight": msg, "type": "neutral"}],
        "risk_entities": risk_entities_list,
        "insufficient_data": False
    }

def calculate_account_health_summary(db: Session, current_user: User, period: str = "all_time") -> Dict[str, Any]:
    query = db.query(Customer).filter(Customer.deleted_at == None)
    query = apply_rbac_filter(query, Customer, current_user)
    items = query.all()
    return _aggregate_health(db, items, calculate_account_health, "customer_id", period=period)

def calculate_company_health_summary(db: Session, current_user: User, period: str = "all_time") -> Dict[str, Any]:
    query = db.query(Company).filter(Company.deleted_at == None)
    query = apply_rbac_filter(query, Company, current_user)
    items = query.all()
    return _aggregate_health(db, items, calculate_company_health, "company_id", period=period)

def calculate_product_health_summary(db: Session, current_user: User, period: str = "all_time") -> Dict[str, Any]:
    # Products typically don't have row-level owner in this schema, so we evaluate all non-deleted
    items = db.query(Product).filter(Product.deleted_at == None).all()
    return _aggregate_health(db, items, calculate_product_health, "product_id", period=period)
