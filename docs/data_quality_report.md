# Indian B2B CRM Dataset — End-to-End Audit Report

**Audit date:** 2026-09-15
**Seed:** `20260915` (all generators, fixed and reproducible)
**Scope:** all 19 source tables (master + transactional + historical) and all 5 ML-ready datasets — 24 tables, 25 validation categories, every declared relationship and business rule.

This audit re-validated the entire pipeline end-to-end, found **4 real defects across two audit passes** (3 in the original 25-category audit; a 4th found later during a targeted review of future-dated fields — see §1.4), corrected each one **at its generator source** (not by hand-patching CSVs), regenerated the full pipeline from master tables through the ML datasets with the same fixed seed, and re-ran every check until clean. The three phase-specific validators (`audit.py`, `validate_phase2.py`, `validate_phase3.py`) and the ML validator (`validate_ml_datasets.py`) all still report zero violations after the fix, and the cross-cutting `validate_dataset.py`/`full_audit.py` (25 categories + the `9b_future_date_policy_violations` cross-field checks, all tables) also reports zero unresolved defects.

---

## 1. Defects found and corrected

### 1.1 Lead-status history chronology broken for 188 / 201 converted leads (93.5%)

**Table:** `lead_status_history` (and `leads.converted_at`)
**Category:** #10 impossible date sequences, #11/#12 status-transition integrity

**What was wrong:** `leads.qualified_at` records when a lead reached **Qualified (MQL)** — an earlier milestone than **Sales Qualified (SQL)**. The opportunity-generation step (`generate_opps_customers.py`) anchored a new opportunity's `created_at` (and therefore the lead's `converted_at`) to `qualified_at + random(1–10 days)`. But the lead's actual SQL-transition event, simulated independently in Phase 2's funnel walk, could land far more than 10 days after `qualified_at` (its own dwell time was unbounded by that window). Result: for leads where the real SQL dwell exceeded ~10 days, the backfilled "Sales Qualified (SQL) → Converted" history row got a timestamp **earlier** than the pre-existing "Qualified (MQL) → Sales Qualified (SQL)" row already in the table — e.g. lead `LEAD-000002` showed `Converted` at 2025-08-02 13:53 followed by `Qualified (MQL) → Sales Qualified (SQL)` at 2025-08-12 12:26, ten days later. That's a lead converting before it became sales-qualified.

**Affected records:** 188 of the 201 originally-converted leads (found via chain-continuity check: each history row's `status_from` must equal the immediately preceding row's `status_to`, sorted by `changed_at`).

