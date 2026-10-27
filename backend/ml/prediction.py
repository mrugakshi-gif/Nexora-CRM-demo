import os
import joblib
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..models import (Lead, Company, Contact, LeadSource, Customer, CustomerTransaction, SupportCase, 
                      Opportunity, SalesRep, LeadStatusHistory)
from .schemas import (LeadConversionResponse, LeadScoringResponse, KeyFactorItem, CustomerSegmentationResponse, 
                      CustomerChurnResponse, SalesForecastResponse, LeadIntelligenceAggregateResponse, CustomerRiskAggregateResponse, CustomerSegmentDistributionResponse, LeadAggregateItem, CustomerRiskAggregateItem)

MODELS_DIR = os.path.join(os.path.dirname(__file__), 'models')

class PredictionService:
    def __init__(self):
        self.models = {}
        self.load_models()
        
    def load_models(self):
        model_files = [
            'lead_conversion_pipeline.joblib',
            'lead_scoring_pipeline.joblib',
            'customer_segmentation_pipeline.joblib',
            'churn_prediction_pipeline.joblib'
        ]
        for mf in model_files:
            path = os.path.join(MODELS_DIR, mf)
            if os.path.exists(path):
                self.models[mf] = joblib.load(path)
            else:
                print(f"Warning: Model artifact {mf} not found at {path}")

    def _get_model(self, name: str):
        model = self.models.get(name)
        if not model:
            raise ValueError(f"Model artifact {name} is unavailable.")
        return model

    def _calculate_budget_band(self, budget):
        if budget is None:
            return "Unknown"
        if float(budget) < 300000:
            return "Low"
        if float(budget) < 1500000:
            return "Mid"
        return "High"

    def predict_lead_conversion(self, db: Session, lead_id: str) -> LeadConversionResponse:
        model_name = "lead_conversion_pipeline.joblib"
        model = self._get_model(model_name)
        
        lead = db.query(Lead).filter(Lead.lead_id == lead_id).first()
        if not lead:
            raise ValueError("Lead not found")
        
        company = lead.company
        contact = lead.contact
        source = lead.lead_source
        
        created_dt = datetime.fromisoformat(lead.created_at)
        cutoff_dt = datetime.fromisoformat(lead.qualified_at) if lead.qualified_at else (
            datetime.fromisoformat(lead.first_contacted_at) if lead.first_contacted_at else created_dt
        )
        now_dt = datetime.utcnow()
        days_since_created = (cutoff_dt - created_dt).days
        
        status_transitions = db.query(LeadStatusHistory).filter(LeadStatusHistory.lead_id == lead_id).count()
        
        six_mo_ago = now_dt - timedelta(days=180)
        rep_leads = db.query(Lead).filter(
            Lead.assigned_rep_id == lead.assigned_rep_id,
            Lead.created_at >= six_mo_ago.isoformat(),
            Lead.lead_status.in_(["Converted", "Lost"])
        ).all()
        converted_count = sum(1 for l in rep_leads if l.lead_status == "Converted")
        rep_conv_rate = converted_count / len(rep_leads) if rep_leads else 0.05
        
        features = {
            "industry_id": company.industry_id if company else "Unknown",
            "region": company.region if company else "Unknown",
            "company_size_at_lead_time": lead.company_size_at_lead_time or "Unknown",
            "lead_source_category": source.source_category if source else "Unknown",
            "campaign_sourced_flag": str(lead.campaign_id is not None),
            "contact_seniority_level": contact.seniority_level if contact else "Unknown",
            "contact_is_decision_maker": str(contact.is_decision_maker) if contact else "False",
            "estimated_budget_known": str(lead.estimated_budget_inr is not None),
            "estimated_budget_band": self._calculate_budget_band(lead.estimated_budget_inr),
            "days_since_created_to_cutoff": days_since_created,
            "num_status_transitions_before_cutoff": status_transitions,
            "rep_assigned_flag": str(lead.assigned_rep_id is not None),
            "rep_trailing_conversion_rate": rep_conv_rate,
            "is_duplicate_lead": str(lead.is_duplicate_of_lead_id is not None)
        }
        
        df = pd.DataFrame([features])
        prob = model.predict_proba(df)[0, 1]
        pred = int(prob >= 0.4)
        
        return LeadConversionResponse(
            lead_id=lead_id,
            conversion_probability=prob,
            prediction=pred,
            model_identifier=model_name
        )

    def predict_lead_scoring(self, db: Session, lead_id: str) -> LeadScoringResponse:
        model_name = "lead_scoring_pipeline.joblib"
        model = self._get_model(model_name)
        
        lead = db.query(Lead).filter(Lead.lead_id == lead_id).first()
        if not lead:
            raise ValueError("Lead not found")
            
        company = lead.company
        contact = lead.contact
        source = lead.lead_source
        
        created_dt = datetime.fromisoformat(lead.created_at)
        cutoff_dt = datetime.fromisoformat(lead.qualified_at) if lead.qualified_at else (
            datetime.fromisoformat(lead.first_contacted_at) if lead.first_contacted_at else created_dt
        )
        now_dt = datetime.utcnow()
        days_since_created = (cutoff_dt - created_dt).days
        
        status_transitions = db.query(LeadStatusHistory).filter(LeadStatusHistory.lead_id == lead_id).count()
        
        six_mo_ago = now_dt - timedelta(days=180)
        rep_leads = db.query(Lead).filter(
            Lead.assigned_rep_id == lead.assigned_rep_id,
            Lead.created_at >= six_mo_ago.isoformat(),
            Lead.lead_status.in_(["Converted", "Lost"])
        ).all()
        converted_count = sum(1 for l in rep_leads if l.lead_status == "Converted")
        rep_conv_rate = converted_count / len(rep_leads) if rep_leads else 0.05

        features = {
            "industry_id": company.industry_id if company else "Unknown",
            "region": company.region if company else "Unknown",
            "company_size_at_lead_time": lead.company_size_at_lead_time or "Unknown",
            "lead_source_category": source.source_category if source else "Unknown",
            "campaign_sourced_flag": str(lead.campaign_id is not None),
            "contact_seniority_level": contact.seniority_level if contact else "Unknown",
            "contact_is_decision_maker": str(contact.is_decision_maker) if contact else "False",
            "contact_department": contact.department if contact else "Unknown",
            "estimated_budget_known": str(lead.estimated_budget_inr is not None),
            "estimated_budget_band": self._calculate_budget_band(lead.estimated_budget_inr),
            "days_since_created_to_cutoff": days_since_created,
            "num_status_transitions_before_cutoff": status_transitions,
            "rep_assigned_flag": str(lead.assigned_rep_id is not None),
            "rep_trailing_conversion_rate": rep_conv_rate
        }
        
        df = pd.DataFrame([features])
        prob = float(model.predict_proba(df)[0, 1])
        
        # Mathematically valid local explanation via instance-level logit decomposition:
        # In logistic regression: z = beta_0 + sum(beta_j * x_j).
        # beta_j * x_j is the exact local additive contribution of feature j to this lead's log-odds.
        key_factors = []
        try:
            preprocessor = model.named_steps.get("preprocessor")
            classifier = model.named_steps.get("classifier")
            if preprocessor and classifier and hasattr(classifier, "coef_"):
                X_trans = preprocessor.transform(df)
                if hasattr(X_trans, "toarray"):
                    X_trans = X_trans.toarray()
                feat_names = preprocessor.get_feature_names_out()
                coefs = classifier.coef_[0]
                contributions = X_trans[0] * coefs

                FEATURE_LABEL_MAP = {
                    "contact_is_decision_maker_True": "Decision Maker Contact",
                    "contact_is_decision_maker_False": "Non-Decision Maker Contact",
                    "rep_assigned_flag_True": "Sales Rep Assigned",
                    "rep_assigned_flag_False": "No Sales Rep Assigned",
                    "campaign_sourced_flag_True": "Sourced via Campaign",
                    "campaign_sourced_flag_False": "Direct / Non-Campaign Sourced",
                    "estimated_budget_known_True": "Estimated Budget Provided",
                    "estimated_budget_known_False": "Budget Not Provided",
                    "num_status_transitions_before_cutoff": "Pipeline Velocity / Stages",
                    "days_since_created_to_cutoff": "Qualification Timing",
                    "rep_trailing_conversion_rate": "Assigned Rep Track Record",
                }

                active_indices = np.where(X_trans[0] != 0)[0]
                scored_factors = []
                for idx in active_indices:
                    raw_name = feat_names[idx].replace("cat__", "").replace("num__", "")
                    contrib = float(contributions[idx])
                    scored_factors.append((raw_name, contrib))

                scored_factors.sort(key=lambda x: abs(x[1]), reverse=True)
                for name, contrib in scored_factors[:5]:
                    impact = "positive" if contrib > 0 else "negative"
                    label = FEATURE_LABEL_MAP.get(name)
                    if not label:
                        label = name.replace("_", " ").title()
                    sign = "+" if contrib > 0 else ""
                    desc = f"{label} ({sign}{round(contrib, 2)} log-odds impact)"
                    key_factors.append(KeyFactorItem(
                        feature=name,
                        impact=impact,
                        contribution=round(contrib, 3),
                        description=desc
                    ))
        except Exception as e:
            import logging
            logging.getLogger(__name__).debug("Lead scoring explanation generation skipped: %s", e)

        return LeadScoringResponse(
            lead_id=lead_id,
            score_probability=prob,
            lead_score=prob,
            key_factors=key_factors,
            model_identifier=model_name
        )

    def predict_customer_segmentation(self, db: Session, customer_id: str) -> CustomerSegmentationResponse:
        model_name = "customer_segmentation_pipeline.joblib"
        model = self._get_model(model_name)
        
        customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
        if not customer:
            raise ValueError("Customer not found")
            
        company = customer.company
        
        now = datetime.utcnow()
        one_yr_ago = now - timedelta(days=365)
        
        # Transactions
        txns = db.query(CustomerTransaction).filter(
            CustomerTransaction.customer_id == customer_id,
            CustomerTransaction.transaction_date >= one_yr_ago.isoformat()
        ).all()
        
        freq = len(txns)
        monetary = sum(t.amount_inr for t in txns)
        if txns:
            last_txn_date = max(datetime.fromisoformat(t.transaction_date) for t in txns)
            recency = (now - last_txn_date).days
        else:
            recency = 365
            
        # Support
        support_cases = db.query(SupportCase).filter(
            SupportCase.customer_id == customer_id,
            SupportCase.opened_at >= one_yr_ago.isoformat()
        ).all()
        support_count = len(support_cases)
        
        scored_cases = [c.satisfaction_score for c in support_cases if c.satisfaction_score is not None]
        avg_sat = sum(scored_cases)/len(scored_cases) if scored_cases else None
        
        try:
            cust_since = datetime.fromisoformat(customer.customer_since)
        except:
            cust_since = now
        tenure = (now - cust_since).days // 30
        
        features = {
            "recency_days_since_last_transaction": recency,
            "frequency_transactions_last_12mo": freq,
            "monetary_total_last_12mo_inr": monetary,
            "tenure_months_at_snapshot": tenure,
            "support_case_count_last_12mo": support_count,
            "avg_satisfaction_score": avg_sat,
            "product_category_diversity": 1, # Default base
            "industry_id": company.industry_id if company else "Unknown",
            "company_size_band": company.company_size_band if company else "Unknown",
            "customer_tier": customer.customer_tier or "Unknown",
            "contract_type": customer.contract_type or "Unknown"
        }
        
        df = pd.DataFrame([features])
        cluster_id = int(model.predict(df)[0])
        
        return CustomerSegmentationResponse(
            customer_id=customer_id,
            cluster_id=cluster_id,
            cluster_info="Cluster assignment generated by KMeans.",
            model_identifier=model_name
        )

    def predict_customer_churn(self, db: Session, customer_id: str) -> CustomerChurnResponse:
        model_name = "churn_prediction_pipeline.joblib"
        model = self._get_model(model_name)
        
        customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
        if not customer:
            raise ValueError("Customer not found")
            
        now = datetime.utcnow()
        ninety_days_ago = now - timedelta(days=90)
        
        try:
            cust_since = datetime.fromisoformat(customer.customer_since)
        except:
            cust_since = now
        tenure = (now - cust_since).days // 30
        
        txns = db.query(CustomerTransaction).filter(CustomerTransaction.customer_id == customer_id).all()
        if txns:
            last_txn = max(datetime.fromisoformat(t.transaction_date) for t in txns)
            days_since_last = (now - last_txn).days
        else:
            days_since_last = tenure * 30
            
        recent_cases = db.query(SupportCase).filter(
            SupportCase.customer_id == customer_id,
            SupportCase.opened_at >= ninety_days_ago.isoformat()
        ).all()
        
        priority_map = {"Critical": 3, "High": 2, "Medium": 1, "Low": 0}
        recent_txns = [t for t in txns if datetime.fromisoformat(t.transaction_date) >= ninety_days_ago]
        curr_90d_amt = sum(t.amount_inr for t in recent_txns)
        
        one_eighty_days_ago = now - timedelta(days=180)
        prev_txns = [t for t in txns if one_eighty_days_ago <= datetime.fromisoformat(t.transaction_date) < ninety_days_ago]
        prev_90d_amt = sum(t.amount_inr for t in prev_txns)
        trend = (curr_90d_amt - prev_90d_amt) / prev_90d_amt if prev_90d_amt > 0 else 0.0
        
        avg_priority = sum(priority_map.get(c.priority, 1) for c in recent_cases)/len(recent_cases) if recent_cases else 0.0
        
        features = {
            "tenure_months_at_snapshot": tenure,
            "days_since_last_transaction_at_snapshot": days_since_last,
            "support_case_count_trailing_90d": len(recent_cases),
            "avg_case_priority_trailing_90d": avg_priority,
            "contract_type": customer.contract_type or "Unknown",
            "customer_tier": customer.customer_tier or "Unknown",
            "transaction_amount_trailing_90d_inr": curr_90d_amt,
            "transaction_amount_trend_90d_inr": trend,
            "horizon_days": 90
        }
        
        df = pd.DataFrame([features])
        prob = model.predict_proba(df)[0, 1]
        pred = int(model.predict(df)[0])
        
        return CustomerChurnResponse(
            customer_id=customer_id,
            churn_probability=prob,
            prediction=pred,
            model_identifier=model_name,
            warnings="Extremely small training dataset (59 rows). Probabilities are directional only."
        )

    def predict_sales_forecast(self, db: Session) -> SalesForecastResponse:
        """
        Calculates a statistical sales forecast baseline.

        Revenue Semantics & Distinction:
        - Production Target: Realized cash collections from CustomerTransaction
          where payment_status == 'Paid' and deleted_at is null.
          Pending, Overdue, and Partially Paid invoices are excluded from realized revenue
          because the schema does not track partial payment receipts (only total invoice amounts).
        - Training Target Distinction: The offline model training dataset (sales_forecasting_dataset.csv)
          used closed-won opportunity deal bookings (Opportunity.deal_value_inr for close_outcome == 'Won').
          The production runtime baseline tracks realized cash collections, which is more directly actionable
          for operational cashflow planning.
        - Prediction Horizon: 1-calendar-month ahead from the evaluation anchor (next incoming calendar month).
        - Historical Window: Evaluates the three most recent fully completed calendar months.
          (For reference date in October 2026, completed months are July, August, September 2026,
          and the forecast period is November 2026).
        """
        now = datetime.utcnow()
        # Next incoming calendar month to forecast (for October 2026, forecast period is 2026-11)
        next_month_dt = (now.replace(day=28) + timedelta(days=4)).replace(day=1)
        period_description = next_month_dt.strftime("%Y-%m")

        def _parse_iso_date(dt_str: str) -> datetime:
            if not dt_str:
                raise ValueError("Empty date string")
            clean_str = dt_str.replace("Z", "").split("+")[0]
            if "T" in clean_str:
                return datetime.fromisoformat(clean_str)
            if len(clean_str) >= 10:
                return datetime.strptime(clean_str[:10], "%Y-%m-%d")
            raise ValueError(f"Unparseable date: {dt_str}")

        def _normalize_cashflow(amt_val, txn_type: str = "") -> float:
            if amt_val is None:
                return 0.0
            try:
                f_val = float(amt_val)
                if not np.isfinite(f_val):
                    return 0.0
            except Exception:
                return 0.0
            is_refund = (txn_type == "Refund") or (f_val < 0)
            return -abs(f_val) if is_refund else abs(f_val)

        def _get_completed_calendar_months(ref_dt: datetime, count: int = 3) -> list[tuple[int, int]]:
            cur = ref_dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            months = []
            for _ in range(count):
                last_day_prev = cur - timedelta(days=1)
                prev_first = last_day_prev.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                months.append((prev_first.year, prev_first.month))
                cur = prev_first
            months.reverse() # [m-count, ..., m-1]
            return months

        completed_months = _get_completed_calendar_months(now, count=3)
        target_yms = [f"{y:04d}-{m:02d}" for y, m in completed_months]
        window_start_iso = f"{completed_months[0][0]:04d}-{completed_months[0][1]:02d}-01"
        window_end_iso = f"{now.year:04d}-{now.month:02d}-01"

        # Check total lifetime distinct paid months to distinguish sparse CRM launch history from genuine zero months
        all_paid_lifetime = db.query(CustomerTransaction).filter(
            CustomerTransaction.deleted_at == None,
            CustomerTransaction.payment_status == "Paid"
        ).all()

        lifetime_months = set()
        for t in all_paid_lifetime:
            if t.transaction_date and len(t.transaction_date) >= 7:
                lifetime_months.add(t.transaction_date[:7])

        # 1. Primary Path: Three most recent fully completed calendar months of realized cash collections
        recent_txns = db.query(CustomerTransaction).filter(
            CustomerTransaction.deleted_at == None,
            CustomerTransaction.payment_status == "Paid",
            CustomerTransaction.transaction_date >= window_start_iso,
            CustomerTransaction.transaction_date < window_end_iso
        ).all()

        if recent_txns:
            monthly_totals = {ym: 0.0 for ym in target_yms}
            for t in recent_txns:
                net_amt = _normalize_cashflow(t.amount_inr, getattr(t, "transaction_type", ""))
                try:
                    dt = _parse_iso_date(t.transaction_date)
                    ym = dt.strftime("%Y-%m")
                except Exception:
                    ym = t.transaction_date[:7] if (t.transaction_date and len(t.transaction_date) >= 7) else None
                if ym in monthly_totals:
                    monthly_totals[ym] += net_amt

            total_realized_rev = sum(monthly_totals.values())

            # If the database has < 3 distinct months across its entire lifetime, evaluate only available months
            if len(lifetime_months) < 3:
                active_months = [ym for ym, amt in monthly_totals.items() if amt != 0.0]
                eval_months = max(1, len(active_months))
                monthly_avg = total_realized_rev / eval_months
                model_identifier = "sparse_trailing_baseline"
                methodology = f"Trailing {eval_months}-Month Realized Revenue Average"
                confidence = "Low (Sparse Trailing History)"
                warning = f"Only {eval_months} distinct month(s) of paid transactions found prior to current period. Average computed over {eval_months} month(s)."
                note = f"Statistical baseline computed over {eval_months} available distinct month(s) of realized transactions."
                eval_count = eval_months
            else:
                # Normal 3 completed calendar months baseline: divide by 3, retaining genuine zero months
                monthly_avg = total_realized_rev / 3.0
                model_identifier = "trailing_3mo_baseline"
                methodology = "Trailing 3-Month Realized Revenue Moving Average"
                confidence = "Medium (Statistical Baseline)"
                warning = None
                note = "Statistical baseline (trailing 3-month realized cash revenue moving average) used due to small sample size in ML training."
                eval_count = 3

            if total_realized_rev < 0:
                warning = (warning + " | " if warning else "") + "Net realized revenue in trailing window is negative due to refunds exceeding gross receipts. Forecast floored at 0.0."

            return SalesForecastResponse(
                period_description=period_description,
                forecast_amount_inr=round(max(0.0, monthly_avg), 2),
                model_identifier=model_identifier,
                baseline_note=note,
                methodology=methodology,
                is_ml_model=False,
                confidence_level=confidence,
                historical_months_evaluated=eval_count,
                trailing_revenue_inr=round(total_realized_rev, 2),
                data_quality_warning=warning
            )

        # 2. Fallback Path 1: Clock drift / Historical transactions exist (> trailing completed calendar months ago)
        if all_paid_lifetime:
            valid_paid_txns = []
            for t in all_paid_lifetime:
                try:
                    dt = _parse_iso_date(t.transaction_date)
                    valid_paid_txns.append((t, dt))
                except Exception:
                    continue

            if valid_paid_txns:
                valid_paid_txns.sort(key=lambda x: x[1], reverse=True)
                latest_txn, latest_dt = valid_paid_txns[0]

                ref_hist = (latest_dt.replace(day=28) + timedelta(days=4)).replace(day=1)
                hist_months = _get_completed_calendar_months(ref_hist, count=3)
                hist_target_yms = [f"{y:04d}-{m:02d}" for y, m in hist_months]
                hist_start_iso = f"{hist_months[0][0]:04d}-{hist_months[0][1]:02d}-01"
                hist_end_iso = f"{ref_hist.year:04d}-{ref_hist.month:02d}-01"

                window_txns = [t for t, dt in valid_paid_txns if hist_start_iso <= t.transaction_date < hist_end_iso]
                if not window_txns:
                    window_txns = [t for t, _ in valid_paid_txns]

                monthly_hist = {}
                for t in window_txns:
                    net_amt = _normalize_cashflow(t.amount_inr, getattr(t, "transaction_type", ""))
                    try:
                        dt = _parse_iso_date(t.transaction_date)
                        ym = dt.strftime("%Y-%m")
                    except Exception:
                        ym = t.transaction_date[:7] if (t.transaction_date and len(t.transaction_date) >= 7) else "unknown"
                    monthly_hist[ym] = monthly_hist.get(ym, 0.0) + net_amt

                distinct_yms = sorted(monthly_hist.keys())
                num_months = len(distinct_yms)
                eval_months = max(1, min(3, num_months))
                recent_eval_yms = distinct_yms[-eval_months:]
                total_realized_rev = sum(monthly_hist[ym] for ym in recent_eval_yms)
                monthly_avg = total_realized_rev / eval_months

                # Horizon: 1 month after latest historical transaction date
                hist_target_month = (latest_dt.replace(day=28) + timedelta(days=4)).replace(day=1)
                hist_period_desc = hist_target_month.strftime("%Y-%m")

                warning = (
                    f"No paid transactions found in trailing 3 completed calendar months from system clock ({now.strftime('%Y-%m-%d')}). "
                    f"Baseline computed using latest available historical transaction window ending {latest_dt.strftime('%Y-%m-%d')} "
                    f"across {eval_months} distinct month(s) ({', '.join(recent_eval_yms)})."
                )

                if total_realized_rev < 0:
                    warning += " Net realized revenue in trailing window is negative due to refunds exceeding gross receipts. Forecast floored at 0.0."

                model_id = "historical_window_baseline"
                return SalesForecastResponse(
                    period_description=hist_period_desc,
                    forecast_amount_inr=round(max(0.0, monthly_avg), 2),
                    model_identifier=model_id,
                    baseline_note="Statistical baseline computed from latest available historical transaction window.",
                    methodology=f"Latest Historical {eval_months}-Month Realized Revenue Average",
                    is_ml_model=False,
                    confidence_level="Low (Historical Baseline Drift)",
                    historical_months_evaluated=eval_months,
                    trailing_revenue_inr=round(total_realized_rev, 2),
                    data_quality_warning=warning
                )

        # 3. Fallback Path 2: Closed-Won Opportunities Monthly Aggregation (when 0 customer transactions exist)
        won_opps = db.query(Opportunity).filter(
            Opportunity.deleted_at == None,
            Opportunity.close_outcome == "Won"
        ).all()

        if won_opps:
            monthly_won = {}
            for o in won_opps:
                raw_val = o.deal_value_inr if o.deal_value_inr is not None else 0.0
                try:
                    f_val = float(raw_val)
                    val = f_val if (np.isfinite(f_val) and f_val > 0) else 0.0
                except Exception:
                    val = 0.0
                cdate = o.actual_close_date or o.expected_close_date or o.created_at
                ym = None
                if cdate:
                    try:
                        dt = _parse_iso_date(cdate)
                        ym = dt.strftime("%Y-%m")
                    except Exception:
                        if len(cdate) >= 7:
                            ym = cdate[:7]
                if ym:
                    monthly_won[ym] = monthly_won.get(ym, 0.0) + val

            if monthly_won:
                sorted_yms = sorted(monthly_won.keys(), reverse=True)
                eval_yms = sorted_yms[:3]
                total_opp_rev = sum(monthly_won[ym] for ym in eval_yms)
                num_months = len(eval_yms)
                monthly_avg = total_opp_rev / num_months

                try:
                    last_ym_dt = datetime.strptime(eval_yms[0], "%Y-%m")
                    opp_target_month = (last_ym_dt.replace(day=28) + timedelta(days=4)).replace(day=1)
                    opp_period_desc = opp_target_month.strftime("%Y-%m")
                except Exception:
                    opp_period_desc = period_description

                warning = (
                    f"No customer transactions found. Baseline calculated from monthly aggregated "
                    f"closed-won opportunity deal bookings across {num_months} distinct month(s) ({', '.join(reversed(eval_yms))})."
                )

                return SalesForecastResponse(
                    period_description=opp_period_desc,
                    forecast_amount_inr=round(max(0.0, monthly_avg), 2),
                    model_identifier="closed_won_opps_monthly_baseline",
                    baseline_note="Opportunity-based monthly baseline derived from closed-won deal bookings.",
                    methodology=f"Closed-Won Opportunity Bookings {num_months}-Month Average",
                    is_ml_model=False,
                    confidence_level="Low (Opportunity Bookings Fallback)",
                    historical_months_evaluated=num_months,
                    trailing_revenue_inr=round(total_opp_rev, 2),
                    data_quality_warning=warning
                )

        # 4. Fallback Path 3: Empty database / No eligible transaction or opportunity history
        return SalesForecastResponse(
            period_description=period_description,
            forecast_amount_inr=0.0,
            model_identifier="insufficient_data",
            baseline_note="Insufficient data to calculate a sales forecast.",
            methodology="None (Insufficient Historical Data)",
            is_ml_model=False,
            confidence_level="None",
            historical_months_evaluated=0,
            trailing_revenue_inr=0.0,
            data_quality_warning="Insufficient transaction and deal history to calculate a sales forecast (0 eligible historical records found)."
        )

