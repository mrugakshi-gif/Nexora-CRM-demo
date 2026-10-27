# Validation Report

## Validation scripts and what each covers

| Script | Scope |
|---|---|
| `scripts/validation/validate_dataset.py` (packaged from `full_audit.py`) | All 24 tables, all categories requested for the final audit: duplicate rows/keys/entities, missing values (required and acceptable-null), FK integrity/orphans and repeated-FK reporting, categorical values, date validity/sequencing, status/stage transitions, customer derivation, transaction chronology, revenue arithmetic, probability-vs-stage bands, distributions, repeated values, placeholder records, synthetic-pattern checks, ML leakage, class imbalance, source/ML duplication, ID consistency, naming/formatting, activities-specific checks, and ML-dataset-specific duplicate/target/numeric/date/missing-value checks. **This is the authoritative, most current validator — run this one.** |
| `audit.py` (Phase 1 artifact) | 14-category master-table-only audit (industries → companies) |
| `validate_phase2.py` (Phase 2 artifact) | contacts / leads / lead_status_history / campaign_responses |
| `validate_phase3.py` (Phase 3 artifact) | opportunities / opportunity_products / opportunity_stage_history / customers / customer_transactions / customer_support_cases |
| `validate_ml_datasets.py` (Phase 4 artifact) | The 5 ML-ready datasets: ID traceability, label consistency, leakage audit, split proportions/chronology, distributions, nulls |

The earlier phase-specific scripts are kept in the package for transparency (they show the incremental validation history this dataset went through) but `validate_dataset.py` supersedes them — it is the one script that checks the fully assembled, final dataset end-to-end, including cross-phase interactions the phase-specific scripts couldn't see (e.g. it was this script that caught the lead-status chronology defect described in `data_quality_report.md`, which none of the phase-specific scripts individually could catch because each only looked at its own phase's tables).

## How to run

```bash
pip install -r requirements.txt
python3 scripts/validation/validate_dataset.py
```

Run it from `scripts/` (it defaults to the sibling `../data/source` and `../data/ml`, or pass `--data-dir` explicitly). It prints a full JSON report to stdout, exits non-zero on any unresolved violation, and writes the same report to `data/full_audit_report.json`. The report from the run that produced this delivery is preserved at [`docs/full_audit_report.json`](full_audit_report.json) rather than under `data/`, so that `data/` holds only the 23 dataset CSVs.

## Section `9b_future_date_policy_violations`

