# ML-Ready Derived Datasets — Documentation

All five datasets below are built **entirely by reading the validated Phase 1–3 CRM source tables** (`companies`, `contacts`, `leads`, `lead_status_history`, `sales_reps`, `departments`, `lead_sources`, `opportunities`, `opportunity_products`, `products`, `customers`, `customer_transactions`, `customer_support_cases`) — nothing here is independently invented. Each is a **regenerable snapshot**, not part of the operational schema: rerunning `generate_ml_datasets.py` against the same source tables reproduces the same output deterministically (fixed seed). Scale note: these are built from the pilot-scale dataset generated so far (1,200 companies, 1,083 leads, 201 opportunities, 46 customers) — row counts are proportionally small; the feature/label logic is what would carry forward unchanged at full scale.

---

## 1. lead_conversion_dataset.csv

| | |
|---|---|
| **Business objective** | Predict, once a lead has been engaged, whether it will ultimately become an opportunity (a genuine sales pursuit), so reps can prioritize follow-up effort. |
| **Prediction target** | `label_converted` (binary) |
| **Unit of observation** | One row per lead |
| **Time window** | All leads in `leads.csv` (created Jul 2022 – Sep 2026) |
| **Data sources** | `leads`, `lead_status_history`, `contacts`, `companies`, `lead_sources` |
| **Train/val/test split** | **Chronological** by `observation_cutoff_at` — earliest 70% train, next 15% validation, most recent 15% test. Never random: a random split would let the model see near-future leads during training and evaluate on near-past ones, which doesn't match how the model will actually be used (always predicting forward from today). |
| **Class distribution** | 18.6% positive (201/1083) — close to the design target of ~18–20%, not artificially balanced |

**Feature-generation logic:** `observation_cutoff_at` = `qualified_at` if the lead ever reached MQL, else `first_contacted_at`, else `created_at` — i.e., the latest point still strictly *before* any conversion could have happened. All features are computed using only information dated at or before that cutoff: firmographics (`industry_id`, `region`, `company_size_at_lead_time` — the *snapshot* size, not today's), `lead_source_category`, `campaign_sourced_flag`, contact attributes (fixed at contact creation, so always safe), `days_since_created_to_cutoff`, `num_status_transitions_before_cutoff` (count of `lead_status_history` rows dated ≤ cutoff), `rep_assigned_flag`, and `rep_trailing_conversion_rate` — a genuinely leakage-safe rolling rate computed only from leads *created earlier* than this lead and already resolved before this lead's cutoff (falls back to a global trailing rate if the rep has fewer than 5 prior resolved leads).

**Target-generation logic:** `label_converted` = `True` iff `leads.lead_status == 'Converted'` as of the final delivered state of the leads table (set in Phase 3 only for leads that actually produced an opportunity).

**Data dictionary:**
| Column | Type | Description |
|---|---|---|
| ml_record_id | string PK | |
| lead_id | string | traces to `leads.lead_id` |
| company_id | string | traces to `companies.company_id` |
| observation_cutoff_at | datetime | feature computation boundary |
| industry_id, region, company_size_at_lead_time | categorical | firmographic snapshot |
| lead_source_category | enum (Inbound/Outbound/Referral/Partner) | |
| campaign_sourced_flag | bool | |
| contact_seniority_level, contact_is_decision_maker | categorical/bool | |
| estimated_budget_known, estimated_budget_band | bool / enum (Low/Mid/High/Unknown) | see leakage note below |
| days_since_created_to_cutoff | int | |
| num_status_transitions_before_cutoff | int | |
| rep_assigned_flag, rep_trailing_conversion_rate | bool / float 0–1 | |
| is_duplicate_lead | bool | |
| label_converted | bool | **target** |
| dataset_split | enum | train/validation/test |

**Leakage risks (audited):**
- `opportunities.probability_pct` and any post-conversion field (`converted_at`, opportunity IDs) — **excluded entirely**, never computed into this table.
- `estimated_budget_known`/`estimated_budget_band` — **flagged as a medium risk inherited from source generation**: in Phase 2, a lead's *final* funnel stage influenced how often its budget field was left blank (early-stage leads had 60% missingness vs. 15% for later-stage). Since `label_converted` requires first reaching Sales Qualified, there's a soft mechanical correlation between "budget known" and "progressed past early stage" that isn't a purely causal business signal. Kept in the dataset (it's realistic that reps *do* capture budget more diligently on promising leads) but documented so a modeler can run a sensitivity check (train with/without it) rather than trust it blindly.
- Validated: 0 rows where `observation_cutoff_at` falls after `converted_at`; label matches `leads.lead_status` with 0 mismatches.

