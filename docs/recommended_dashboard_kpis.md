# Recommended Dashboard KPIs

Grouped by audience, with the source table(s)/computation each draws from. Figures in parentheses are this pilot batch's actual values, as a sanity-check reference — not targets.

## Executive / leadership dashboard

| KPI | Computation | Source |
|---|---|---|
| Total open pipeline value | Σ `deal_value_inr` where `pipeline_stage` not in (Closed Won, Closed Lost) | opportunities |
| Weighted pipeline (forecast) | Σ `deal_value_inr × probability_pct/100` over open opportunities | opportunities |
| Win rate (trailing period) | Closed Won ÷ (Closed Won + Closed Lost) | opportunities (46.4% in this batch) |
| Revenue this month / quarter | Σ `amount_inr` from `customer_transactions` in period | customer_transactions |
| New customers this period | count of `customers` with `customer_since` in period | customers |
| Active customer count & MRR-equivalent | count where `customer_status = Active`; sum of latest-period transaction amounts normalized to monthly by `contract_type` cadence | customers, customer_transactions |
| At-risk revenue | Σ deal value of customers with `customer_status = At Risk`, or flagged by the churn model | customers, churn_prediction_dataset |
| Lead → Customer conversion rate | Converted leads that produced a Closed-Won opportunity ÷ total leads | leads, opportunities |

## Sales manager dashboard

| KPI | Computation |
|---|---|
| Pipeline by stage (funnel chart) | count and Σ deal_value_inr grouped by `pipeline_stage` |
| Pipeline by rep | grouped by `owner_rep_id`, joined to `sales_reps.full_name` |
| Average deal cycle length | avg(`actual_close_date` − `created_at`) for Closed Won, by rep/department/product |
| Stage-to-stage conversion rate | from `opportunity_stage_history`: for each `stage_from`, % of transitions that go forward vs. to Closed Lost |
| Rep quota attainance | Σ Closed Won `deal_value_inr` per rep in period ÷ target (target not in this dataset — needs a `sales_targets` table if you add quotas) |
| Forecast vs. actual (this month) | `sales_forecasting_dataset.label_actual_amount_inr` vs. the model's or manual forecast |
| Deals stalling (no stage change in N days) | latest `opportunity_stage_history.changed_at` per open opportunity vs. today |

## Marketing dashboard

| KPI | Computation |
|---|---|
| Leads by source | count grouped by `lead_source_id` → `lead_sources.source_name` |
| Lead source → conversion rate | Converted count ÷ total count, grouped by source |
| Campaign ROI | (Σ attributed Closed-Won `deal_value_inr` via `opportunities.source_lead_id` → `leads.campaign_id`) ÷ `campaigns.budget_inr` |
| Campaign response rate | count(`campaign_responses`) ÷ estimated audience (not directly in this dataset — track your own send volume) |
| MQL/SQL funnel by campaign | count of leads reaching each `lead_status`, grouped by `campaign_id` |

## Customer success dashboard

| KPI | Computation |
|---|---|
| Customer health score (composite) | weighted combination of: recency of last transaction, open/escalated support case count, satisfaction score trend, renewal proximity — model this the same way `churn_prediction_dataset`'s features are built, but compute it live rather than at fixed checkpoints |
| Churn risk list | customers with high predicted churn probability from a model trained on `churn_prediction_dataset`, ranked |
| Renewal calendar | customers with `renewal_date` in the next 30/60/90 days |
| Support case load & SLA | open case count by priority; avg resolution time (`resolved_at` − `opened_at`) by priority, vs. an SLA target |
| CSAT trend | rolling average of `satisfaction_score` over time, by CSM and overall |
| Upsell/downgrade rate | count of `transaction_type = Upsell` vs. `Downgrade` per period, as a % of active customers |
| Revenue at risk by tier | Σ deal value of `At Risk` customers, grouped by `customer_tier` |

## Data-quality / ops dashboard (operational meta-KPIs, not business KPIs)

| KPI | Computation |
|---|---|
| Unassigned lead backlog | count of leads with `assigned_rep_id` blank and `lead_status = New` |
| Leads with no follow-up | leads with `first_contacted_at` blank and age > N days |
| Open opportunities past expected close date | `expected_close_date < today` and `pipeline_stage` not in (Closed Won, Closed Lost) |
| Validator pass rate | last run of `scripts/validation/validate_dataset.py` — 0 unresolved violations is the target; surface this if the dashboard also monitors data pipeline health |

## Notes on building these against the source tables vs. the ML datasets

Most of these KPIs should query the **live source tables** directly (they need "as of right now" values), not the ML-ready datasets, which are point-in-time snapshots built for model training. The one exception is the churn-risk and lead-scoring widgets, which should call your deployed model (trained on `churn_prediction_dataset`/`lead_scoring_dataset`) rather than recomputing a heuristic score in SQL — that keeps the dashboard's number consistent with whatever model version is actually in production.