**Fix (at source, `generate_opps_customers.py`):** built a `SQL_REACHED_AT` lookup from each lead's actual `Sales Qualified (SQL)` transition row in `lead_status_history`, and anchor the opportunity's `created_dt` (and hence `converted_at`) to that real SQL-transition timestamp, falling back to `qualified_at` only if no SQL row exists (shouldn't happen for SQL-sourced leads, kept as a defensive fallback).

**Re-validation:** `lead_status_history_invalid_transitions` = 0 (was 564 raw sub-checks / 188 leads).

### 1.2 Apostrophe surnames produced unrealistic email/LinkedIn handles

**Tables:** `contacts`, `sales_reps` (email-generation logic; only manifested in `contacts` this run, since no sales rep happened to be sampled with the affected surname)
**Category:** #25 inconsistent naming/formatting, #19 realism

**What was wrong:** The Goan Christian surname `D'Souza` (a legitimate entry in the surname pool) was lower-cased directly into the email local-part (`vikas.d'souza60@...`) and LinkedIn slug. Real corporate email systems and LinkedIn URLs strip apostrophes and punctuation from generated handles — an email containing a raw `'` character is both unrealistic and, per RFC 5321, discouraged/rejected by many mail systems' local-part validators.

**Affected records:** 18 contact emails/LinkedIn handles.

**Fix (at source, `generate_master_tables.py` and `generate_contacts_leads.py`):** email and LinkedIn local-parts are now built from an alphanumeric-only lowercased version of each name component (`"".join(ch for ch in name.lower() if ch.isalnum())`), applied identically to both the contacts and sales-reps generators so the same latent defect can't resurface if a future reseed happens to draw `D'Souza` into the sales-rep pool.

**Re-validation:** `contacts.invalid_email_format` = 0; apostrophe-containing emails = 0 across all tables.

### 1.3 One transaction dated after `TODAY`

**Table:** `customer_transactions`
**Category:** #9 invalid (future) dates

**What was wrong:** `customer_since` is explicitly clamped to `min(close_date + lag, TODAY)`, but the first transaction's date (`customer_since + random(0–5 days)`) was not re-clamped — so a customer whose `since` date already equaled `TODAY` could get an invoice dated up to 5 days into the future (`TXN-0000087`, dated 2026-09-19, 4 days past the 2026-09-15 cutoff).

**Affected records:** 1 transaction.

**Fix (at source, `generate_opps_customers.py`):** `first_txn_date = min(since + timedelta(days=random.randint(0,5)), TODAY)`.

**Re-validation:** `customer_transactions.transaction_date.future_dated` = 0.

### 1.4 12 customers marked `"Active"` despite an already-overdue `renewal_date`

**Table:** `customers`
**Category:** #9b future-date policy violations (new), #13 invalid customer derivations (cross-field consistency)

**How this surfaced:** a later validation pass (triggered by a user report that `validate_dataset.py` printed non-zero future-dated counts for `opportunities.expected_close_date`, `customers.renewal_date`, and `campaigns.end_date` alongside a blanket "all categories clean" summary) required auditing every future/past-dated value in those three columns individually rather than treating raw future-date counts as informational by default. Two of the three columns (`expected_close_date`, `campaigns.end_date`) turned out to be legitimately forward-looking by design — see rule 4.5 in `business_rules.md`. The third, `customers.renewal_date`, surfaced a real defect once cross-checked against `customer_status`.

**What was wrong:** `customer_status` is drawn once, independently, at customer-creation time from a weighted distribution keyed on the customer's `engagement` tier (High/Medium/Low) — before the generator has simulated whether that customer actually keeps renewing on schedule. `renewal_date` is computed separately, later in the same function, from the customer's actual simulated transaction/renewal history. Nothing reconciled the two: a customer could be assigned `customer_status = "Active"` by the independent draw, while the renewal simulation *separately* determined their most recent scheduled renewal had already passed with no transaction covering it (i.e. a missed renewal) — a customer who has already lapsed but is still labeled "Active."

**Affected records:** 12 of 48 customers — `CUST-000001` (142 days overdue), `CUST-000006` (273), `CUST-000008` (386), `CUST-000010` (364), `CUST-000012` (470), `CUST-000013` (220), `CUST-000016` (169), `CUST-000018` (125), `CUST-000019` (354), `CUST-000022` (66), `CUST-000023` (298), `CUST-000044` (46) — overdue by 46 to 470 days at the 2026-09-15 cutoff.

**Fix (at source, `generate_opps_customers.py`):** immediately after `renewal_date` is computed, if `customer_status == "Active"` and the computed `renewal_dt < TODAY`, the status is deterministically downgraded using only that already-computed date (never a fresh random draw, so the RNG stream and every downstream row count are undisturbed): overdue **< 90 days → `"At Risk"`**; overdue **≥ 90 days → `"Paused"`**. Applying this rule to the 12 affected records: `CUST-000022` (66d) and `CUST-000044` (46d) became `"At Risk"`; the other 10 (125–470d) became `"Paused"`.

**Re-validation:** `9b_future_date_policy_violations.customers.renewal_date_overdue_while_status_active.violations` = 0. `customer_status` mix shifted from the pre-fix distribution to **Active 27, Paused 12, At Risk 9** (48 total, unchanged) — see updated §5 and `MANIFEST.md` §2.

This is also the occasion for two related fixes to the validator itself (not the data): `full_audit.py`/`validate_dataset.py` previously reported a raw future-dated count for these 3 columns without distinguishing it from a genuine violation count, so a non-zero future-dated number could appear next to an "all clean" summary with no explanation — this looked contradictory even when every printed number was individually correct. The validator now gives each date column an explicit, documented `DATE_COLUMN_POLICY` (`"never"` / `"conditional"` / `"always_allowed"`), reports `future_dated` (informational) and `violations` (policy-aware) as two separate numbers per column, adds section `9b_future_date_policy_violations` with the four concrete cross-field checks this defect required, and prints an itemized summary of every future-dated column's policy and violation count immediately before any PASS/FAIL verdict — so the summary can never again assert "clean" without accounting for every non-zero number in the JSON. A separate, unrelated `pandas` `UserWarning` (a regex capturing group in the placeholder-text check, `(test|dummy|...)`, which pandas flags when used with `.str.contains()`) was also fixed by converting it to a non-capturing group `(?:test|dummy|...)`.

### 1.5 `activities` addition: a validator comparison-precision bug (caught before delivery, not a data defect)

**Table:** `activities` (new table)
**Category:** #26 activities validation (new)

**What happened:** When `activities.csv` was added to the dataset and integrated into `validate_dataset.py`, the first run of the new `due_date_before_activity_date` check reported 440 "violations" out of 2,348 rows. Investigating before accepting that number (rather than either shipping it or silently suppressing it) showed the generated data was correct — the validator's comparison logic was not: `due_date` is a pure `DATE` value (no time-of-day) while `activity_date` is a full timestamp, so a `due_date` on the *same calendar day* as `activity_date` parses at implicit midnight (`00:00:00`) and compares as "earlier than" an `activity_date` logged later that same day (e.g. at `14:20:00`) — a false positive from comparing a date-only field to a timestamp field at full precision, not a real ordering defect.

**Fix (in the validator, `full_audit.py`/`validate_dataset.py`, not the generator or the data):** the `due_date_before_activity_date` and `next_follow_up_date_not_after_activity_date` checks now compare calendar dates (`.date()`) on both sides, matching the actual granularity of `due_date`/`next_follow_up_date` (both are `DATE` columns per the data dictionary) instead of comparing a date-only value against a full timestamp.

**Re-validation:** `26_activities_validation.due_date_before_activity_date.violations` = 0 (was 440 before the comparison fix); all other `activities` checks (`next_follow_up_date_not_after_activity_date`, `activity_date_after_created_or_updated_at`, `completed_without_outcome`) were 0 from the first run. No `activities.csv` rows were altered by this fix — it corrected how the validator read the data, not the data itself.

### 1.6 `activities` v2: excessive text repetition (template collapse), not a duplicate-records defect

**Table:** `activities`
**Category:** #26 activities validation — new `likely_duplicate_business_events` and `repeated_content_warnings` checks

**What was wrong:** a user review of the delivered `activities.csv` (v1, 2,348 rows) confirmed there were no exact duplicate rows and no duplicate `activity_id` values, and — checking the strict business-event key (`activity_type` + `company_id` + `contact_id` + `opportunity_id` + `activity_date` + `subject`) — no two rows actually described the same event either. The dataset still "looked artificially generated" because v1 built `subject`/`description`/`outcome` text from a small, mostly context-free template pool: `Email` and `Task` subjects in particular never included the company or contact name, so all 2,348 rows drew from only 20 topic phrases for those fields — e.g. `"Email - contract terms review"` appeared 31 times, `"Email - pricing and licensing terms"` 29 times, purely because the subject template ignored which company/contact the email was actually about. `outcome` text for `Completed` activities was drawn from fixed 4–7-item lists per activity type, so only 48 distinct outcome strings covered 1,296 completed rows.

**This is a text-variety problem, not a record-duplication problem** — no record was a duplicate of another by the business-event definition, so nothing qualified for removal under requirement 3/4 ("remove only records that represent the same business event," "do not remove records merely because they share the same activity type or subject").

**Fix (at source, `generate_activities.py`, rewritten as v2 — no rows deleted):**
- every `subject` now always includes the company name (previously only Call/Meeting/Follow-up/Negotiation did), and includes the contact's name too for a randomized ~55% of contact-bearing rows, so two unrelated activities essentially never produce identical subject text;
- the topic vocabulary was widened from 20 to 51 phrases;
- `outcome` for `Completed` activities is now composed from an opening clause × a topic reference × one of 25 concrete next-step clauses (e.g. "will send a revised proposal by end of week," "escalated pricing approval to the regional sales head"), giving thousands of possible combinations per activity type instead of a fixed short list;
- `description` is now drawn from 2–3 phrasing variants per activity type instead of one fixed template, and references the specific contact by name where one is set;
- an explicit post-generation **business-event dedup pass** was added (grouping by the same six-column key above): any row that *would* collide with an earlier one on all six fields is repaired in place — its date is nudged and its subject/description/outcome are re-rolled against its same real entity linkage — rather than deleted, so a true duplicate can never survive but no valid record is ever dropped to fix it. On this dataset the pass found 0 collisions to repair (the widened vocabulary alone was sufficient), so all 2,359 rows are original generations, not repairs.

**Result:** regenerating end-to-end (a fresh run reseeded for v2, so the exact row count shifted slightly with the new context-pool draw) produced 2,359 rows with 2,310 unique subjects (97.9%, vs. 1,577/2,348 = 67.2% in v1), 2,351 unique descriptions (99.7%, vs. 2,301/2,348 = 98.0% in v1), and 1,246 unique outcomes among 1,280 Completed rows (97.3%, vs. only 48 distinct outcome strings covering all 1,296 Completed rows in v1 — under 4% unique). Maximum single-subject repeat share dropped from 1.32% (31 identical occurrences of `"Email - contract terms review"`) to 0.17% (4 occurrences, the new maximum for any subject); maximum single-description repeat share dropped from 0.13% to 0.08%. `validate_dataset.py`'s new `26_activities_validation.repeated_content_warnings` block (informational; flags any text repeated more than 5 times or over 0.5% of rows) reports **0 flagged values** for both `subject` and `description` in the delivered v2 file, and `likely_duplicate_business_events.violations` = 0.

---

### 1.7 `customer_segmentation_dataset.avg_satisfaction_score`: window-mismatch bug against its neighboring count column

**Table:** `customer_segmentation_dataset` (ML-ready dataset, generated by `generate_ml_datasets.py`)
**Category:** #27b ML missing-value investigation — `customer_segmentation_dataset.avg_satisfaction_score`

**What was wrong:** a follow-up review asked for an explicit investigation of every missing-value pattern in the three multi-snapshot ML datasets (`churn_prediction_dataset`, `customer_segmentation_dataset`, `sales_forecasting_dataset`), classifying each as logically valid, requiring imputation, requiring correction, or an intentional null — rather than assuming any null pattern is fine by inspection alone. Cross-checking `avg_satisfaction_score` against its neighboring column `support_case_count_last_12mo` (a `pd.crosstab` of "count == 0" against "score is null") surfaced 10 of 244 rows where `support_case_count_last_12mo` was 0 but `avg_satisfaction_score` was still populated — a logical impossibility, since there is nothing to average when zero support cases fall in the trailing 12-month window. Root cause: the generator computed `avg_satisfaction_score` from `cases_to_date` (every case the customer had ever opened, unbounded), while the neighboring `support_case_count_last_12mo` was correctly scoped to `cases_12mo` (a trailing-12-month window) — two columns sitting side by side in the same row, silently built from two different time windows.

**Fix (at source, `generate_ml_datasets.py`):** the `resolved_scores` list comprehension that feeds `avg_satisfaction_score` was changed to draw from `cases_12mo` (the same trailing-12-month window as `support_case_count_last_12mo`) instead of `cases_to_date`, so the two columns are now always consistent with each other.

**Result:** regenerating `generate_ml_datasets.py` (deterministic — confirmed no randomness beyond the single `random.seed(20260915)` call at the top of the script, so this table can be safely regenerated in isolation from the other 4 ML tables) produced identical row counts (244 rows across 48 customers) with the anomaly count now 0/244 (re-checked via the same crosstab). `avg_satisfaction_score`'s null count rose slightly, from 89/244 to 112/244 — expected, since rows that previously carried a stale all-time score now correctly show null when the trailing-12mo window has no cases. This is now a permanent, machine-checked invariant: `full_audit_report.json` → `27b_ml_missing_value_investigation` → `customer_segmentation_dataset.avg_satisfaction_score.invariant_violations` must be 0 on every future run, and `validate_dataset.py`'s BUCKET 6/8 (unacceptable null values) fails the run if it ever isn't.

---

### 1.8 `customer_transactions.amount_inr`: 2 negative values investigated — valid refunds, now an explicit checked invariant

**Table:** `customer_transactions`
**Category:** #15 revenue inconsistencies — new `customer_transactions_refund_type_not_negative_amount` / `customer_transactions_negative_amount_not_refund_type` checks

**What was investigated:** a review flagged 2 rows in `customer_transactions.csv` with a negative `amount_inr` (`TXN-0000040`: -₹157.28; `TXN-0000111`: -₹4,760.14) and asked whether this represents a valid refund/reversal or a data error requiring correction.

**Finding:** both rows already carry `transaction_type = "Refund"` (one of the five documented `transaction_type` values alongside `New Sale`, `Renewal`, `Upsell`, `Downgrade` — this value was already part of the schema, not newly added). Checking the full table confirms the pattern is exact and total: **every** `Refund` row is negative, and **no** non-`Refund` row is ever negative (`(df[df.transaction_type=='Refund'].amount_inr < 0).all()` → `True`; `(df[df.transaction_type!='Refund'].amount_inr < 0).any()` → `False`). This is a valid, intentional business pattern — a refund reduces the customer's net billed amount — not a data-entry error, and no correction was needed.

**Action taken:** the invariant was not previously an explicit, checked rule anywhere (it happened to hold, but nothing would have caught a regression). Two new checks were added to `full_audit.py`/`validate_dataset.py` section `15_revenue_inconsistencies` — `customer_transactions_refund_type_not_negative_amount` (a `Refund` row that isn't negative) and `customer_transactions_negative_amount_not_refund_type` (a negative amount on any other transaction type) — both must be 0, and both are wired into BUCKET 8/8 (errors) of the final summary. The business rule is now documented explicitly in `business_rules.md` rule 4.8 and `data_dictionary.md`.

---

### 1.9 `customer_segmentation_dataset.segment_label_cluster_id`: removed — was a misleading always-blank placeholder

**Table:** `customer_segmentation_dataset` (ML-ready dataset)
**Category:** #21 ML target leakage — `segmentation.cluster_id_column_present`

**What was wrong:** `segment_label_cluster_id` was 100% blank in every row of every prior delivery. It was originally documented as an intentional output-only placeholder (reserved for a downstream clustering model's result), which is a legitimate design for an unsupervised dataset — but a column that is *always* empty, with no other row ever populating it, is indistinguishable in practice from a column that simply failed to generate, and a reviewer has no way to tell those two situations apart just by looking at the CSV. The user's review correctly flagged this as a misleading empty label column that needed either real values or removal, and asked for a deliberate decision one way or the other rather than leaving the ambiguity in place.

**Decision:** `customer_segmentation_dataset` is genuinely built for **unsupervised** clustering (RFM + firmographic + support-engagement features, no target column, no train/val/test split — see `ml_dataset_documentation.md` §4). There is no ground-truth cluster assignment to ship for an unsupervised task — generating fake cluster IDs would be actively wrong (it would imply a supervised label exists when none does, and risks being mistaken for real target leakage by anyone who later feeds this table into a leakage-scanning pipeline). The correct fix is removal, not backfilling: the column has been dropped from the schema entirely.

**Fix (at source, `generate_ml_datasets.py`):** the `"segment_label_cluster_id": ""` key was removed from the row-construction dict, and `segment_label_cluster_id` was removed from `SG_FIELDS` (the CSV's written column list). The SQL schemas (`create_tables_postgres.sql`, `create_tables_mysql.sql`) had the column dropped to match. `full_audit.py`'s ML-leakage check was changed from asserting "must be blank" (`segmentation.cluster_id_prepopulated == 0`) to asserting "must not exist" (`segmentation.cluster_id_column_present == False`) — a stronger, more explicit guarantee that also makes any future accidental reintroduction of a cluster-label column fail loudly rather than silently pass because it happened to still be blank.

**Result:** regenerating `generate_ml_datasets.py` produced identical row counts (244 rows across 48 customers) for `customer_segmentation_dataset`, and confirmed byte-identical output for all 4 other ML datasets (`lead_conversion_dataset`, `lead_scoring_dataset`, `sales_forecasting_dataset`, `churn_prediction_dataset` — none of them reference this column, so none were affected). `customer_segmentation_dataset.csv` now has 15 columns instead of 16.

---

### 1.10 `companies.sub_industry`: was hardcoded blank for 100% of rows — populated with a real industry-scoped vocabulary

**Table:** `companies`
**Category:** #4b acceptable null values

**What was wrong:** `companies.sub_industry` was hardcoded to `""` in the generator (`"sub_industry": ""`, with no generation logic at all) for every one of the 1,200 companies, while the shipped `data_dictionary.md` described it as "Free-form sub-industry note, sparsely populated" — actively incorrect documentation for a column that was in fact populated in exactly 0% of rows, not "sparsely." The user's review correctly identified this as either needing real values or needing the column removed, rather than left in this inconsistent state.

**Decision:** populate it. Unlike `segment_label_cluster_id` (§1.9), `sub_industry` is a normal firmographic attribute with an obvious real-world source of values (every `industry_id` has a natural set of sub-industries), so backfilling it with realistic values — rather than removing the column — is the right fix here.

**Fix (at source, `generate_master_tables.py`):** added a fixed vocabulary of 3–5 sub-industries per `industry_id` (20 industries × their own sub-industry list, e.g. IT & Software Services → IT Services & Consulting / Software Products/SaaS / IT Infrastructure & Cloud / Cybersecurity / BPO/ITES), and a `pick_sub_industry(company_id, industry_id)` function that selects one (or, for ~6% of companies, leaves it blank — matching the sparsity that other optional company fields like `founded_year` or `website_domain` already show, since real CRM sub-industry tagging is itself often incomplete).

**A deliberate implementation detail, to protect the rest of the dataset:** this function draws from its own independent `random.Random(f"subind::{company_id}::{industry_id}")` instance rather than the shared module-level `random` stream that the rest of `generate_master_tables.py` (and every downstream generator script) consumes. Since this dataset's entire generation pipeline is one continuous, seeded random-number stream (`random.seed(20260915)` at the very top, consumed sequentially through all 5 generator scripts), inserting even a single extra call to the shared `random` module here would have shifted every subsequent random draw — email formats, GSTINs, founded years, rep assignments, and everything generated by every later script — silently changing the entire rest of the dataset as a side effect of fixing one column. Using a separate, independently-seeded local RNG avoids that entirely: it was verified by running the full generator pipeline both with and without the fix and diffing every output CSV — only `companies.csv`'s `sub_industry` column differs; all 23 other CSVs (including every downstream table that depends on `companies` — `contacts`, `leads`, `opportunities`, `customers`, `activities`, and all 5 ML datasets) are byte-for-byte identical to the pre-fix versions.

**Result:** regenerating the full pipeline (`generate_master_tables.py` → `generate_contacts_leads.py` → `generate_opps_customers.py` → `generate_activities.py` → `generate_ml_datasets.py`) produced `sub_industry` populated for 1,139/1,200 companies (94.9%), blank for the remaining 61 (5.1%), drawn only from that company's own industry's vocabulary in every case — with every other file in the delivery unchanged. `data_dictionary.md` was corrected to describe the actual populated vocabulary instead of the previous (already-inaccurate) "sparsely populated" description.

---

### 1.11 Confirmed: duplicate-primary-key checking was already correctly scoped to primary-key columns only

**Category:** #1 duplicate rows / #2 duplicate primary keys / #6b repeated foreign keys

A user-run external/basic testing pass had separately reported repeated `company_id`, `customer_id`, `opportunity_id`, `lead_id`, and `sales_rep_id` values as duplicate-record errors. This was re-verified against `full_audit.py`/`validate_dataset.py` directly (not just re-asserted): the `PK` dictionary that drives `2_duplicate_primary_keys` maps each of the 19 tables to **its own** primary-key column only (`companies → company_id`, `customers → customer_id`, `opportunities → opportunity_id`, `leads → lead_id`, `sales_reps → rep_id`) — `grep`ing the script confirms `sales_rep_id` (the *foreign*-key column name used in `activities` and elsewhere) never appears anywhere in that dictionary, and `company_id`/`customer_id`/`lead_id`/`opportunity_id` are checked only within the one table where each is genuinely a primary key, never within the several other tables where the same name is used as a foreign key. Repeated FK values are surfaced separately and explicitly, and labeled `is_this_an_error: false`, in `6b_repeated_foreign_keys_informational` (see §"The eight-bucket final summary" in `validation_report.md`). No code change was needed here; this section exists so the correction is documented with the evidence that was checked, not just asserted.

---

## 2. Full regeneration and downstream effects

All three fixes live in the generators, not in random-number-consuming code paths, so the RNG stream position was undisturbed for the master-table and lead/contact generation stages (row counts for `industries` through `campaign_responses` are byte-for-byte identical to the pre-fix run). The opportunity-anchor fix (1.1) does shift *which* leads clear the "still has runway before TODAY" filter, since some opportunities now get a later, more-accurate `created_at` — this is an intended, honest consequence of fixing the anchor date, not a new defect:

| Table | Before fix | After fix | Why it changed |
|---|---|---|---|
| `opportunities` | 201 | 198 | 3 SQL leads whose corrected (later) SQL-anchor date leaves too little runway before TODAY no longer qualify for an opportunity |
| `opportunity_products` | 410 | 388 | follows opportunity count |
| `opportunity_stage_history` | 722 | 703 | follows opportunity count |
| `customers` | 46 | 48 | shifted win/loss outcomes among the corrected opportunity set |
| `customer_transactions` | 88 | 116 | more customers, plus longer/differently-timed tenures change renewal counts |
| `customer_support_cases` | 119 | 113 | follows customer set |
| `leads` / `lead_status_history` / `contacts` / `companies` (pre-opportunity fields) | — | unchanged | fix doesn't touch these generators' RNG stream |
| all 5 ML datasets | — | regenerated | rebuilt from the corrected source tables (required — they are derived, never hand-edited) |

Full corrected pipeline was re-run in order: `generate_master_tables.py` → `generate_contacts_leads.py` → `generate_opps_customers.py` → `generate_ml_datasets.py`, then every validator was re-run against the final output.

---

## 3. Final row counts

| Table | Rows |
|---|---|
| industries | 20 |
| territories | 18 |
| departments | 7 |
| lead_sources | 12 |
| products | 20 |
| sales_reps | 80 |
| campaigns | 180 |
| companies | 1,200 |
| contacts | 925 |
| leads | 1,083 |
| lead_status_history | 4,129 |
| campaign_responses | 676 |
| opportunities | 198 |
| opportunity_products | 388 |
| opportunity_stage_history | 703 |
| customers | 48 |
| customer_transactions | 116 |
| customer_support_cases | 113 |
| activities | 2,359 |
| lead_conversion_dataset | 1,083 |
| lead_scoring_dataset | 1,083 |
| sales_forecasting_dataset | 172 |
| customer_segmentation_dataset | 244 |
| churn_prediction_dataset | 59 |

---

## 4. Data-quality report — all categories

Full machine-readable results: `full_audit_report.json`. Summary by category (0 = clean unless noted). This report explicitly separates duplicate primary keys, exact duplicate rows, repeated foreign keys, invalid foreign keys, acceptable nulls, and unacceptable nulls into their own categories/rows (rather than lumping repeated FK values in with duplicates), per the taxonomy `validate_dataset.py`'s final summary now prints in eight labeled buckets:

| # | Category | Result |
|---|---|---|
| 1 | Duplicate rows (exact whole-row duplicates) | 0 across all 24 tables |
| 2 | Duplicate primary keys (each table's own PK column only) | 0 across all 24 tables |
| 3 | Duplicate business entities (company name+city, website domain, GSTIN, contact/rep email, product name, customer↔company) | 0 |
| 4 | Missing required values | 0 across all required columns in 10 checked tables |
| 4b | Acceptable null values (nullable-by-design columns) — informational, never an error | see §1.7 note below and `4b_acceptable_null_values_informational` in the JSON for the full per-table/per-column breakdown |
| 5 | Unexpected nulls / conditional rules (Converted needs converted_at, Disqualified needs a reason, Closed Won/Lost need close date/outcome/loss reason) | 0 |
| 6/7 | Invalid foreign keys / orphan records (40 FK relationships + 4 semantic cross-checks) | 0 |
| 6b | Repeated foreign keys (a parent ID appearing in many child rows) — informational, **never** treated as a duplicate or an error | 40 relationships reported explicitly with repeat counts (e.g. `companies.industry_id` max 222x) — see `6b_repeated_foreign_keys_informational` |
| 8 | Invalid categorical values (12 enum columns checked against the design doc's allowed sets, including `activities.activity_type`/`.status`/`.priority`) | 0 |
| 9 | Invalid / unparseable dates | 0 unparseable; future-dated values are limited to 5 explicitly policy-documented forward-looking fields (`expected_close_date`, `renewal_date`, `campaigns.end_date`, `activities.due_date`, `activities.next_follow_up_date` — see `business_rules.md` rules 4.5–4.7) — expected, not a defect. Raw future-dated counts: `expected_close_date` 39, `renewal_date` 29, `campaigns.end_date` 2, `activities.due_date` 178, `activities.next_follow_up_date` 112 — all policy-allowed; genuine `violations` = 0 for all five (see `9b_future_date_policy_violations` and `26_activities_validation`) |
| 10 | Impossible date sequences (8 checks: created/contacted/qualified/converted ordering, opp created-vs-close, customer-since-vs-opp-close, case resolved-vs-opened) | 0 |
| 11 | Lead-status transitions (chain continuity + terminal-state enforcement) | 0 (was 188 broken chains — see §1.1) |
| 12 | Sales-stage transitions (chain continuity + terminal-state enforcement) | 0 |
| 13 | Invalid customer derivations (must originate from a Closed Won opportunity at the same company) | 0 (was 12 `customer_status`/`renewal_date` cross-field inconsistencies — see §1.4) |
| 14 | Transaction chronology (no transaction before `customer_since`) | 0 |
| 15 | Revenue inconsistencies (line-item math, deal value vs. product-line sum, refund/negative-amount invariant) | 0 — includes the 2-row `Refund` negative-amount pattern in `customer_transactions`, confirmed valid and now a checked invariant rather than an unexplained anomaly (see §1.8) |
| 16 | Opportunity probability vs. stage band | 0 |
| 17 | Unrealistic distributions | win rate 46.4%, lead conversion 18.3%, size/status/tier splits all within the design doc's target ranges — see §5 |
| 18 | Excessive repeated values | max single-value share ≤ 8.1% (`opportunities.deal_value_inr`), explained by the fixed 20-product catalog with discrete discount tiers — a small catalog naturally produces some identical deal totals; not a generation artifact |
| 19 | Placeholder records (test/dummy/lorem/todo/etc. in any name/title/subject field) | 0 |
| 20 | Suspicious synthetic patterns (identical created/close timestamps, etc.) | 0 |
| 21 | ML target leakage (8 checks — see §6) | 0 — includes `segmentation.cluster_id_column_present = False`: `customer_segmentation_dataset` carries no cluster/segment-label column at all (removed entirely, not just left blank — see §1.9) |
| 22 | Class imbalance | lead conversion 18.3%, lead scoring 18.3%, churn 25.4% — all within realistic, modelable ranges (not <2% or >90%) |
| 23 | Data duplication across source and ML tables | ML tables copy forward a small number of day-0 identifying/feature columns (e.g. `company_id`, `company_size_at_lead_time` into `lead_scoring_dataset`) by design — this is standard feature denormalization, not redundant storage, and none of it includes outcome-adjacent columns |
| 24 | Inconsistent IDs | every table's PK uses exactly one prefix and one fixed digit-width — fully self-consistent |
| 25 | Inconsistent naming/formatting | 0 after fix (was 18 apostrophe emails — see §1.2); phone numbers are 100% consistent in the dataset's `+91-XXXXXXXXXX` house format |
| 26 | Activities validation (`due_date`/`activity_date`/`next_follow_up_date` cross-field logic, `Completed` ⇒ `outcome` required, likely-duplicate-business-event detection, repeated-content warnings) | 0 violations (a validator comparison-precision bug, not a data defect, was caught and fixed before delivery — see §1.5); 0 likely duplicate business events; 0 repeated-content warnings flagged (max subject repeat share 0.17%, max description repeat share 0.08% — see §1.6) |
| 26b | Activities missing-value breakdown (`lead_id`/`contact_id`/`company_id`/`opportunity_id`/`customer_id`/`outcome`/`next_follow_up_date`, cross-tabulated against `activity_type`/`status`) | informational only — every pattern investigated is logically valid, not a defect: e.g. `customer_id` is populated 100% of the time for `Support Follow-up` activities and only 0–9% for pipeline-stage types (a customer usually doesn't exist yet at that point), `outcome` is populated exactly 100% for `Completed` and exactly 0% for every still-open status, and `next_follow_up_date` is 0% for `Planned`/`Cancelled` (nothing to schedule yet, or nothing left to follow up on) — see the full breakdown in `26b_activities_missing_value_breakdown` |
| 27 | ML dataset validation (duplicate source-entity IDs where uniqueness is expected, invalid target values, invalid numeric values, invalid dates, across all 5 ML-ready tables) | 0 violations — `lead_conversion_dataset`/`lead_scoring_dataset` each have exactly one row per `lead_id` (0 duplicates); the multi-snapshot tables (`churn_prediction_dataset`, `customer_segmentation_dataset`, `sales_forecasting_dataset`) correctly repeat entity IDs across time buckets by design (informational, not a defect) with 0 duplicated (entity, time-bucket) pairs |
| 27b | ML missing-value investigation (`churn_prediction_dataset`, `customer_segmentation_dataset`, `sales_forecasting_dataset`) | all 4 null-bearing columns investigated classify as `logically_valid`, each backed by a computable invariant — 0 invariant violations after the §1.7 fix (was 10/244 rows in `customer_segmentation_dataset.avg_satisfaction_score` before the fix — see §1.7). `customer_segmentation_dataset.segment_label_cluster_id` no longer appears here because the column itself was removed — see §1.9 |

---

## 5. Distribution report (highlights)

- Opportunity win rate (Closed Won / all closed): **46.4%** — realistic for a validated, active pipeline; consistent with the design doc's target range.
- Lead → Converted rate: **18.3%** of all leads ever created.
- Company size mix: Small 31.1%, Mid 24.3%, Micro 19.6%, Large 12.6%, Enterprise 12.4% — matches the intended long-tail-of-SMBs shape.
- Customer status mix: Active 56.3% (27/48), At Risk 18.7% (9/48), Paused 25.0% (12/48) — updated after the §1.4 fix corrected 12 customers whose status contradicted an already-overdue `renewal_date`.
- Customer tier mix: Bronze 75.0%, Silver 25.0%.
- ML target rates: lead_conversion 18.3%, lead_scoring 18.3% (same underlying population, day-0 view), churn 25.4% — none are degenerate (no class below ~2% or above ~90%).
- Activity type mix (2,359 rows, v2): Call 28.6%, Email 19.8%, Follow-up 18.0%, Meeting 13.1%, Task 11.0%, Demo 2.6%, Proposal Discussion 2.4%, Negotiation 1.6%, Support Follow-up 1.6%, Site Visit 1.2%. Activity status mix: Completed 54.3%, Planned 15.6%, Pending 10.6%, Rescheduled 7.8%, In Progress 7.7%, Cancelled 4.2%.

## 6. Referential-integrity report

40 declared foreign-key relationships (34 across the core schema plus `activities`' 6) plus 4 semantic cross-checks (contact↔company consistency on leads/opportunities/support cases, customer↔originating-opportunity company match) were checked; all resolve with **zero orphans and zero mismatches**. Full detail in `full_audit_report.json` under `6_7_invalid_fk_and_orphans`.

## 7. Business-rule validation report

Covers categories 10–16: date-sequence logic, lead/opportunity state-machine transitions, customer derivation rules, transaction chronology, revenue arithmetic, and probability-vs-stage bands. All zero after the fix in §1.1. Full detail in `full_audit_report.json`.

## 8. ML leakage report

Re-verified all 8 leakage checks from the original Phase 4 validation, now against the regenerated tables:

- `lead_conversion_dataset`: observation cutoff never falls after `converted_at` — 0 violations.
- `lead_scoring_dataset`: cutoff always exactly equals `created_at` (strict day-0) — 0 violations; forbidden post-day-0 columns (`num_status_transitions_before_cutoff`, `estimated_budget_inr`, `rep_trailing_conversion_rate`) confirmed absent.
- `churn_prediction_dataset`: `customer_status` confirmed absent as a feature (it would leak the outcome).
- `customer_segmentation_dataset`: confirmed the table carries **no** cluster/segment-label column at all — removed entirely rather than shipped as an always-blank placeholder (see §1.9).

Full independent recomputation checks (trailing-90d transaction sums, pipeline-value snapshots) from `validate_ml_datasets.py` also re-ran clean — see `phase4_ml_validation_report.json`.

## 9. Validation scripts delivered

- `audit.py` — 14-category master-table audit (from Phase 1B)
- `validate_phase2.py` — contacts/leads/lead_status_history/campaign_responses validator
- `validate_phase3.py` — opportunities/customers/transactions/support-cases validator
- `validate_ml_datasets.py` — ML-dataset leakage/traceability/split validator
- `full_audit.py` / `validate_dataset.py` — this audit's cross-cutting 25-category + activities (§26) validator spanning all 24 tables
- `generate_activities.py` — the `activities` table generator (read-only against all prior phases; see README §"How the data was generated")
- `full_audit_report.json` — this audit's full machine-readable output

## 10. Remaining limitations (not defects — scope/scale honesty)

- **Scale:** this remains the 1,200-company pilot batch (not full-scale generation). Absolute row counts (e.g. 198 opportunities, 48 customers) are small enough that some per-category percentages (§5) will move noticeably if the dataset is scaled up; the *shape* of each distribution is designed to hold at scale, not the exact counts.
- **Customer tier ceiling:** only `Bronze`/`Silver` tiers appear in this pilot batch (`Gold`/`Platinum`, if defined in the tier-band logic, require higher-value customers than this batch size happened to produce) — an artifact of the small closed-won sample, not a generation bug; scaling up should populate the higher tiers.
- **`customer_status` vocabulary:** the dataset uses `Active` / `At Risk` / `Paused` rather than an explicit `Churned` status — this is a deliberate design choice (churn is derived behaviorally from the transaction/renewal record, per the ML churn-dataset methodology, rather than stored as a status label) documented in the Phase 4 delivery, not an oversight.
- **Real-company layer:** company *identities* (name, city, industry) for the curated real-company subset are genuine public reference facts; every interaction, score, financial figure and outcome attached to them remains entirely synthetic, as required from Phase 1 onward. No new real-world data was introduced during this audit.
- **Non-idempotent generator:** `generate_opps_customers.py` still reads and rewrites `leads.csv`/`companies.csv` in place as part of its backfill step; any future manual rerun must start from freshly regenerated (not previously-backfilled) Phase-2 output, exactly as documented when this constraint was first discovered.
