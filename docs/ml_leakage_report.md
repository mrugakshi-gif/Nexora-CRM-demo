# ML Leakage Report

Generated from the final validation run (`scripts/validation/validate_dataset.py`) against the 5 ML-ready CSVs shipped in this package. Source: `data/full_audit_report.json`, section `21_ml_target_leakage` (plus the recompute checks described below). For the rules and reasoning behind each check, see `docs/ml_leakage_prevention.md`.

## Result: 0 leakage violations across all 5 datasets

| # | Check | Dataset | Result |
|---|---|---|---|
| 1 | Observation cutoff never falls after the lead's `converted_at` | lead_conversion_dataset | **0 violations** |
| 2 | Observation cutoff equals `leads.created_at` exactly (strict day-0) | lead_scoring_dataset | **0 violations** |
| 3 | Forbidden post-day-0 columns absent (`num_status_transitions_before_cutoff`, `estimated_budget_inr`, `rep_trailing_conversion_rate`, `qualified_at`, `converted_at`) | lead_scoring_dataset | **confirmed absent** |
| 4 | `pipeline_value_open_at_period_start_inr` independently recomputed from `opportunities` and matches stored value | sales_forecasting_dataset | **0 mismatches** |
| 5 | Recency (`recency_days_since_last_transaction`) never negative | customer_segmentation_dataset | **0 violations** |
| 6 | No cluster/segment-label column present at all (removed entirely — see `data_quality_report.md` §1.9) | customer_segmentation_dataset | **confirmed absent** |
| 7 | `transaction_amount_trailing_90d_inr` independently recomputed from `customer_transactions` and matches stored value | churn_prediction_dataset | **0 mismatches** |
| 8 | `customer_status` column absent (would leak the churn outcome) | churn_prediction_dataset | **confirmed absent** |

## Chronological split integrity

| Dataset | Split column | Max `train` value ≤ Min `test` value? |
|---|---|---|
| lead_conversion_dataset | observation_cutoff_at | Yes |
| lead_scoring_dataset | observation_cutoff_at | Yes |
| sales_forecasting_dataset | period_start | Yes |
| churn_prediction_dataset | observation_snapshot_date | Yes |

`customer_segmentation_dataset` has no `dataset_split` (unsupervised task — see `ml_dataset_documentation.md`).

All four time-ordered datasets were split chronologically, not randomly: every `train` row's observation point is at or before every `validation`/`test` row's observation point for that dataset. This means a model trained on `train` is never exposed, even indirectly through a near-duplicate row, to information from later in time than what it's evaluated on.

## Class balance (not leakage per se, but checked alongside it — category 22)

| Dataset | Label | Positive rate |
|---|---|---|
| lead_conversion_dataset | label_converted | 18.3% |
| lead_scoring_dataset | label_converted | 18.3% |
| churn_prediction_dataset | label_churned_within_horizon | 25.4% |

None of these are degenerate (no class below ~2% or above ~90%), so standard classification metrics (PR-AUC recommended given the imbalance) remain meaningful without extreme resampling.

## Source-vs-ML duplication check (category 23)

`lead_scoring_dataset` intentionally carries forward two day-0 columns also present in `leads` (`company_id`, `company_size_at_lead_time`) — this is standard feature denormalization for a model-ready table, not leakage or redundant storage; neither column is derived from anything after the observation cutoff.

**Conclusion:** every leakage-prevention rule declared for this dataset (see `ml_leakage_prevention.md`) is independently verified true against the final CSVs. No feature in any of the 5 ML-ready datasets was computed from data timestamped after that row's observation point, and no target-derived or outcome-adjacent column was left in as a feature.
