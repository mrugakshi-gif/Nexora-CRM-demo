import logging
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
import calendar
from typing import Dict, Any, List, Optional

from ..models import (
    Customer, Company, Product, CustomerTransaction, SupportCase, 
    Opportunity, OpportunityProduct, Lead, Activity, OpportunityStageHistory
)
from ..schemas import (
    HealthStatus, InsightInput, AccountHealthResponse, CompanyHealthResponse, 
    ProductHealthResponse, DealHealthFactor, DealHealthResponse
)
from ..ml.prediction import PredictionService

logger = logging.getLogger(__name__)

prediction_service = PredictionService()

def determine_status(score: float) -> HealthStatus:
    if score >= 80:
        return HealthStatus.EXCELLENT
    if score >= 60:
        return HealthStatus.HEALTHY
    if score >= 40:
        return HealthStatus.AT_RISK
    return HealthStatus.CRITICAL

def get_date_range_from_period(period: str):
    now = datetime.utcnow()
    
    if period == "this_month":
        start_date = datetime(now.year, now.month, 1).strftime("%Y-%m-%d")
        _, last_day = calendar.monthrange(now.year, now.month)
        end_date = datetime(now.year, now.month, last_day, 23, 59, 59).strftime("%Y-%m-%d")
    elif period == "last_month":
        first_day = (now.replace(day=1) - timedelta(days=1)).replace(day=1)
        _, last_day = calendar.monthrange(first_day.year, first_day.month)
        start_date = first_day.strftime("%Y-%m-%d")
        end_date = datetime(first_day.year, first_day.month, last_day, 23, 59, 59).strftime("%Y-%m-%d")
    elif period == "this_quarter":
        quarter = (now.month - 1) // 3 + 1
        first_month = 3 * quarter - 2
        start_date = datetime(now.year, first_month, 1).strftime("%Y-%m-%d")
        last_month = 3 * quarter
        _, last_day = calendar.monthrange(now.year, last_month)
        end_date = datetime(now.year, last_month, last_day, 23, 59, 59).strftime("%Y-%m-%d")
    elif period == "this_year":
        start_date = datetime(now.year, 1, 1).strftime("%Y-%m-%d")
        end_date = datetime(now.year, 12, 31, 23, 59, 59).strftime("%Y-%m-%d")
    else: # all_time
        start_date = "0000-00-00"
        end_date = "9999-12-31"
        
    return start_date, end_date

