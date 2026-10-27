# Business Rules

These rules are enforced by the generation logic and re-checked by `scripts/validation/validate_dataset.py` on every run. All currently pass with zero violations against the delivered CSVs.

## 1. Funnel-gating rules (the core business logic)

1.1. A `leads` row may only produce an `opportunities` row if it ever reached `lead_status = "Sales Qualified (SQL)"`.
1.2. A `customers` row may only be created from an `opportunities` row whose `pipeline_stage = "Closed Won"`.
1.3. A `customers.company_id` must equal `opportunities.company_id` for its `originating_opportunity_id`.
1.4. `customer_transactions` and `customer_support_cases` may only exist for a `customer_id` that already exists in `customers` — a customer must be created before it can transact or raise a case.
1.5. A `customer_transactions` row's `transaction_date` may never precede its customer's `customer_since` date.
1.6. An `activities` row references exactly the entities its context actually involves: a lead-context activity carries `lead_id`/`company_id`/`contact_id`; an opportunity-context activity carries `opportunity_id`/`company_id`/`contact_id` (and optionally its `source_lead_id`); a customer-context activity carries `customer_id`/`company_id` (and usually `opportunity_id`, `contact_id`). A small share of activities (general internal tasks) legitimately carry none of the five — see rule 3.7.

## 2. Status / stage machine rules

2.1. `lead_status` follows a directed progression: New → Contacted → Qualifying → Qualified (MQL) → Sales Qualified (SQL) → {Converted | Disqualified}, with Dead/Nurture reachable as stall states from any pre-SQL stage. Converted and Disqualified are terminal — no further transitions follow them in `lead_status_history`.
2.2. `pipeline_stage` follows Qualification → Discovery → Solution Fit → Proposal → Negotiation → {Closed Won | Closed Lost}. Closed Won/Closed Lost are terminal.
2.3. Every row in `lead_status_history` / `opportunity_stage_history` must chain continuously: a row's `status_from`/`stage_from` must equal the immediately preceding row's `status_to`/`stage_to` for the same lead/opportunity, ordered by `changed_at`.
2.4. `probability_pct` is fully determined by `pipeline_stage`: exactly 100 at Closed Won, exactly 0 at Closed Lost, and within a fixed band for each open stage (Qualification 10–20%, Discovery 20–35%, Solution Fit 35–50%, Proposal 50–70%, Negotiation 70–85%).

## 3. Conditional-required-field rules

3.1. `leads.converted_at` is required (non-blank) if and only if `lead_status = "Converted"`.
3.2. `leads.disqualification_reason` is required if and only if `lead_status = "Disqualified"`.
3.3. `opportunities.actual_close_date` and `close_outcome` are required if and only if `pipeline_stage` ∈ {Closed Won, Closed Lost}.
3.4. `opportunities.loss_reason` is required if and only if `close_outcome = "Lost"`.
3.5. `sales_reps.termination_date` is populated if and only if `is_active = False`.
3.6. `customer_support_cases.resolved_at` is populated if and only if `status` ∈ {Resolved, Closed}.
3.7. `activities.outcome` is required if and only if `status = "Completed"`. `activities.lead_id`/`contact_id`/`company_id`/`opportunity_id`/`customer_id` may all be blank at once (a general internal task with no entity link) — that is valid by design, not a missing-value defect.

## 4. Date-logic rules

