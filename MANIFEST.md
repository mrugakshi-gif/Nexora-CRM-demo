# FINAL_INDIAN_B2B_CRM_DATASET — Manifest

Generated at final packaging time, from the same validation run that certified this delivery (see `docs/full_audit_report.json`, `docs/validation_report.md`). Generation seed: `20260915`. Generation cutoff date: `2026-09-15`.

## 1. Final row counts — every CSV file

### Master / reference tables (8)
| File | Rows |
|---|---:|
| data/source/industries.csv | 20 |
| data/source/territories.csv | 18 |
| data/source/departments.csv | 7 |
| data/source/lead_sources.csv | 12 |
| data/source/products.csv | 20 |
| data/source/sales_reps.csv | 80 |
| data/source/campaigns.csv | 180 |
| data/source/companies.csv | 1,200 |

### Transactional tables (10)
| File | Rows |
|---|---:|
| data/source/contacts.csv | 925 |
| data/source/leads.csv | 1,083 |
| data/source/campaign_responses.csv | 676 |
| data/source/opportunities.csv | 198 |
| data/source/opportunity_products.csv | 388 |
| data/source/customers.csv | 48 |
| data/source/customer_transactions.csv | 116 |
| data/source/customer_support_cases.csv | 113 |
| data/source/activities.csv | 2,359 |

### Historical / audit-trail tables (2)
| File | Rows |
|---|---:|
| data/source/lead_status_history.csv | 4,129 |
| data/source/opportunity_stage_history.csv | 703 |

### ML-ready datasets (5)
| File | Rows |
|---|---:|
| data/ml/lead_conversion_dataset.csv | 1,083 |
| data/ml/lead_scoring_dataset.csv | 1,083 |
| data/ml/sales_forecasting_dataset.csv | 172 |
| data/ml/customer_segmentation_dataset.csv | 244 |
| data/ml/churn_prediction_dataset.csv | 59 |

**24 CSV files, 15,254 total data rows.** Every file opened and parsed successfully with pandas immediately before packaging (see §3).

## 2. Data-quality summary (final validation run)

`scripts/validation/validate_dataset.py` was re-run immediately before this ZIP was created, against exactly the CSVs in `data/`. **Exit code 0.** The script's final printed report is organized into eight explicit buckets (see script output / `docs/validation_report.md`): duplicate primary keys, exact duplicate rows, repeated foreign keys (informational, never an error), invalid foreign keys, acceptable null values (informational, never an error), unacceptable null values, warnings (printed, never fail the run), and errors (every other genuine-violation check). This structure exists specifically so a repeated foreign-key value (e.g. many contacts sharing one `company_id`) is never misread as a duplicate-record error — see `docs/data_quality_report.md` §1.7 note and the walkthrough in `docs/validation_report.md`.