def calculate_account_health(db: Session, customer_id: str, period: str = "all_time") -> AccountHealthResponse:
    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    if not customer:
        raise ValueError("Customer not found")

    insights = []
    start_date, end_date = get_date_range_from_period(period)
    
    # Transactions (Payment Status & Frequency)
    transactions = db.query(CustomerTransaction).filter(
        CustomerTransaction.customer_id == customer_id,
        CustomerTransaction.transaction_date >= start_date,
        CustomerTransaction.transaction_date <= end_date
    ).all()
    
    thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
    recent_transactions = [t for t in transactions if t.transaction_date >= thirty_days_ago]
    late_payments = len([t for t in transactions if t.payment_status == 'Late'])
    
    # Support
    support_cases = db.query(SupportCase).filter(
        SupportCase.customer_id == customer_id,
        SupportCase.opened_at >= start_date,
        SupportCase.opened_at <= end_date
    ).all()
    open_cases = [c for c in support_cases if c.status not in ('Closed', 'Resolved')]
    high_priority_open = len([c for c in open_cases if c.priority == 'High'])
    avg_sat_score = sum(c.satisfaction_score for c in support_cases if c.satisfaction_score) / len([c for c in support_cases if c.satisfaction_score]) if [c for c in support_cases if c.satisfaction_score] else None

    # Activities
    activities = db.query(Activity).filter(
        Activity.customer_id == customer_id,
        Activity.activity_date >= start_date,
        Activity.activity_date <= end_date
    ).all()
    recent_activities = len([a for a in activities if a.activity_date >= thirty_days_ago])

    # ML Churn (Period Independent)
    churn_prob = None
    try:
        churn_res = prediction_service.predict_customer_churn(db, customer_id)
        churn_prob = churn_res.churn_probability
    except Exception:
        pass

    if len(transactions) == 0 and len(activities) == 0 and len(support_cases) == 0:
        return AccountHealthResponse(
            customer_id=customer_id,
            entity_name=customer.company.company_name if customer.company else customer.customer_id,
            score=0.0,
            status=HealthStatus.UNKNOWN,
            metrics={},
            insights=[InsightInput(insight="No interaction history available in this period.", type="negative")],
            insufficient_data=True
        )

    # Score calculation (0-100)
    score = 70.0  # Base
    
    if len(recent_transactions) > 0:
        score += 10
        insights.append(InsightInput(insight=f"{len(recent_transactions)} transactions in last 30 days.", type="positive"))
        
    if late_payments > 0:
        score -= min(late_payments * 5, 20)
        insights.append(InsightInput(insight=f"{late_payments} late payments recorded.", type="negative"))
        
    if high_priority_open > 0:
        score -= min(high_priority_open * 10, 30)
        insights.append(InsightInput(insight=f"{high_priority_open} high priority support cases currently open.", type="negative"))
        
    if avg_sat_score is not None:
        if avg_sat_score >= 4.0:
            score += 10
            insights.append(InsightInput(insight=f"High average satisfaction score ({avg_sat_score:.1f}/5).", type="positive"))
        elif avg_sat_score < 3.0:
            score -= 15
            insights.append(InsightInput(insight=f"Low average satisfaction score ({avg_sat_score:.1f}/5).", type="negative"))

    if recent_activities > 5:
        score += 10
        insights.append(InsightInput(insight=f"Strong recent engagement ({recent_activities} activities).", type="positive"))
    elif recent_activities == 0:
        score -= 10
        insights.append(InsightInput(insight="No recent activity logged in the last 30 days.", type="negative"))

    if churn_prob is not None:
        if churn_prob > 0.5:
            score -= (churn_prob * 30)
            insights.append(InsightInput(insight=f"ML Churn model indicates {(churn_prob*100):.1f}% risk.", type="negative"))
        else:
            score += 10
            insights.append(InsightInput(insight="Low predicted churn risk.", type="positive"))

    score = max(0.0, min(100.0, score))

    metrics = {
        "recent_transactions": len(recent_transactions),
        "late_payments": late_payments,
        "high_priority_open_cases": high_priority_open,
        "avg_satisfaction": round(avg_sat_score, 1) if avg_sat_score else None,
        "recent_activities": recent_activities,
        "churn_probability": churn_prob
    }

    if not insights:
        insights.append(InsightInput(insight="Account is stable but lacks strong recent engagement signals.", type="neutral"))

    return AccountHealthResponse(
        customer_id=customer_id,
        entity_name=customer.company.company_name if customer.company else customer.customer_id,
        score=score,
        status=determine_status(score),
        metrics=metrics,
        insights=insights
    )