# Singleton instance

    def predict_aggregate_leads(self, db: Session, current_user) -> LeadIntelligenceAggregateResponse:
        conv_model_name = "lead_conversion_pipeline.joblib"
        score_model_name = "lead_scoring_pipeline.joblib"
        conv_model = self._get_model(conv_model_name)
        score_model = self._get_model(score_model_name)
        
        query = db.query(Lead)
        if current_user.role not in ["Admin", "Manager", "System Admin", "Sales Manager"]:
            query = query.filter(Lead.assigned_rep_id == current_user.rep_id)
            
        leads = query.all()
        if not leads:
            return LeadIntelligenceAggregateResponse(top_leads=[], model_identifier=f"{score_model_name} & {conv_model_name}")
            
        now_dt = datetime.utcnow()
        six_mo_ago = now_dt - timedelta(days=180)
        
        # Batch query for features
        all_rep_ids = list(set([l.assigned_rep_id for l in leads if l.assigned_rep_id]))
        if all_rep_ids:
            recent_rep_leads = db.query(Lead.assigned_rep_id, Lead.lead_status).filter(
                Lead.assigned_rep_id.in_(all_rep_ids),
                Lead.created_at >= six_mo_ago.isoformat(),
                Lead.lead_status.in_(["Converted", "Lost"])
            ).all()
            rep_stats = {}
            for r_id, status in recent_rep_leads:
                if r_id not in rep_stats:
                    rep_stats[r_id] = {'total': 0, 'converted': 0}
                rep_stats[r_id]['total'] += 1
                if status == "Converted":
                    rep_stats[r_id]['converted'] += 1
        else:
            rep_stats = {}
            
        # status transitions counts
        lead_ids = [l.lead_id for l in leads]
        from sqlalchemy import func
        status_counts_q = db.query(LeadStatusHistory.lead_id, func.count(LeadStatusHistory.history_id)).filter(
            LeadStatusHistory.lead_id.in_(lead_ids)
        ).group_by(LeadStatusHistory.lead_id).all()
        status_counts = {lid: count for lid, count in status_counts_q}

        conv_features = []
        score_features = []
        for lead in leads:
            company = lead.company
            contact = lead.contact
            source = lead.lead_source
            
            created_dt = datetime.fromisoformat(lead.created_at)
            cutoff_dt = datetime.fromisoformat(lead.qualified_at) if lead.qualified_at else (
                datetime.fromisoformat(lead.first_contacted_at) if lead.first_contacted_at else created_dt
            )
            days_since_created = (cutoff_dt - created_dt).days
            status_transitions = status_counts.get(lead.lead_id, 0)
            
            rep_id = lead.assigned_rep_id
            if rep_id in rep_stats:
                rep_conv_rate = rep_stats[rep_id]['converted'] / rep_stats[rep_id]['total'] if rep_stats[rep_id]['total'] > 0 else 0.05
            else:
                rep_conv_rate = 0.05
                
            conv_features.append({
                "industry_id": company.industry_id if company else "Unknown",
                "region": company.region if company else "Unknown",
                "company_size_at_lead_time": lead.company_size_at_lead_time or "Unknown",
                "lead_source_category": source.source_category if source else "Unknown",
                "campaign_sourced_flag": str(lead.campaign_id is not None),
                "contact_seniority_level": contact.seniority_level if contact else "Unknown",
                "contact_is_decision_maker": str(contact.is_decision_maker) if contact else "False",
                "estimated_budget_known": str(lead.estimated_budget_inr is not None),
                "estimated_budget_band": self._calculate_budget_band(lead.estimated_budget_inr),
                "days_since_created_to_cutoff": days_since_created,
                "num_status_transitions_before_cutoff": status_transitions,
                "rep_assigned_flag": str(rep_id is not None),
                "rep_trailing_conversion_rate": rep_conv_rate,
                "is_duplicate_lead": str(lead.is_duplicate_of_lead_id is not None)
            })
            
            score_features.append({
                "industry_id": company.industry_id if company else "Unknown",
                "region": company.region if company else "Unknown",
                "company_size_at_lead_time": lead.company_size_at_lead_time or "Unknown",
                "lead_source_category": source.source_category if source else "Unknown",
                "campaign_sourced_flag": str(lead.campaign_id is not None),
                "contact_seniority_level": contact.seniority_level if contact else "Unknown",
                "contact_is_decision_maker": str(contact.is_decision_maker) if contact else "False",
                "contact_department": contact.department if contact else "Unknown",
                "estimated_budget_known": str(lead.estimated_budget_inr is not None),
                "estimated_budget_band": self._calculate_budget_band(lead.estimated_budget_inr),
                "days_since_created_to_cutoff": days_since_created,
                "num_status_transitions_before_cutoff": status_transitions,
                "rep_assigned_flag": str(rep_id is not None),
                "rep_trailing_conversion_rate": rep_conv_rate
            })
            
        conv_df = pd.DataFrame(conv_features)
        score_df = pd.DataFrame(score_features)
        
        conv_probs = conv_model.predict_proba(conv_df)[:, 1]
        score_probs = score_model.predict_proba(score_df)[:, 1]
        
        aggregate_items = []
        for i, lead in enumerate(leads):
            aggregate_items.append(LeadAggregateItem(
                lead_id=lead.lead_id,
                company_name=lead.company.company_name if lead.company else "Unknown",
                score_probability=float(score_probs[i]),
                conversion_probability=float(conv_probs[i])
            ))
            
        aggregate_items.sort(key=lambda x: x.score_probability, reverse=True)
        return LeadIntelligenceAggregateResponse(
            top_leads=aggregate_items,
            model_identifier=f"{score_model_name} & {conv_model_name}"
        )

    def predict_aggregate_customers_risk(self, db: Session, current_user) -> CustomerRiskAggregateResponse:
        model_name = "churn_prediction_pipeline.joblib"
        model = self._get_model(model_name)
        
        query = db.query(Customer)
        if current_user.role not in ["Admin", "Manager", "System Admin", "Sales Manager"]:
            query = query.filter(Customer.csm_rep_id == current_user.rep_id)
            
        customers = query.all()
        if not customers:
            return CustomerRiskAggregateResponse(top_at_risk_customers=[], model_identifier=model_name)
            
        now = datetime.utcnow()
        ninety_days_ago = now - timedelta(days=90)
        one_eighty_days_ago = now - timedelta(days=180)
        
        customer_ids = [c.customer_id for c in customers]
        
        # Batch support cases
        all_cases = db.query(SupportCase).filter(
            SupportCase.customer_id.in_(customer_ids),
            SupportCase.opened_at >= ninety_days_ago.isoformat()
        ).all()
        
        cases_by_cust = {}
        for c in all_cases:
            cases_by_cust.setdefault(c.customer_id, []).append(c)
            
        # Batch transactions
        all_txns = db.query(CustomerTransaction).filter(
            CustomerTransaction.customer_id.in_(customer_ids)
        ).all()
        
        txns_by_cust = {}
        for t in all_txns:
            txns_by_cust.setdefault(t.customer_id, []).append(t)
            
        priority_map = {"Critical": 3, "High": 2, "Medium": 1, "Low": 0}
        
        features = []
        for cust in customers:
            try:
                cust_since = datetime.fromisoformat(cust.customer_since)
            except:
                cust_since = now
            tenure = (now - cust_since).days // 30
            
            cust_txns = txns_by_cust.get(cust.customer_id, [])
            if cust_txns:
                last_txn = max(datetime.fromisoformat(t.transaction_date) for t in cust_txns)
                days_since_last = (now - last_txn).days
            else:
                days_since_last = tenure * 30
                
            cust_cases = cases_by_cust.get(cust.customer_id, [])
            avg_priority = sum(priority_map.get(c.priority, 1) for c in cust_cases)/len(cust_cases) if cust_cases else 0.0
            
            recent_txns = [t for t in cust_txns if datetime.fromisoformat(t.transaction_date) >= ninety_days_ago]
            curr_90d_amt = sum(t.amount_inr for t in recent_txns)
            
            prev_txns = [t for t in cust_txns if one_eighty_days_ago <= datetime.fromisoformat(t.transaction_date) < ninety_days_ago]
            prev_90d_amt = sum(t.amount_inr for t in prev_txns)
            trend = (curr_90d_amt - prev_90d_amt) / prev_90d_amt if prev_90d_amt > 0 else 0.0
            
            features.append({
                "tenure_months_at_snapshot": tenure,
                "days_since_last_transaction_at_snapshot": days_since_last,
                "support_case_count_trailing_90d": len(cust_cases),
                "avg_case_priority_trailing_90d": avg_priority,
                "contract_type": cust.contract_type or "Unknown",
                "customer_tier": cust.customer_tier or "Unknown",
                "transaction_amount_trailing_90d_inr": curr_90d_amt,
                "transaction_amount_trend_90d_inr": trend,
                "horizon_days": 90
            })
            
        df = pd.DataFrame(features)
        probs = model.predict_proba(df)[:, 1]
        
        aggregate_items = []
        for i, cust in enumerate(customers):
            aggregate_items.append(CustomerRiskAggregateItem(
                customer_id=cust.customer_id,
                company_name=cust.company.company_name if cust.company else "Unknown",
                churn_probability=float(probs[i])
            ))
            
        aggregate_items.sort(key=lambda x: x.churn_probability, reverse=True)
        return CustomerRiskAggregateResponse(
            top_at_risk_customers=aggregate_items,
            model_identifier=model_name
        )

    def predict_aggregate_segments(self, db: Session, current_user) -> CustomerSegmentDistributionResponse:
        model_name = "customer_segmentation_pipeline.joblib"
        model = self._get_model(model_name)
        
        query = db.query(Customer)
        if current_user.role not in ["Admin", "Manager", "System Admin", "Sales Manager"]:
            query = query.filter(Customer.csm_rep_id == current_user.rep_id)
            
        customers = query.all()
        if not customers:
            return CustomerSegmentDistributionResponse(distribution={}, model_identifier=model_name)
            
        customer_ids = [c.customer_id for c in customers]
        now = datetime.utcnow()
        one_yr_ago = now - timedelta(days=365)
        
        all_txns = db.query(CustomerTransaction).filter(
            CustomerTransaction.customer_id.in_(customer_ids),
            CustomerTransaction.transaction_date >= one_yr_ago.isoformat()
        ).all()
        txns_by_cust = {}
        for t in all_txns:
            txns_by_cust.setdefault(t.customer_id, []).append(t)
            
        all_cases = db.query(SupportCase).filter(
            SupportCase.customer_id.in_(customer_ids),
            SupportCase.opened_at >= one_yr_ago.isoformat()
        ).all()
        cases_by_cust = {}
        for c in all_cases:
            cases_by_cust.setdefault(c.customer_id, []).append(c)
            
        features = []
        for cust in customers:
            company = cust.company
            cust_txns = txns_by_cust.get(cust.customer_id, [])
            freq = len(cust_txns)
            monetary = sum(t.amount_inr for t in cust_txns)
            if cust_txns:
                last_txn_date = max(datetime.fromisoformat(t.transaction_date) for t in cust_txns)
                recency = (now - last_txn_date).days
            else:
                recency = 365
                
            cust_cases = cases_by_cust.get(cust.customer_id, [])
            support_count = len(cust_cases)
            scored_cases = [c.satisfaction_score for c in cust_cases if c.satisfaction_score is not None]
            avg_sat = sum(scored_cases)/len(scored_cases) if scored_cases else None
            
            try:
                cust_since = datetime.fromisoformat(cust.customer_since)
            except:
                cust_since = now
            tenure = (now - cust_since).days // 30
            
            features.append({
                "recency_days_since_last_transaction": recency,
                "frequency_transactions_last_12mo": freq,
                "monetary_total_last_12mo_inr": monetary,
                "tenure_months_at_snapshot": tenure,
                "support_case_count_last_12mo": support_count,
                "avg_satisfaction_score": avg_sat,
                "product_category_diversity": 1,
                "industry_id": company.industry_id if company else "Unknown",
                "company_size_band": company.company_size_band if company else "Unknown",
                "customer_tier": cust.customer_tier or "Unknown",
                "contract_type": cust.contract_type or "Unknown"
            })
            
        df = pd.DataFrame(features)
        preds = model.predict(df)
        
        distribution = {}
        for p in preds:
            cluster_id = int(p)
            distribution[cluster_id] = distribution.get(cluster_id, 0) + 1
            
        return CustomerSegmentDistributionResponse(
            distribution=distribution,
            model_identifier=model_name
        )

prediction_service = PredictionService()