4.1. Within a lead's lifecycle, `created_at ≤ first_contacted_at ≤ qualified_at ≤ converted_at` (each only enforced when both sides are non-blank).
4.2. An opportunity's `created_at` must precede its `actual_close_date` and `expected_close_date`.
4.3. A customer's `customer_since` must be on or after its originating opportunity's `actual_close_date`.
4.4. A support case's `resolved_at` must be on or after its `opened_at`.
4.5. No operational date in the dataset may fall after the generation cutoff (`2026-09-15`), **except** three explicitly forward-looking fields, each with its own documented policy (also enforced by `scripts/validation/validate_dataset.py`'s `DATE_COLUMN_POLICY` and section `9b_future_date_policy_violations`):
   - `opportunities.expected_close_date` — a forecast field; may be ahead of the cutoff on an open deal (it's the target close date), and may *remain* ahead of the cutoff even on an already-closed deal, since that just reflects the deal closing earlier than originally forecast (forecast-vs-actual variance, not an error). The only real constraint is `created_at ≤ expected_close_date` (rule 4.2).
   - `customers.renewal_date` — the next scheduled renewal checkpoint. May be in the future (upcoming renewal) or in the past (a missed renewal) for any non-"Active" customer. **It may never be in the past while `customer_status = "Active"`** — see rule 4.6.
   - `campaigns.end_date` — may be ahead of the cutoff for a still-running campaign. The only real constraint is `end_date ≥ start_date` (rule 4.1-equivalent, checked separately).

4.6. `customers.renewal_date` must never precede `customer_since` (rule 4.5 variant, checked independently), and — this is the one genuine cross-field business rule among the three above — a customer whose `renewal_date` has already passed (i.e. they missed their scheduled renewal, with no covering transaction) must **not** be `customer_status = "Active"`. When the generator detects this at creation time it downgrades the status: overdue by fewer than 90 days → `"At Risk"`; overdue by 90 days or more → `"Paused"`. This rule was added after a real defect (12 customers) was found and fixed — see `data_quality_report.md` §1.4.

4.7. `activities.activity_date` follows the same never-future policy as any other "this either happened or hasn't" field — it is always on or before the generation cutoff, and always on or before its own `created_at`/`updated_at` (an activity is logged on or after the date it covers, never before). `activities.due_date` and `activities.next_follow_up_date`, by contrast, are schedule/deadline fields — like `campaigns.end_date` and `customers.renewal_date` above — and may legitimately fall after the generation cutoff for an open (Planned/Pending/In Progress/Rescheduled) activity; both are `"always_allowed"` in `DATE_COLUMN_POLICY`. The two real cross-field constraints, checked in `9b`/`26_activities_validation` rather than left as raw future-date counts, are: `due_date` on/after `activity_date`'s calendar date (rule 7 of the activities spec), and `next_follow_up_date`, when present, strictly after `activity_date`'s calendar date (rule 8).

4.8. `customer_transactions.amount_inr` is negative **if and only if** `transaction_type = "Refund"` — a refund/reversal of a prior sale is the only transaction type where a negative amount is meaningful; every other `transaction_type` (`New Sale`, `Renewal`, `Upsell`, `Downgrade`) is always non-negative. This dataset ships 2 `Refund` rows (both negative), found during a review of `customer_transactions.csv`'s negative values and confirmed valid rather than a data error — see `data_quality_report.md` §1.8. Checked by `full_audit.py`/`validate_dataset.py` section `15_revenue_inconsistencies` (`customer_transactions_refund_type_not_negative_amount`, `customer_transactions_negative_amount_not_refund_type`) — both must be 0.

4.9. `companies.sub_industry` is populated from a fixed vocabulary of 3–5 sub-industries specific to that row's `industry_id` (e.g. Pharmaceuticals & Healthcare → "Pharmaceutical Manufacturing" / "Hospitals & Clinics" / "Diagnostics & Labs" / "Medical Devices" / "Health-Tech") for ~95% of companies, and left blank for the remaining ~5% — matching the sparsity a real CRM's sub-industry classification typically shows (some records just never got tagged). It is never populated from a different industry's vocabulary. See `data_quality_report.md` §1.9 for the fix (this column was previously hardcoded blank for 100% of rows, which was itself the defect).

## 5. Revenue / arithmetic rules

5.1. `opportunity_products.line_total_inr = quantity × unit_price_inr × (1 − discount_pct/100)`, exactly (within floating-point rounding).
5.2. `opportunities.deal_value_inr` = the sum of `line_total_inr` across all of that opportunity's `opportunity_products` rows, exactly.

## 6. Referential-integrity rules

6.1. Every non-blank foreign key must resolve to an existing row in its parent table (40 declared FK relationships across the schema, including `activities`' 6 — see `er_documentation.md`).
6.2. Cross-entity consistency: a lead's `contact_id` must belong to the same `company_id` as the lead itself; an opportunity's `primary_contact_id` must belong to the same company as the opportunity; a support case's `contact_id` must belong to the same company as the case's customer.

## 7. Uniqueness rules

7.1. Primary keys are unique within every table.
7.2. `companies` are unique by (`company_name`, `city`) and by `website_domain`/`gstin` where populated.
7.3. `contacts.email` and `sales_reps.email` are unique where populated.
7.4. A `companies` row produces at most one `customers` row.
7.5. No two `activities` rows describe the same business event: no two rows may share `activity_type` + `company_id` + `contact_id` + `opportunity_id` + `activity_date` + `subject` simultaneously (checked by `26_activities_validation.likely_duplicate_business_events`). Sharing only some of these — the same `activity_type`, or the same `subject` text, on its own — is normal and explicitly not a violation of this rule (see rule 8 note below and `data_quality_report.md` §1.6).

## 8. Categorical-value rules

All enum-like columns (`lead_status`, `pipeline_stage`, `company_size_band`, `account_status`, `company_type`, `customer_status`, `customer_tier`, `contract_type`, `transaction_type`, `payment_status`, `case_type`, `priority`, `status`, `activities.activity_type`, `activities.status`, `activities.priority`) are restricted to a fixed, documented value set — see `data_dictionary.md` for each column's allowed values. No free-text categorical drift is permitted.

## 9. ML-specific rules

See `ml_leakage_prevention.md` for the full list; summarized:

9.1. No ML feature may be computed from source-table data timestamped after that row's observation cutoff.
9.2. `lead_scoring_dataset`'s cutoff must equal `leads.created_at` exactly (strict day-0; no engagement/budget features permitted).
9.3. `churn_prediction_dataset` must never include `customers.customer_status` as a feature.
9.4. `customer_segmentation_dataset` must carry **no** cluster/segment-label column at all — cluster assignment is a downstream modeling output, never a shipped input. (An earlier revision shipped `segment_label_cluster_id` as an always-blank placeholder; it has since been removed from the schema entirely — see `data_quality_report.md` §1.9.)
9.5. `dataset_split` must be assigned chronologically per dataset, never randomly, and no `train` row's cutoff/period may fall after any `test` row's cutoff/period.