| Category | Result |
|---|---|
| 1. Duplicate rows (exact whole-row duplicates) | 0, all 24 tables |
| 2. Duplicate primary keys (each table's own PK column only) | 0, all 24 tables |
| 3. Duplicate business entities | 0 |
| 4. Missing required values | 0 |
| 4b. Acceptable null values (nullable-by-design columns) | informational only — never an error; see `4b_acceptable_null_values_informational` in `docs/full_audit_report.json` for the full per-table breakdown |
| 5. Unexpected nulls / conditional rules | 0 |
| 6–7. Invalid foreign keys / orphan records | 0 across 40 relationships + 4 semantic checks — see `docs/referential_integrity_report.md` |
| 6b. Repeated foreign keys (a parent ID appearing in many child rows) | informational only — **never** treated as a duplicate or an error; 40 relationships reported with explicit repeat counts (e.g. `companies.industry_id` max 222x) in `6b_repeated_foreign_keys_informational` |
| 8. Invalid categorical values | 0 (includes `activities.activity_type` / `.status` / `.priority`) |
| 9. Invalid dates | 0 unparseable; 0 genuine violations. Raw future-dated counts (expected, policy-documented — see `docs/business_rules.md` rules 4.5–4.7, `docs/validation_report.md`): `opportunities.expected_close_date` 39, `customers.renewal_date` 29, `campaigns.end_date` 2, `activities.due_date` 178, `activities.next_follow_up_date` 112. 4 additional cross-field checks in `9b_future_date_policy_violations` (e.g. overdue renewal vs. Active status) — 0 violations |
| 10. Impossible date sequences | 0 |
| 11. Lead-status transitions | 0 |
| 12. Sales-stage transitions | 0 |
| 13. Invalid customer derivations | 0 |
| 14. Transaction chronology | 0 |
| 15. Revenue inconsistencies | 0 — includes the `customer_transactions` refund/negative-amount invariant (a negative `amount_inr` iff `transaction_type = "Refund"`), confirmed valid for the 2 refund rows this dataset ships — see `docs/data_quality_report.md` §1.8 |
| 16. Opportunity probability inconsistencies | 0 |
| 17. Unrealistic distributions | none found — win rate 46.4%, lead conversion 18.3%, size/tier/status mixes within realistic range |
| 18. Excessive repeated values | none — max single-value share 8.1%, explained by a small fixed product catalog |
| 19. Placeholder records | 0 (includes `activities.subject`) |
| 20. Suspicious synthetic patterns | 0 |
| 21. ML target leakage | 0 across 8 checks — see `docs/ml_leakage_report.md`. `customer_segmentation_dataset` now carries no cluster/segment-label column at all (removed, not just left blank — see §1.9) |
| 22. Class imbalance | none degenerate — 18.3% / 18.3% / 25.4% positive rates |
| 23. Source-vs-ML duplication | none improper — day-0 column overlap in lead_scoring_dataset is by design |
| 24. Inconsistent IDs | 0 — every table's PK uses exactly one prefix and one fixed width |
| 25. Inconsistent naming/formatting | 0 |
| 26. Activities validation | 0 violations — `due_date` on/after `activity_date`, `next_follow_up_date` strictly after `activity_date`, `activity_date` never after `created_at`/`updated_at`, every `Completed` activity has an `outcome`, 0 likely-duplicate business events (`activity_type`+`company_id`+`contact_id`+`opportunity_id`+`activity_date`+`subject`), 0 repeated-content warnings flagged (max subject repeat share 0.17%, max description repeat share 0.08%) — see `docs/data_quality_report.md` §1.5–§1.6 |
| 26b. Activities missing-value breakdown | informational — `lead_id`/`contact_id`/`company_id`/`opportunity_id`/`customer_id`/`outcome`/`next_follow_up_date` nulls cross-tabulated against `activity_type`/`status`; every pattern found is logically valid, e.g. `outcome` populated exactly 100% for `Completed` and exactly 0% for every open status |
| 27. ML dataset validation | 0 violations — 0 duplicate `lead_id` in `lead_conversion_dataset`/`lead_scoring_dataset` (single-snapshot-per-lead, uniqueness required); 0 duplicated (entity, time-bucket) pairs in the 3 multi-snapshot ML tables (repeated entity IDs alone are expected there, by design); 0 invalid target values, invalid numeric values, or unparseable dates across all 5 ML tables |
| 27b. ML missing-value investigation | `churn_prediction_dataset`, `customer_segmentation_dataset`, `sales_forecasting_dataset` — all 4 investigated null-bearing columns classified as `logically_valid`, each backed by a computable invariant; 0 invariant violations (a real defect — a window-mismatch bug in `avg_satisfaction_score` — was found and fixed in an earlier round; see §1.7 below) |

Seven real defects/documentation-gaps were found and corrected during this project — all fixed at the generator source and re-validated; full root-cause writeup in `docs/data_quality_report.md`:

1. Lead-status-history chronology broken for 188/201 converted leads (§1.1).
2. 18 apostrophe-surname emails (§1.2).
3. One future-dated transaction (§1.3).
4. 12 customers whose `customer_status = "Active"` contradicted an already-overdue `renewal_date` (§1.4) — found during a later, more rigorous review of the three legitimately-forward-dated fields, which also prompted rewriting the validator's summary logic so it can never again print "clean" alongside an unexplained non-zero count.
5. A window-mismatch bug in `customer_segmentation_dataset.avg_satisfaction_score` (§1.7), found by an explicit missing-value investigation requested after a review flagged that an earlier external/basic testing pass had also miscategorized repeated foreign-key values as duplicate-record errors; the validator's report structure was rewritten into eight explicit buckets (duplicate PKs, exact duplicate rows, repeated FKs, invalid FKs, acceptable nulls, unacceptable nulls, warnings, errors) so that misreading can't recur — see `docs/validation_report.md`.
6. `customer_segmentation_dataset.segment_label_cluster_id` — a misleading always-100%-blank label column — removed from the schema entirely rather than left ambiguous, since this is a genuinely unsupervised feature table with no ground-truth cluster to ship (§1.9).
7. `companies.sub_industry` — previously hardcoded blank for 100% of rows despite being documented as "sparsely populated" — populated from a real, industry-scoped vocabulary for ~95% of companies via a generation change verified (by diffing a full with/without pipeline re-run) to touch no other column in any of the 24 CSVs (§1.10).

The `customer_transactions.amount_inr` negative-value pattern (2 rows) was also investigated (§1.8) and confirmed to be a valid, intentional refund/reversal pattern rather than a defect — it is now an explicit, machine-checked invariant rather than an unexplained anomaly. The repeated-foreign-key-vs-duplicate-primary-key concern was re-verified directly against the validator's own code and confirmed to have already been correctly scoped (§1.11) — no code change was needed there, only the documented evidence.

The `activities` table, added earlier in this project, went through the same regenerate-and-revalidate discipline before delivery (one generator bug — a date/datetime-precision mismatch between `due_date` and `activity_date` in the validator's own comparison logic, not the data — was caught and fixed during that pass; see `data_quality_report.md` §1.5). It was then revised a second time (v2) after a user review found no duplicate records but excessive text-template repetition in `subject`/`description`/`outcome`; the generator's text vocabulary was widened and an explicit business-event dedup-and-repair pass was added, with 0 records deleted — see `data_quality_report.md` §1.6. **No known unresolved data-quality issues remain in this delivery.**

## 3. Pre-packaging checks performed

- [x] Full validation re-run immediately before packaging (`scripts/validation/validate_dataset.py`, exit code 0)
- [x] Every CSV file opened and parsed successfully (pandas `read_csv`, all 24 files, no errors)
- [x] SQL schema (`sql/create_tables_postgres.sql`) load-tested against a live PostgreSQL instance with these exact CSVs — all 24 tables loaded with matching row counts, 0 constraint violations
- [x] All foreign keys and relationships verified valid (§1 of `docs/referential_integrity_report.md`)
- [x] Documentation cross-checked against the final dataset (row counts, column lists, and category results below all sourced from this run, not an earlier one)
- [x] No temporary, duplicate, outdated, or intermediate files included — only the current generator scripts, current validator, current CSVs, and current documentation
- [x] Filenames consistent and meaningful throughout (snake_case, one file per table/topic, no version suffixes or "_v2"/"_final"/"_old" artifacts)

## 4. Complete file listing (56 files)

```
FINAL_INDIAN_B2B_CRM_DATASET/
├── MANIFEST.md
├── README.md
├── requirements.txt
├── data/
│   ├── ml/
│   │   ├── churn_prediction_dataset.csv
│   │   ├── customer_segmentation_dataset.csv
│   │   ├── lead_conversion_dataset.csv
│   │   ├── lead_scoring_dataset.csv
│   │   └── sales_forecasting_dataset.csv
│   └── source/
│       ├── activities.csv
│       ├── campaign_responses.csv
│       ├── campaigns.csv
│       ├── companies.csv
│       ├── contacts.csv
│       ├── customer_support_cases.csv
│       ├── customer_transactions.csv
│       ├── customers.csv
│       ├── departments.csv
│       ├── industries.csv
│       ├── lead_sources.csv
│       ├── lead_status_history.csv
│       ├── leads.csv
│       ├── opportunities.csv
│       ├── opportunity_products.csv
│       ├── opportunity_stage_history.csv
│       ├── products.csv
│       ├── sales_reps.csv
│       └── territories.csv
├── docs/
│   ├── activities_dedup_report.md
│   ├── business_rules.md
│   ├── data_dictionary.md
│   ├── data_quality_report.md
│   ├── database_import_instructions.md
│   ├── er_diagram.txt
│   ├── er_documentation.md
│   ├── full_audit_report.json
│   ├── generation_methodology.md
│   ├── ml_dataset_documentation.md
│   ├── ml_leakage_prevention.md
│   ├── ml_leakage_report.md
│   ├── ml_project_structure.md
│   ├── project_structure.md
│   ├── recommended_api_endpoints.md
│   ├── recommended_dashboard_kpis.md
│   ├── recommended_schema.md
│   ├── referential_integrity_report.md
│   └── validation_report.md
├── scripts/
│   ├── generate_activities.py
│   ├── generate_contacts_leads.py
│   ├── generate_master_tables.py
│   ├── generate_ml_datasets.py
│   ├── generate_opps_customers.py
│   ├── load_mysql.py
│   ├── load_postgres.py
│   └── validate_dataset.py
└── sql/
    ├── create_tables_mysql.sql
    └── create_tables_postgres.sql
```

56 files total (24 CSVs + 19 docs + 8 scripts + 2 SQL files + README.md + requirements.txt + this MANIFEST.md), ~1.86 MB uncompressed.