**Example modeling plan:** Logistic regression or gradient-boosted trees (LightGBM/XGBoost) with class-weighting for the 18.6% positive rate; evaluate with PR-AUC (not just ROC-AUC, given imbalance) and calibration curves since the output feeds prioritization scoring; time-based cross-validation (rolling-origin) rather than k-fold, consistent with the chronological split.

---

## 2. lead_scoring_dataset.csv

| | |
|---|---|
| **Business objective** | Score a lead *at the moment it arrives* (before any sales engagement), to route/prioritize inbound volume. |
| **Prediction target** | `label_converted` (binary) — same eventual outcome, different observation point |
| **Unit of observation** | One row per lead |
| **Time window** | Same as above |
| **Data sources** | `leads`, `contacts`, `companies`, `lead_sources` (deliberately **not** `lead_status_history` — see below) |
| **Train/val/test split** | Chronological, same method as lead_conversion_dataset |
| **Class distribution** | 18.6% positive — identical base rate to lead_conversion_dataset (same leads, same eventual label), but the *features* are far weaker signals, which is expected and realistic for a day-0 model |

**Feature-generation logic:** `observation_cutoff_at` = `leads.created_at` exactly, with **zero engagement-derived features** — no status-transition counts, no rep-assignment history, no budget field. This is the design decision that separates this dataset from lead_conversion_dataset: it answers "how promising does this lead look on arrival," not "how is this lead progressing." `estimated_budget_inr` is excluded here for the same reason flagged above, but more strictly — at true day 0 it would be almost entirely unknown anyway.

**Target-generation logic:** identical to lead_conversion_dataset.

**Data dictionary:** same shape as lead_conversion_dataset minus `estimated_budget_*`, `days_since_created_to_cutoff`, `num_status_transitions_before_cutoff`, `rep_assigned_flag`, `rep_trailing_conversion_rate`, `is_duplicate_lead`; adds `contact_department`.

**Leakage risks (audited):** Verified programmatically that `observation_cutoff_at` equals `leads.created_at` for every row (0 mismatches) and that none of the forbidden engagement columns exist in the file (0 found). This is the strictest-cutoff dataset of the five by design.

**Example modeling plan:** A simple, monotonic-constrained model (logistic regression or a shallow GBM with monotonic constraints on e.g. decision-maker flag) is preferable here over a complex model — day-0 signal is inherently weak, and an opaque model risks fitting noise. Expect meaningfully lower AUC than lead_conversion_dataset; that gap is itself informative (it quantifies how much predictive value comes from actual sales engagement vs. static firmographics).

---

## 3. sales_forecasting_dataset.csv

| | |
|---|---|
| **Business objective** | Forecast next-period revenue per sales department, to support pipeline/quota planning. |
| **Prediction target** | `label_actual_amount_inr` (continuous) — realized Closed-Won revenue in the period |
| **Unit of observation** | One row per (department, calendar month) |
| **Time window** | Feb 2023 – Aug 2026 (44 months × the 4 departments whose reps actually own opportunities: Enterprise Sales, SMB Sales, Inside Sales, Channel Partnerships) |
| **Data sources** | `opportunities`, `sales_reps`, `departments` |
| **Train/val/test split** | Chronological by `period_start` — earliest 70/15/15. This is the clearest case for time-aware splitting: a random split would leak later-period trend information into earlier-period training. |
| **Class distribution** | Continuous target; 20.9% of periods have nonzero realized revenue (79% are legitimate zero-revenue months — a department with a handful of reps and long enterprise sales cycles often closes nothing in a given month; this is realistic sparsity, not a data defect) |

**Feature-generation logic:** every feature is computed using **only opportunities created before `period_start`** and, for trailing-window features, only outcomes with `actual_close_date` before `period_start`: `pipeline_value_open_at_period_start_inr` (sum of open deal value), `num_open_opportunities_at_period_start`, `historical_win_rate_trailing_3mo`, `revenue_trailing_3mo_inr`, `avg_deal_cycle_days_trailing_6mo`, `active_rep_count` (as of period start), `seasonality_month`.

