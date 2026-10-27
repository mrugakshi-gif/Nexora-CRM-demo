# ML Leakage-Prevention Document

This document is the reference to check *before* adding any new feature to one of the 5 ML-ready datasets, or before joining additional source-table columns into them. It states what was already checked and enforced, and how to keep it that way.

## The core principle

Every row in every ML dataset has an explicit **observation point** — a timestamp (or, for `sales_forecasting_dataset`, a period start) beyond which no information may be used to compute that row's features. The label is the only thing allowed to reflect what happened *after* that point (that is, after all, the entire point of a predictive label). Any feature computed from source-table data timestamped after the observation point is leakage, full stop — even if the feature "feels" like something you'd naturally know (e.g. "how many status transitions has this lead had" is fine as long as it only counts transitions before cutoff).

## Per-dataset observation point and cutoff rule

| Dataset | Observation-point column | Cutoff rule |
|---|---|---|
| lead_conversion_dataset | `observation_cutoff_at` | `qualified_at` → `first_contacted_at` → `created_at`, whichever is the latest non-blank value in that fallback chain — i.e. the latest milestone the lead had actually reached, never a milestone from later in its life |
| lead_scoring_dataset | `observation_cutoff_at` | forced to equal `leads.created_at` exactly — day-0 only |
| sales_forecasting_dataset | `period_start` | all features computed from opportunities/transactions dated strictly before `period_start`; the label is realized revenue **within** the period, which is legitimately the future relative to the feature snapshot (that's what makes it a forecast) |
| customer_segmentation_dataset | `snapshot_date` | all RFM/engagement features computed from transactions/cases dated on or before `snapshot_date` |
| churn_prediction_dataset | `observation_snapshot_date` | fixed at 30 days before each renewal `renewal_due_date`; all features computed from data on or before the snapshot date; the label looks at the `[due−15, due+45]` window, which is after the snapshot by construction |

## Checks performed (all currently pass — see `validation_report.md`)

1. **Cutoff-after-outcome check** (`lead_conversion_dataset`): no row's `observation_cutoff_at` falls after that lead's `converted_at`, if converted. If it did, the model would effectively be told the outcome before being asked to predict it.
2. **Day-0 enforcement** (`lead_scoring_dataset`): `observation_cutoff_at` must equal `created_at` exactly for every row; and the dataset must not contain any of the forbidden post-day-0 columns (`num_status_transitions_before_cutoff`, `estimated_budget_inr`, `rep_trailing_conversion_rate`, `qualified_at`, `converted_at`).
3. **Pipeline-value recompute check** (`sales_forecasting_dataset`): `pipeline_value_open_at_period_start_inr` is independently recomputed from `opportunities` (sum of deal value for opportunities created before `period_start` and not yet closed by `period_start`) and compared to the stored value — must match.
4. **Negative-recency / no-cluster-column check** (`customer_segmentation_dataset`): recency must never be negative (would indicate a future transaction was used), and the table must carry **no** cluster/segment-label column at all — an earlier revision shipped `segment_label_cluster_id` as an always-blank placeholder, which was removed entirely (not just left blank) rather than risk it ever being populated upstream and leaking a pre-computed label into what must stay an unsupervised feature table. See rule 9.4 below and `data_quality_report.md` §1.9.
5. **Trailing-90d recompute check** (`churn_prediction_dataset`): `transaction_amount_trailing_90d_inr` is independently recomputed from `customer_transactions` (sum in the 90 days before the snapshot) and compared — must match.
6. **customer_status exclusion check** (`churn_prediction_dataset`): the column must not appear at all — including `customer_status` as a feature would hand the model a value that is itself derived from (and highly correlated with) the thing it's trying to predict.
7. **Chronological-split check** (all 4 time-ordered datasets): the maximum observation timestamp/period among `train` rows must be ≤ the minimum among `test` rows — i.e. the split is a genuine time-based holdout, never a random shuffle that could leak future information into training via adjacent rows.
8. **Target-derived-feature check**: no feature column is a direct or near-direct function of the label (e.g. `lead_conversion_dataset` does not include anything like "opportunity_created_flag," which would be nearly synonymous with eventual conversion).

## Rules for anyone extending these datasets

- **Never** join a source-table column into an ML row without first checking that column's date-generating event against that row's observation point. If the column doesn't have an obvious associated date, assume it's unsafe until proven otherwise.
- **Never** add a feature computed from a source table's *current/latest* value (e.g. `leads.lead_status` as of the CSV snapshot) — always recompute "as of observation point" from the history tables (`lead_status_history`, `opportunity_stage_history`) or from `customer_transactions`/`customer_support_cases` filtered by date, the way the existing trailing/rolling features do.
- **Never** add the target's own source column as a feature (e.g. don't add `leads.lead_status` to `lead_conversion_dataset` — that's the label in another form).
- **Always** re-run `scripts/validation/validate_dataset.py` after adding a feature; its leakage-audit section is written generically enough to catch a recompute mismatch on any of the "trailing" or "as of cutoff" style features, not just the ones shipped today.
- **Always** keep `dataset_split` assignment chronological. A random split on time-series-flavored CRM data (leads/opportunities/renewals) is a classic, easy-to-miss leakage vector: adjacent-in-time rows share a lot of unobserved context (the same campaign wave, the same rep's current pipeline, the same macro conditions), so a random split lets the model implicitly learn from "the future" via its near-neighbors even without an explicit leaked column.

## Class balance note (category 22)

None of the 5 labels are degenerate: lead_conversion 18.3% positive, lead_scoring 18.3% positive, churn 25.4% positive, forecasting label is a continuous revenue amount (not binary), segmentation has no label (unsupervised). If you resample or reweight for training, do it only on the `train` split — never let a resampling step see `validation`/`test` rows, and never resample before checking that doing so doesn't reintroduce a leakage path (e.g. duplicating a `train` row that happens to share exact feature values with a `test` row from a scale-up run).