`9_invalid_dates` reports, per date column, both a raw `future_dated` count (informational — how many rows fall after the 2026-09-15 generation cutoff) and a policy-aware `violations` count (how many of those are actually disallowed, per that column's documented `DATE_COLUMN_POLICY` in `business_rules.md` rule 4.5: `"never"`, `"always_allowed"`, or `"conditional"`). For the three columns permitted to be forward-dated at all, `9b_future_date_policy_violations` adds four explicit, named cross-field checks that catch the genuine ways a forward-dated value can still be wrong even when the raw future-dating itself is fine:

- `customers.renewal_date_overdue_while_status_active` — an overdue renewal must not coexist with `customer_status = "Active"` (rule 4.6).
- `customers.renewal_date_before_customer_since` — a renewal date can never precede the customer's start date.
- `opportunities.expected_close_before_created_at` — a forecast close date can never precede the opportunity's creation date.
- `campaigns.end_date_before_start_date` — a campaign can't end before it starts.

The final printed summary enumerates every column with a non-zero `future_dated` count, states its policy and its (separately computed) `violations` count, and only then prints PASS/FAIL — so the summary can never assert "all categories clean" while a JSON block above it shows an unexplained non-zero number. This replaced an earlier version of the script that suppressed a fixed whitelist of "expected non-zero" paths from the pass/fail check without printing why, which could make a legitimate future-dated count look identical, in the summary, to a genuine violation being silently ignored.

## Section `26_activities_validation`

Beyond the cross-field date/outcome checks described in `business_rules.md` rule 4.7, this section carries two checks specific to the user-reported "looks artificially generated" review of `activities.csv`:

- `likely_duplicate_business_events` — a **violation**, not a warning. Two rows are only flagged as the same business event if they match on ALL of `activity_type`, `company_id`, `contact_id`, `opportunity_id`, `activity_date`, and `subject` simultaneously. Sharing just an `activity_type` or a `subject` in isolation is explicitly NOT flagged (that's normal — many companies discuss the same topic). Each flagged group lists the colliding `activity_ids` so they can be inspected directly.
- `repeated_content_warnings` — **informational only, never fails the run**. Reports, for `subject` and `description` independently, the unique-value count, the single most-repeated value's count/share, and a list of any exact text used more than 5 times or over 0.5% of all rows. This is what actually caught the v1 dataset's template collapse (`"Email - contract terms review"` repeated 31 times) even though that dataset had zero duplicate business events by the stricter definition above.

The printed summary echoes both under a dedicated "ACTIVITIES -- repeated-content warnings" block, separate from the PASS/FAIL verdict, so a clean run's absence of duplicates is never confused with an absence of repetitive-sounding text (they are different questions, checked separately).

## The eight-bucket final summary (duplicate PKs vs. exact duplicate rows vs. repeated FKs vs. invalid FKs vs. acceptable/unacceptable nulls vs. warnings vs. errors)

A user-reported issue with an external/basic testing pass motivated this: that separate tool had flagged repeated `company_id`/`customer_id`/`opportunity_id`/`lead_id`/`sales_rep_id` values as duplicate-record errors, when a foreign key repeating across many child rows is exactly what a correct relational schema looks like (one company legitimately has many contacts; one sales rep legitimately owns many opportunities). `full_audit.py`'s own category 2 (`duplicate_primary_keys`) was already scoped to each table's own primary-key column only, and was never conflating the two — but the printed report didn't make that separation *explicit* enough for a reader (or another tool) to trust without re-deriving it themselves. The final summary now prints exactly eight labeled buckets, in this order:

1. **Duplicate primary keys** — `2_duplicate_primary_keys`, each table's own PK column only. Error if nonzero.
2. **Exact duplicate rows** — `1_duplicate_rows`, whole-row identity across every column. Error if nonzero.
3. **Repeated foreign keys** — `6b_repeated_foreign_keys_informational`, one entry per FK relationship with its distinct-value count, populated-row count, and max repeat count (e.g. `companies.industry_id` repeats up to 222x — expected, since only 20 industries exist for 1,200 companies). **Never** checked against pass/fail; explicitly labeled `is_this_an_error: false` in the JSON.
4. **Invalid foreign keys** — `6_7_invalid_fk_and_orphans`, orphan references (a child row's FK value that doesn't exist in the parent table) plus 4 semantic cross-checks. Error if nonzero.
5. **Acceptable null values** — `4b_acceptable_null_values_informational`, blank-cell counts for columns that are nullable by design (see `data_dictionary.md`'s Nullable column). **Never** checked against pass/fail.
6. **Unacceptable null values** — `4_missing_required_values` and `5_unexpected_nulls_conditional_rules` (required columns and conditional-required rules), plus the `invariant_violations` leaf of `27b_ml_missing_value_investigation` (a genuine contradiction in an ML dataset's null pattern, as opposed to its informational `null_count`). Error if nonzero.
7. **Warnings** — printed, **never** fail the run: the future-dated-columns policy summary (§ above), `26_activities_validation.repeated_content_warnings`, and the ML multi-snapshot tables' expected repeated-entity-ID counts.
8. **Errors** — every other genuine-violation check not covered by buckets 1/2/4/6: duplicate business entities, invalid categorical values, date-sequence/transition/derivation/chronology/revenue/probability checks, placeholder records, suspicious synthetic patterns, ML target leakage, ID-prefix/width consistency, naming/formatting, the rest of `26_activities_validation`, and the rest of `27_ml_dataset_validation`.

This also closed a real gap in the previous summary logic: `6_7_invalid_fk_and_orphans`, `8_invalid_categorical_values`, `19_placeholder_records`, `20_suspicious_synthetic_patterns`, `21_ml_target_leakage`, `24_inconsistent_ids`, and `25_inconsistent_naming_formatting` were all computed and printed in the JSON (and had always been reported as 0 in `MANIFEST.md`, correctly, based on manual inspection) but were **not** actually wired into the script's own pass/fail exit code — the run could never have failed on a regression in any of those seven categories even though the report claimed to cover them. All seven are now included in bucket 8 (with the appropriate leaf selected for each — e.g. only `.invalid_count` from category 8, not the `.invalid_values` list; only the `_internally_inconsistent` booleans from category 24, not the prefix/width lists).

## Last known-good run — summary

Every genuine-violation check across all categories — buckets 1, 2, 4, 6, and 8 above — reports **zero unresolved violations** against the CSVs shipped in this package (`scripts/validation/validate_dataset.py` exits 0). Five real data defects were found and fixed during development (see `data_quality_report.md` §1 for the full root-cause writeup of each):

1. Lead-status-history chronology broken for 188/201 converted leads — fixed by anchoring opportunity creation to the lead's actual Sales-Qualified transition timestamp instead of the earlier MQL timestamp.
2. 18 contact emails contained an unrealistic apostrophe from the surname "D'Souza" — fixed by stripping non-alphanumeric characters when building email/LinkedIn handles.
3. 1 transaction dated 4 days past the generation cutoff — fixed by clamping the first-transaction date the same way `customer_since` was already clamped.
4. 12 customers were marked `customer_status = "Active"` despite an already-overdue `renewal_date` (46–470 days overdue, no covering transaction) — fixed by downgrading status (`"At Risk"` if <90 days overdue, else `"Paused"`) deterministically from the already-computed renewal date at customer-creation time. See `data_quality_report.md` §1.4.
5. `customer_segmentation_dataset.avg_satisfaction_score` was computed from an unbounded all-time case window while its neighboring column `support_case_count_last_12mo` used a trailing-12-month window, letting 10/244 rows show a non-null score alongside a 0 trailing-window case count — fixed by scoping both columns to the same trailing-12mo window. See `data_quality_report.md` §1.7.

Two additional issues were found and fixed after `activities` was added, neither of them a defect in the shipped data: a validator comparison-precision bug (§1.5) and, following a user review, excessive text-template repetition in `activities.subject`/`description`/`outcome` — 0 duplicate records, but far too few distinct phrasings (§1.6, fixed by widening the generator's text vocabulary and adding a business-event dedup-and-repair pass; 0 rows deleted).

A handful of checks return non-zero **raw** `future_dated` counts that are **expected, not defects**, and are distinguished from genuine `violations` (always 0) in both the JSON and the printed summary — documented so a future validator run doesn't mistake them for regressions:

- Forward-looking schedule fields — `opportunities.expected_close_date` (39 rows), `customers.renewal_date` (29 rows), `campaigns.end_date` (2 rows), `activities.due_date` (178 rows), `activities.next_follow_up_date` (112 rows) — are legitimately dated after the generation cutoff; see `business_rules.md` rules 4.5–4.7 for the exact, per-column policy and the one genuine cross-field constraint on `renewal_date`.
- `opportunities.deal_value_inr` has some repeated values (max ~8% share) — a natural consequence of a small, fixed 20-product catalog with discrete discount tiers, not a generation artifact.
- `lead_scoring_dataset` intentionally re-includes a couple of day-0 identifying/firmographic columns also present in `leads` (`company_id`, `company_size_at_lead_time`) — standard feature denormalization, not redundant storage or leakage.
- `activities.subject`/`.description` repeat at most 0.17%/0.08% of rows (see `repeated_content_warnings` above) — well under the 5x/0.5% warning threshold, so 0 values are flagged in this delivery.

## Interpreting a future failing run

If you regenerate the dataset yourself (different seed, larger scale, or after modifying a generator script) and `validate_dataset.py` reports non-zero counts outside the expected exceptions above, treat it as a real defect and do not ship the data until root-caused and fixed at the generator source — this dataset's own development process (see `data_quality_report.md`) is the model to follow: locate the affected records, trace them to the generation code, fix the code, regenerate, and re-validate, rather than hand-editing the CSV.
