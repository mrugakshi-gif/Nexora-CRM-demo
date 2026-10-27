# activities.csv — Duplicate & Content-Variety Report

This report responds directly to a user review of the delivered `activities.csv` that found no exact duplicate rows and no duplicate `activity_id` values, but flagged that subjects and descriptions repeated far more than a real CRM activity log would, making the file "look artificially generated." Full root-cause narrative: `data_quality_report.md` §1.6. Full validator output: `full_audit_report.json` → `26_activities_validation`.

## 1. Record counts

| Metric | Value |
|---|---:|
| Original record count (pre-dedup-pass generation) | 2,359 |
| Records removed as duplicates | 0 |
| Records repaired as duplicates (re-rolled in place, not deleted) | 0 |
| **Final record count (delivered `activities.csv`)** | **2,359** |

No records were removed. The business-event dedup pass (defined below) found 0 rows that collided with an earlier row on every field that defines "the same event" — the widened text vocabulary made a genuine collision statistically unlikely at this dataset size, and none occurred in this run. The pass still runs on every regeneration as a permanent safeguard: if a future, larger-scale regeneration does produce a collision, that row is **repaired in place** (its date nudged and its subject/description/outcome re-rolled against its same real entity linkage) rather than deleted, so a valid business event is never lost to satisfy this check.

## 2. Duplicate-detection method

A row is only counted as a **business-event duplicate** of another row if it matches on **all six** of:

`activity_type`, `company_id`, `contact_id`, `opportunity_id`, `activity_date`, `subject`

Matching on any subset of these — the same `activity_type` alone, the same `subject` text alone, or any other partial match — is **not** flagged. This directly satisfies the requirement not to treat a shared activity type or subject, by itself, as evidence of duplication: two different companies legitimately have "Email - budget approval status" activities on different dates, and that is not a duplicate.

**Result on the delivered file:** 0 groups of ≥2 rows share all six fields. `likely_duplicate_business_events.violations = 0`.

## 3. Repeated-content warnings (informational — distinct from duplicates)

Because zero duplicate *business events* doesn't guarantee varied *text*, the validator separately tracks how repetitive the free-text fields are, independent of whether the underlying events are distinct. Threshold: any exact `subject` or `description` value used more than 5 times, or in more than 0.5% of rows, is listed as a warning (this never fails validation).

| Field | Unique values | Total rows | Max repeat count | Max repeat share | Values over threshold |
|---|---:|---:|---:|---:|---:|
| `subject` | 2,310 | 2,359 | 4 | 0.17% | 0 |
| `description` | 2,351 | 2,359 | 2 | 0.08% | 0 |

For comparison, the previously delivered file (v1) had 1,577/2,348 unique subjects (67.2%) with one subject repeated 31 times (1.32% share) — well past what a real activity log would show. The v2 generator fix (widened topic vocabulary from 20 → 51 phrases; subjects now always include the company name, and the contact's name for ~55% of contact-bearing rows; outcomes composed from an opening × topic × next-step combination instead of a short fixed list) brought both fields' repetition down by roughly an order of magnitude, with zero warnings triggered in this delivery.

`outcome` (for `Completed` activities) is tracked the same way in the underlying data, though it is not one of the two fields the validator's `repeated_content_warnings` block enumerates by name: 1,246 of 1,280 Completed rows (97.3%) have a unique outcome string, versus only 48 distinct outcome strings covering all 1,296 Completed rows in v1 (well under 4% unique).

## 4. All remaining validation issues

None. The full `26_activities_validation` block, and every other category (1–25, plus `9b_future_date_policy_violations`), report 0 genuine violations against the delivered `activities.csv` — see the "ACTIVITIES -- repeated-content warnings" block and the final `RESULT: PASS` line printed by `scripts/validation/validate_dataset.py`, and the machine-readable `docs/full_audit_report.json`.

Two items remain **expected, not violations**, and are called out explicitly rather than hidden:

- `activities.due_date` (178 rows) and `activities.next_follow_up_date` (112 rows) are dated after the generation cutoff — both are schedule/deadline fields on open (Planned/Pending/In Progress/Rescheduled) activities, policy `"always_allowed"` (see `business_rules.md` rule 4.7).
- 96 activities carry no lead/contact/company/opportunity/customer link at all — these are general internal tasks, valid by design (rule 3.7), not missing-value defects.

## 5. Foreign keys, dates, and outcome consistency

All re-checked against this delivered file, unaffected by the content-variety fix (no entity linkage was changed by it):

- Foreign keys (`lead_id`, `contact_id`, `company_id`, `opportunity_id`, `customer_id`, `sales_rep_id`) — 0 orphans across all 6 relationships.
- `due_date` on/after `activity_date`'s calendar date — 0 violations.
- `next_follow_up_date` strictly after `activity_date`'s calendar date (when present) — 0 violations.
- `activity_date` never after `created_at`/`updated_at` — 0 violations.
- Every `Completed` activity has a non-blank `outcome` — 0 violations.
- Planned/Pending/In Progress/Rescheduled activities retain logically open due dates (no forced outcome; `due_date` may extend past the cutoff); Cancelled activities carry an outcome only about half the time (a cancellation reason), matching real-world logging behavior where not every cancelled touchpoint gets a note.