def calculate_company_health(db: Session, company_id: str, period: str = "all_time") -> CompanyHealthResponse:
    company = db.query(Company).filter(Company.company_id == company_id).first()
    if not company:
        raise ValueError("Company not found")

    insights = []
    start_date, end_date = get_date_range_from_period(period)
    
    # We use created_at for opportunities to align with pipeline creation within the period
    # OR we use expected_close_date for active opps.
    # The prompt explicitly said: "Use: Opportunity created/stage/closure information according to what the existing schema actually supports"
    # To include all opps relevant to the period, we can check if they were created in the period OR closed in the period
    opportunities = db.query(Opportunity).filter(
        Opportunity.company_id == company_id,
        (Opportunity.created_at >= start_date) | 
        (Opportunity.actual_close_date >= start_date) |
        (Opportunity.expected_close_date >= start_date)
    ).filter(
        (Opportunity.created_at <= end_date) | 
        (Opportunity.actual_close_date <= end_date) |
        (Opportunity.expected_close_date <= end_date)
    ).all()
    
    leads = db.query(Lead).filter(
        Lead.company_id == company_id,
        Lead.created_at >= start_date,
        Lead.created_at <= end_date
    ).all()
    
    activities = db.query(Activity).filter(
        Activity.company_id == company_id,
        Activity.activity_date >= start_date,
        Activity.activity_date <= end_date
    ).all()
    
    if not opportunities and not leads and not activities:
        return CompanyHealthResponse(
            company_id=company_id,
            entity_name=company.company_name,
            score=0,
            status=HealthStatus.UNKNOWN,
            metrics={},
            insights=[InsightInput(insight="No pipeline, leads, or activities found in this period.", type="negative")],
            insufficient_data=True
        )

    # Opportunity metrics
    active_opps = [o for o in opportunities if o.pipeline_stage not in ('Closed Won', 'Closed Lost')]
    won_opps = [o for o in opportunities if o.pipeline_stage == 'Closed Won']
    lost_opps = [o for o in opportunities if o.pipeline_stage == 'Closed Lost']
    
    total_closed = len(won_opps) + len(lost_opps)
    win_rate = (len(won_opps) / total_closed) if total_closed > 0 else None
    
    total_pipeline_value = sum(o.deal_value_inr for o in active_opps)
    avg_probability = sum(o.probability_pct for o in active_opps) / len(active_opps) if active_opps else 0
    
    # Lead metrics
    converted_leads = [l for l in leads if l.lead_status == 'Converted']
    disqualified_leads = [l for l in leads if l.lead_status == 'Disqualified']
    
    score = 50.0  # Base
    
    if win_rate is not None:
        if win_rate > 0.5:
            score += 20
            insights.append(InsightInput(insight=f"High historical win rate ({(win_rate*100):.0f}%).", type="positive"))
        elif win_rate < 0.2:
            score -= 15
            insights.append(InsightInput(insight=f"Low historical win rate ({(win_rate*100):.0f}%).", type="negative"))
            
    if len(active_opps) > 0:
        score += min(len(active_opps) * 5, 15)
        insights.append(InsightInput(insight=f"{len(active_opps)} active opportunities in pipeline.", type="positive"))
        if avg_probability > 0.6:
            score += 10
            insights.append(InsightInput(insight="High average probability to close on active pipeline.", type="positive"))

    if len(converted_leads) > 0:
        score += 10
        insights.append(InsightInput(insight=f"History of successful lead conversions ({len(converted_leads)}).", type="positive"))
        
    if len(disqualified_leads) > (len(converted_leads) * 2) and len(disqualified_leads) > 0:
        score -= 10
        insights.append(InsightInput(insight="High ratio of disqualified leads.", type="negative"))
        
    thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
    recent_activities = len([a for a in activities if a.activity_date >= thirty_days_ago])
    
    if recent_activities > 10:
        score += 15
        insights.append(InsightInput(insight="Strong recent engagement activity.", type="positive"))
    elif recent_activities == 0 and len(active_opps) > 0:
        score -= 15
        insights.append(InsightInput(insight="No recent activity despite having active opportunities.", type="negative"))

    score = max(0.0, min(100.0, score))
    
    metrics = {
        "active_opportunities": len(active_opps),
        "pipeline_value_inr": total_pipeline_value,
        "historical_win_rate": round(win_rate, 2) if win_rate is not None else None,
        "lead_conversions": len(converted_leads),
        "recent_activities": recent_activities
    }
    
    if not insights:
        insights.append(InsightInput(insight="Standard pipeline health with no significant anomalies.", type="neutral"))

    return CompanyHealthResponse(
        company_id=company_id,
        entity_name=company.company_name,
        score=score,
        status=determine_status(score),
        metrics=metrics,
        insights=insights
    )