**Target-generation logic:** `label_actual_amount_inr` = sum of `deal_value_inr` for that department's opportunities with `close_outcome='Won'` and `actual_close_date` falling inside the period — this is realized revenue *during* the period, which is legitimately later than every feature's cutoff (that's what makes it a forecast rather than a leak).

**Data dictionary:**
| Column | Type | Description |
|---|---|---|
| ml_record_id | string PK | |
| department_id, department_name | string | |
| period_label, period_start | string / date | e.g. "2025-03", 2025-03-01 |
| pipeline_value_open_at_period_start_inr | float | feature |
| num_open_opportunities_at_period_start | int | feature |
| historical_win_rate_trailing_3mo | float 0–1 or null | feature (null = no closed deals in trailing window) |
| revenue_trailing_3mo_inr | float | feature |
| avg_deal_cycle_days_trailing_6mo | float or null | feature |
| active_rep_count | int | feature |
| seasonality_month | int 1–12 | feature |
| label_actual_amount_inr | float | **target** |
| dataset_split | enum | |

**Leakage risks (audited):** independently re-derived `pipeline_value_open_at_period_start_inr` straight from `opportunities.csv` for every row and confirmed it matches the stored feature exactly (0 mismatches) — this specifically checks that no opportunity closing *during or after* the period was accidentally folded into the "as of period start" pipeline snapshot. No feature references `label_actual_amount_inr`'s own period.

**Example modeling plan:** Given the small scale (172 rows, mostly zero), a two-stage model works better than a single regressor: (1) a classifier for "will this department close ≥1 deal this month," (2) a regressor (or simple trailing-average baseline) for amount conditional on closing something. At full dataset scale this collapses into a standard rolling-window gradient-boosted regressor or a light time-series model (e.g. per-department exponential smoothing with the engineered features as exogenous regressors).

---

## 4. customer_segmentation_dataset.csv

| | |
|---|---|
| **Business objective** | Group customers into behavioral/value segments (e.g. RFM-style) to target retention, upsell, and support investment differently by segment. |
| **Prediction target** | None — unsupervised. There is deliberately **no** cluster-label column in this table (see note below); cluster assignments are a downstream modeling *output*, produced by running your own clustering model against these features, never an input shipped with the data. |
| **Unit of observation** | One row per (customer, quarter-end snapshot) from `customer_since` through today |
| **Time window** | Apr 2023 – Sep 2026 |
| **Data sources** | `customers`, `customer_transactions`, `customer_support_cases`, `opportunities`, `opportunity_products`, `companies` |
| **Train/val/test split** | Not applicable — unsupervised tasks don't require leakage-controlled splits the way supervised ones do. `snapshot_date` is included so a modeler can still hold out the most recent snapshot per customer for stability-of-clustering checks if desired. |
| **Distribution** | 244 snapshot-rows across all 48 customers |

**Feature-generation logic:** classic RFM plus firmographic and support context, all computed using only transactions/cases dated ≤ `snapshot_date`: `recency_days_since_last_transaction`, `frequency_transactions_last_12mo`, `monetary_total_last_12mo_inr`, `tenure_months_at_snapshot`, `support_case_count_last_12mo`, `avg_satisfaction_score` (from resolved cases in the SAME trailing-12mo window as `support_case_count_last_12mo` — a window-mismatch bug here was found and fixed; see `data_quality_report.md` §1.7), `product_category_diversity` (distinct product categories on the originating opportunity), `industry_id`, `company_size_band`, `customer_tier`, `contract_type`.

**Target-generation logic:** none — this is intentional.

**No cluster-label column, by design.** An earlier revision of this table shipped a `segment_label_cluster_id` column that was always 100% blank — a misleading placeholder for a downstream clustering model's output, not an input feature. It has been removed from the schema entirely (not just left blank) so the table can never be mistaken for a pre-labeled/supervised dataset. See `ml_leakage_prevention.md` rule 9.4 and `data_quality_report.md` §1.9.

**Data dictionary:** see feature list above; all traceable via `customer_id` → `customers.csv` and `company_id` → `companies.csv`.

**Leakage risks (audited):** confirmed `recency_days_since_last_transaction` is never negative (0 violations — would indicate a future transaction leaking into a past snapshot), and confirmed the table carries no cluster/segment-label column at all (`full_audit_report.json` → `21_ml_target_leakage.segmentation.cluster_id_column_present` = `false`) so nothing resembling a target can accidentally be read back in as a feature.

**Example modeling plan:** Standardize numeric features, one-hot or target-encode categoricals, run K-means (with silhouette/elbow to pick k) or a Gaussian mixture model for softer boundaries; given only 45 customers, treat cluster counts as illustrative rather than statistically robust until the dataset scales up — this is a case where the *pipeline* is what's being validated at pilot scale, not the segment definitions themselves yet.

---

## 5. churn_prediction_dataset.csv

| | |
|---|---|
| **Business objective** | Predict, ahead of each contract renewal, whether the customer will actually renew — to trigger proactive Customer Success intervention. |
| **Prediction target** | `label_churned_within_horizon` (binary) |
| **Unit of observation** | One row per (customer, renewal-cycle checkpoint), snapshotted 30 days before that cycle's renewal is due |
| **Time window** | One checkpoint per contract cadence (Monthly/Annual/Multi-Year) per customer, from `customer_since` up to `today − ~75 days` (enough runway to honestly observe the outcome) |
| **Data sources** | `customers`, `customer_transactions`, `customer_support_cases` |
| **Train/val/test split** | Chronological by `observation_snapshot_date` |
| **Class distribution** | 28.1% churn rate (9/32) — realistic, not extreme |

**Feature-generation logic — and a documented correction:** No `customer_churn_events` table exists yet in this dataset (out of scope for this phase, same rule applied to `leads.lead_status='Converted'` in earlier phases), so churn is necessarily a **proxy label**, defined here as: *no `Renewal`-type transaction lands within a window around the customer's next contractually-due renewal date*. My first implementation used a fixed calendar rule ("no transaction at all in the next 90 days") and it produced a 90.8% positive rate — I caught this as an artifact, not a signal: Annual and Multi-Year customers (the majority here) legitimately go many months between transactions by design, so a flat 90-day window mislabels nearly every healthy customer as churned. I corrected it to tie the label to each customer's **own** contract cadence — one checkpoint per renewal cycle, 30 days before it's due, checking a ±15/+45-day window around the actual due date for a `Renewal` transaction — which is both the standard subscription-churn framing and consistent with how Phase 3 itself decided renew/non-renew. After a customer's first missed renewal, no further checkpoints are generated for them (the relationship effectively ended, matching how the underlying transaction data was generated). Features: `tenure_months_at_snapshot`, `days_since_last_transaction_at_snapshot`, `support_case_count_trailing_90d`, `avg_case_priority_trailing_90d` (numeric-encoded), `contract_type`, `customer_tier`, `transaction_amount_trailing_90d_inr`, `transaction_amount_trend_90d_inr` (90-day-over-90-day change) — all computed using only transactions/cases dated ≤ `observation_snapshot_date`.

**Target-generation logic:** see above; `horizon_days` = 75 (30-day lead + 45-day grace) is recorded per row for transparency.

**Data dictionary:**
| Column | Type | Description |
|---|---|---|
| ml_record_id | string PK | |
| customer_id, company_id | string | traceability |
| observation_snapshot_date | date | feature cutoff |
| renewal_due_date | date | the cycle boundary being evaluated |
| tenure_months_at_snapshot | float | |
| days_since_last_transaction_at_snapshot | int | |
| support_case_count_trailing_90d, avg_case_priority_trailing_90d | int / float | |
| contract_type, customer_tier | categorical | |
| transaction_amount_trailing_90d_inr, transaction_amount_trend_90d_inr | float | |
| label_churned_within_horizon | bool | **target** |
| horizon_days | int | 75, constant |
| dataset_split | enum | |

**Leakage risks (audited):**
- `customer_status` (the customer's **current, final** status) is **deliberately excluded** — there is no historical status-as-of-date table, so using the final status as a feature on an early snapshot would leak the eventual outcome. Verified: the column does not exist in this file.
- `churn_type`/`reason_category` — not applicable (no such source table exists), so no risk here, but noted for when `customer_churn_events` is eventually added: those fields should never become features (they're post-hoc explanations, not leading indicators).
- Re-derived `transaction_amount_trailing_90d_inr` independently from `customer_transactions.csv` for every row and confirmed exact match (0 mismatches) — confirms no post-snapshot transaction leaked into the trailing window.

**Example modeling plan:** With only 32 rows this is far too small to train reliably — treat it as a **pipeline validation set**, not a production model input, until the underlying customer base scales up (the design doc's full-scale target is ~6,500–8,500 customers, which would yield a proportionally larger checkpoint count). At scale: gradient-boosted trees with recall-weighted evaluation (missing a real churn is costlier than a false alarm for a CS team), SHAP-based feature attribution to turn predictions into actionable talking points for renewal calls.

---

## Cross-dataset notes

- **Reproducibility:** `generate_ml_datasets.py` is deterministic (fixed seed 20260915) and reads only the CSV files in this delivery — no hidden state.
- **Scale honesty:** every dataset's row count is a direct, proportional consequence of the underlying CRM data (1,083 leads → 1,083 rows in the two lead-level datasets; 46 customers → 211 segmentation snapshots and 32 churn checkpoints). Nothing was padded or resampled to hit a target size.
- **Full validation results** (ID traceability, duplicate-PK checks, label-vs-source-table consistency, the leakage audit, chronological split ordering, null checks, and distributions) are in `phase4_ml_validation_report.json` — every check returned 0 violations.