def calculate_product_health(db: Session, product_id: str, period: str = "all_time") -> ProductHealthResponse:
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        raise ValueError("Product not found")

    insights = []
    start_date, end_date = get_date_range_from_period(period)
    
    # We filter opp products by joining on Opportunity dates
    opp_products_raw = db.query(OpportunityProduct, Opportunity).join(
        Opportunity, OpportunityProduct.opportunity_id == Opportunity.opportunity_id
    ).filter(
        OpportunityProduct.product_id == product_id,
        (Opportunity.created_at >= start_date) | 
        (Opportunity.actual_close_date >= start_date) |
        (Opportunity.expected_close_date >= start_date)
    ).filter(
        (Opportunity.created_at <= end_date) | 
        (Opportunity.actual_close_date <= end_date) |
        (Opportunity.expected_close_date <= end_date)
    ).all()
    
    opp_products = [op for op, opp in opp_products_raw]
    opps = list(set([opp for op, opp in opp_products_raw]))
    
    if not opp_products:
        return ProductHealthResponse(
            product_id=product_id,
            entity_name=product.product_name,
            score=0,
            status=HealthStatus.UNKNOWN,
            metrics={},
            insights=[InsightInput(insight="Product has no opportunity data in this period.", type="negative")],
            insufficient_data=True
        )

    # Opportunity Attach Rate & Discounts
    total_quantity = sum(op.quantity for op in opp_products)
    total_revenue = sum(op.line_total_inr for op in opp_products)
    avg_discount = sum(op.discount_pct for op in opp_products) / len(opp_products)
    
    won_opps = [o for o in opps if o.pipeline_stage == 'Closed Won']
    lost_opps = [o for o in opps if o.pipeline_stage == 'Closed Lost']
    total_closed = len(won_opps) + len(lost_opps)
    win_rate = (len(won_opps) / total_closed) if total_closed > 0 else None
    
    score = 60.0 # Base
    
    if total_revenue > 1000000:
        score += 15
        insights.append(InsightInput(insight="High historical revenue generator.", type="positive"))
    elif total_revenue > 0:
        score += 5
        
    if avg_discount > 15.0:
        score -= 20
        insights.append(InsightInput(insight=f"Requires high average discount ({avg_discount:.1f}%) to sell.", type="negative"))
    elif avg_discount == 0.0:
        score += 15
        insights.append(InsightInput(insight="Frequently sells at full list price.", type="positive"))
        
    if win_rate is not None:
        if win_rate > 0.6:
            score += 20
            insights.append(InsightInput(insight=f"High win rate ({(win_rate*100):.0f}%) when attached to deals.", type="positive"))
        elif win_rate < 0.2:
            score -= 20
            insights.append(InsightInput(insight=f"Low win rate ({(win_rate*100):.0f}%) when attached to deals.", type="negative"))

    score = max(0.0, min(100.0, score))
    
    metrics = {
        "total_revenue_inr": total_revenue,
        "quantity_sold": total_quantity,
        "average_discount_pct": round(avg_discount, 3),
        "attach_win_rate": round(win_rate, 2) if win_rate is not None else None,
        "times_attached": len(opp_products)
    }
    
    if not insights:
        insights.append(InsightInput(insight="Product performance is average.", type="neutral"))

    return ProductHealthResponse(
        product_id=product_id,
        entity_name=product.product_name,
        score=score,
        status=determine_status(score),
        metrics=metrics,
        insights=insights
    )


def _parse_crm_dt(dt_str: Optional[str]) -> Optional[datetime]:
    if not dt_str:
        return None
    try:
        cleaned = dt_str.replace("Z", "+00:00").strip()
        if " " in cleaned and "T" not in cleaned:
            cleaned = cleaned.replace(" ", "T")
        parsed = datetime.fromisoformat(cleaned)
        if parsed.tzinfo is not None:
            parsed = parsed.replace(tzinfo=None)
        return parsed
    except Exception as e:
        logger.debug("Failed to parse datetime '%s': %s", dt_str, e)
        return None


def calculate_deal_health(db: Session, opportunity_id: str) -> DealHealthResponse:
    """
    Dedicated opportunity-level risk and health assessment.
    Uses observable, defensible CRM indicators:
      1. Terminal status (Won -> 100 health, Lost -> 0 health)
      2. Close date adherence & overdue duration
      3. Stage stagnation & velocity (days in current pipeline stage)
      4. Margin & commercial discounting (line-item discount levels)
      5. Engagement & touchpoints (activity recency and volume)
      6. Record completeness (primary contact champion, source lead, line items)
    
    This implementation is explicitly rule-based heuristic intelligence (not trained ML).
    It operates in read-only mode and NEVER modifies any CRM records.
    """
    opp = db.query(Opportunity).filter(Opportunity.opportunity_id == opportunity_id).first()
    if not opp:
        raise ValueError(f"Opportunity {opportunity_id} not found")

    factors: List[DealHealthFactor] = []
    recs: List[str] = []
    score = 70.0  # Neutral baseline
    now = datetime.utcnow()
    
    # 1. Terminal Stage Handling
    if opp.close_outcome == "Won" or opp.pipeline_stage in ["Closed Won", "Won"]:
        return DealHealthResponse(
            opportunity_id=opp.opportunity_id,
            opportunity_name=opp.opportunity_name or opp.opportunity_id,
            pipeline_stage=opp.pipeline_stage,
            is_closed=True,
            close_outcome=opp.close_outcome or "Won",
            health_score=100.0,
            risk_score=0.0,
            risk_level="Low",
            status=HealthStatus.EXCELLENT,
            scoring_method="rule_based_heuristic",
            is_ml_model=False,
            contributing_factors=[
                DealHealthFactor(
                    category="Timeline",
                    name="Closed Won",
                    impact="positive",
                    weight_score_impact=30.0,
                    detail="Deal successfully won and closed."
                )
            ],
            mitigation_recommendations=["Initiate post-sale customer onboarding and handoff to CSM."],
            supporting_metrics={
                "is_closed": True,
                "close_outcome": "Won",
                "deal_value_inr": opp.deal_value_inr,
                "products_count": len(opp.products),
                "activities_count": len(opp.activities)
            },
            insufficient_data=False
        )
    elif opp.close_outcome == "Lost" or opp.pipeline_stage in ["Closed Lost", "Lost"]:
        loss_reason = opp.loss_reason or "Reason not specified"
        competitor = f" (Lost to: {opp.competitor_name})" if opp.competitor_name else ""
        return DealHealthResponse(
            opportunity_id=opp.opportunity_id,
            opportunity_name=opp.opportunity_name or opp.opportunity_id,
            pipeline_stage=opp.pipeline_stage,
            is_closed=True,
            close_outcome=opp.close_outcome or "Lost",
            health_score=0.0,
            risk_score=100.0,
            risk_level="Critical",
            status=HealthStatus.CRITICAL,
            scoring_method="rule_based_heuristic",
            is_ml_model=False,
            contributing_factors=[
                DealHealthFactor(
                    category="Timeline",
                    name="Closed Lost",
                    impact="negative",
                    weight_score_impact=-70.0,
                    detail=f"Deal closed lost. Loss reason: {loss_reason}{competitor}."
                )
            ],
            mitigation_recommendations=[
                "Conduct a win/loss review to document competitive gaps.",
                "Set a scheduled re-engagement reminder for 6 months out."
            ],
            supporting_metrics={
                "is_closed": True,
                "close_outcome": "Lost",
                "loss_reason": opp.loss_reason,
                "competitor_name": opp.competitor_name,
                "deal_value_inr": opp.deal_value_inr
            },
            insufficient_data=False
        )

    # 2. Target Close Date Adherence
    days_overdue = 0
    if not opp.expected_close_date:
        score -= 15.0
        factors.append(DealHealthFactor(
            category="Timeline",
            name="Missing Expected Close Date",
            impact="negative",
            weight_score_impact=-15.0,
            detail="Deal has no target close date, indicating lack of pipeline schedule commitment."
        ))
        recs.append("Establish and enter a verified target close date with the prospect.")
    else:
        close_dt = _parse_crm_dt(opp.expected_close_date)
        if close_dt:
            diff_days = (now - close_dt).days
            if diff_days > 60:
                score -= 25.0
                days_overdue = diff_days
                factors.append(DealHealthFactor(
                    category="Timeline",
                    name="Severely Overdue Target Close Date",
                    impact="negative",
                    weight_score_impact=-25.0,
                    detail=f"Expected close date lapsed {diff_days} days ago without closure."
                ))
                recs.append("Re-qualify timeline urgency with client executive sponsors immediately.")
            elif diff_days > 14:
                score -= 15.0
                days_overdue = diff_days
                factors.append(DealHealthFactor(
                    category="Timeline",
                    name="Overdue Target Close Date",
                    impact="negative",
                    weight_score_impact=-15.0,
                    detail=f"Expected close date passed {diff_days} days ago."
                ))
                recs.append("Update close date based on latest commercial review.")
            elif diff_days > 0:
                score -= 10.0
                days_overdue = diff_days
                factors.append(DealHealthFactor(
                    category="Timeline",
                    name="Past Expected Close Date",
                    impact="negative",
                    weight_score_impact=-10.0,
                    detail=f"Expected close date lapsed {diff_days} days ago."
                ))
                recs.append("Confirm next procurement step to bring deal to close.")
            elif diff_days >= -30 and opp.pipeline_stage in ["Negotiation", "Proposal", "Proposal/Price Quote"]:
                score += 10.0
                factors.append(DealHealthFactor(
                    category="Timeline",
                    name="Closing Soon in Advanced Stage",
                    impact="positive",
                    weight_score_impact=10.0,
                    detail=f"Target close date is in {abs(diff_days)} days with advanced stage alignment."
                ))

    # 3. Pipeline Velocity & Stage Stagnation
    latest_stage_hist = (
        db.query(OpportunityStageHistory)
        .filter(OpportunityStageHistory.opportunity_id == opportunity_id)
        .order_by(OpportunityStageHistory.changed_at.desc())
        .first()
    )
    last_stage_date_str = latest_stage_hist.changed_at if latest_stage_hist else opp.created_at
    last_stage_dt = _parse_crm_dt(last_stage_date_str)
    days_in_stage = (now - last_stage_dt).days if last_stage_dt else 0

    if days_in_stage > 90:
        score -= 25.0
        factors.append(DealHealthFactor(
            category="Velocity",
            name="Severe Stage Stagnation",
            impact="negative",
            weight_score_impact=-25.0,
            detail=f"Deal has been stalled in '{opp.pipeline_stage}' for {days_in_stage} days."
        ))
        recs.append("Executive escalation required: conduct a joint account review to unblock stalled evaluation.")
    elif days_in_stage > 45:
        score -= 15.0
        factors.append(DealHealthFactor(
            category="Velocity",
            name="Stage Stagnation",
            impact="negative",
            weight_score_impact=-15.0,
            detail=f"Deal has remained in '{opp.pipeline_stage}' for {days_in_stage} days without transition."
        ))
        recs.append("Follow up on pending buyer review milestones to advance stage.")
    elif days_in_stage < 15:
        score += 10.0
        factors.append(DealHealthFactor(
            category="Velocity",
            name="Recent Stage Progression",
            impact="positive",
            weight_score_impact=10.0,
            detail=f"Deal advanced to '{opp.pipeline_stage}' {days_in_stage} days ago."
        ))

    # 4. Commercial Discounting & Margin
    products = opp.products or []
    max_discount = 0.0
    if products:
        max_discount = max((p.discount_pct or 0.0) for p in products)
        if max_discount >= 15.0:
            score -= 15.0
            factors.append(DealHealthFactor(
                category="Margin",
                name="High Commercial Discounting",
                impact="negative",
                weight_score_impact=-15.0,
                detail=f"Heavy discount of {max_discount:.1f}% applied, creating margin compression."
            ))
            recs.append("Tie high product discounts to upfront payment or multi-year terms.")
        elif max_discount == 0.0:
            score += 5.0
            factors.append(DealHealthFactor(
                category="Margin",
                name="Full List Price Maintained",
                impact="positive",
                weight_score_impact=5.0,
                detail="Products are priced at full value with 0% discounting."
            ))
    else:
        score -= 10.0
        factors.append(DealHealthFactor(
            category="Completeness",
            name="No Products Attached",
            impact="negative",
            weight_score_impact=-10.0,
            detail="Deal has no line-item products attached to substantiate pricing."
        ))
        recs.append("Attach opportunity line-item products to validate deal size.")

    # 5. Relationship & Champion Completeness
    if not opp.primary_contact_id:
        score -= 15.0
        factors.append(DealHealthFactor(
            category="Completeness",
            name="Missing Primary Contact",
            impact="negative",
            weight_score_impact=-15.0,
            detail="Deal lacks a designated primary contact / champion."
        ))
        recs.append("Identify and link the primary decision-maker contact to the deal.")
    else:
        score += 5.0
        factors.append(DealHealthFactor(
            category="Completeness",
            name="Designated Primary Contact",
            impact="positive",
            weight_score_impact=5.0,
            detail="Primary contact champion is linked to opportunity."
        ))

    # 6. Engagement & Touchpoint Cadence
    activities = opp.activities or []
    days_since_act = None
    if not activities:
        score -= 15.0
        factors.append(DealHealthFactor(
            category="Engagement",
            name="Zero Touchpoints Recorded",
            impact="negative",
            weight_score_impact=-15.0,
            detail="No calls, meetings, or emails have been logged for this opportunity."
        ))
        recs.append("Log immediate outreach touchpoint (call or meeting) with key stakeholder.")
    else:
        valid_acts = [a for a in activities if a.activity_date]
        if valid_acts:
            latest_act = max(valid_acts, key=lambda a: a.activity_date)
            act_dt = _parse_crm_dt(latest_act.activity_date)
            if act_dt:
                days_since_act = (now - act_dt).days
                if days_since_act > 30:
                    score -= 15.0
                    factors.append(DealHealthFactor(
                        category="Engagement",
                        name="Stale Customer Engagement",
                        impact="negative",
                        weight_score_impact=-15.0,
                        detail=f"Last logged touchpoint was {days_since_act} days ago."
                    ))
                    recs.append("Re-engage prospect with tailored demo or updated pricing proposal.")
                elif days_since_act <= 7:
                    score += 10.0
                    factors.append(DealHealthFactor(
                        category="Engagement",
                        name="Active Touchpoint Cadence",
                        impact="positive",
                        weight_score_impact=10.0,
                        detail=f"Recent customer activity logged within the last {days_since_act} days."
                    ))

    # Clamp health score to [0, 100]
    health_score = max(0.0, min(100.0, round(score, 1)))
    risk_score = round(100.0 - health_score, 1)

    status = determine_status(health_score)
    if health_score >= 80:
        risk_level = "Low"
    elif health_score >= 60:
        risk_level = "Medium"
    elif health_score >= 40:
        risk_level = "High"
    else:
        risk_level = "Critical"

    # Default recommendation if none triggered
    if not recs:
        recs.append("Maintain active touchpoints and monitor buyer timeline through stage progression.")

    supporting_metrics = {
        "days_in_current_stage": days_in_stage,
        "days_overdue": days_overdue,
        "max_discount_pct": round(max_discount, 2),
        "products_count": len(products),
        "activities_count": len(activities),
        "days_since_last_activity": days_since_act,
        "has_primary_contact": bool(opp.primary_contact_id),
        "deal_value_inr": opp.deal_value_inr,
        "probability_pct": opp.probability_pct
    }

    return DealHealthResponse(
        opportunity_id=opp.opportunity_id,
        opportunity_name=opp.opportunity_name or opp.opportunity_id,
        pipeline_stage=opp.pipeline_stage,
        is_closed=False,
        close_outcome=opp.close_outcome,
        health_score=health_score,
        risk_score=risk_score,
        risk_level=risk_level,
        status=status,
        scoring_method="rule_based_heuristic",
        is_ml_model=False,
        contributing_factors=factors,
        mitigation_recommendations=recs,
        supporting_metrics=supporting_metrics,
        insufficient_data=False
    )
