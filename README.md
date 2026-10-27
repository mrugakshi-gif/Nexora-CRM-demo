# Indian B2B CRM Synthetic Dataset

A realistic, production-style Indian B2B CRM dataset built for two purposes: training/evaluating machine-learning models (lead conversion, lead scoring, sales forecasting, customer segmentation, churn prediction) and prototyping a full CRM application (dashboards, reporting, workflows). This package contains the complete relational dataset (19 source tables), 5 derived ML-ready datasets, full documentation, SQL/loading/validation scripts, and design recommendations for a downstream app.

**Scale:** this is a 1,200-company pilot batch, generated deterministically from a fixed random seed (`20260915`). The schema and generation logic are designed to scale to a larger batch without structural changes — see [Known limitations](#known-limitations).

---

## What the dataset contains

24 CSV tables, organized in four layers:

| Layer | Tables |
|---|---|
| **Master / reference** (8) | `industries`, `territories`, `departments`, `lead_sources`, `products`, `sales_reps`, `campaigns`, `companies` |
| **Transactional** (10) | `contacts`, `leads`, `campaign_responses`, `opportunities`, `opportunity_products`, `customers`, `customer_transactions`, `customer_support_cases`, `activities` |
| **Historical / audit trail** (2) | `lead_status_history`, `opportunity_stage_history` |
| **ML-ready (derived)** (5) | `lead_conversion_dataset`, `lead_scoring_dataset`, `sales_forecasting_dataset`, `customer_segmentation_dataset`, `churn_prediction_dataset` |

`activities` is the CRM's engagement log — calls, emails, meetings, demos, follow-ups, tasks, site visits, proposal/negotiation discussions, and post-sale support follow-ups — linked to whichever of `leads` / `contacts` / `companies` / `opportunities` / `customers` the activity actually involves, plus the owning `sales_reps` rep. See [`docs/data_dictionary.md`](docs/data_dictionary.md) for its full column reference.

Full column-level detail is in [`docs/data_dictionary.md`](docs/data_dictionary.md); how the tables connect is in [`docs/er_documentation.md`](docs/er_documentation.md) and [`docs/er_diagram.txt`](docs/er_diagram.txt).

## Which data is real / public reference information

Only **company identity fields** in `companies.csv` — for the ~8% of rows flagged `name_is_real_entity = True` — reference real, publicly known Indian company names, industries, and headquarters cities (e.g. a well-known logistics company's name and city). Nothing else about those rows is real:

- No real financial figures, revenue, GSTIN, employee counts, or confidential business data of any real company appear anywhere.
- No claim of verification is made or implied for any field. The `name_is_real_entity` flag identifies only that the *name and rough public profile* were used as a realistic identity anchor — not that any downstream fact about that row (GSTIN, revenue band, address, or any CRM activity) has been checked against reality or belongs to that company in real life.
- All GSTINs, pincodes, website domains, and address details attached to real-named rows are **synthetically generated** in a valid format and are not the real company's actual registration or contact details.

## Which data is synthetic

**Everything else — 100% of it.** Specifically, always synthetic, with no real-world counterpart:

- Every contact, lead, opportunity, customer, transaction, support case, campaign, and sales rep, and all of their attributes (names, emails, phone numbers, amounts, dates, statuses, notes).
- Every interaction between a company and the fictional "CRM vendor" this dataset simulates — no real company in this dataset ever actually engaged with, bought from, or was sold to by anyone. **Do not interpret any record in this dataset as real company activity, a real transaction, or a real business relationship.**
- All 92% of `companies` rows not flagged `name_is_real_entity = True` are entirely fabricated companies (synthetic name, address, GSTIN — everything).
- All ML dataset labels, scores, and features are derived arithmetically from the synthetic CRM tables above; none reflect real outcomes.

## How the data was generated

Generation proceeded in four phases, each building only on validated output from the previous phase, with a fixed seed for full reproducibility:

1. **Master tables** (`generate_master_tables.py`) — industries, territories, departments, lead sources, products, sales reps (with manager hierarchy), campaigns, and companies (a curated real-company subset plus procedurally-named synthetic companies).
2. **Contacts & leads** (`generate_contacts_leads.py`) — contacts per company, leads with a probabilistic funnel-walk simulation (New → Contacted → Qualifying → Qualified (MQL) → Sales Qualified (SQL) → Converted/Disqualified/Dead/Nurture) that produces `lead_status_history` as a byproduct, plus campaign responses.
3. **Opportunities & customers** (`generate_opps_customers.py`) — opportunities are created only from Sales-Qualified leads, walked stochastically through a 7-stage pipeline with stage-appropriate win/loss probabilities (`opportunity_stage_history`), and customers are created **only** from Closed-Won opportunities, followed by their transaction and support-case history.
4. **ML-ready datasets** (`generate_ml_datasets.py`) — each of the 5 ML datasets is derived from the validated tables above using explicit, leakage-safe observation cutoffs (see [`docs/ml_leakage_prevention.md`](docs/ml_leakage_prevention.md)).
5. **Activities** (`generate_activities.py`) — added after the fact, run last, strictly read-only against all of the phases above: draws only existing, already-validated IDs (leads, contacts, companies, opportunities, customers, sales reps) and never modifies any other table. Uses its own dedicated random stream, seeded from the same project seed, so it never perturbs the RNG sequence (and therefore the row counts) of any earlier phase.

Full method, distributions, and realism assumptions: [`docs/generation_methodology.md`](docs/generation_methodology.md).

## How tables are related

Short version: `companies` is the hub. `contacts` and `leads` belong to a company; a lead can become an `opportunity`; an opportunity, if Closed Won, produces a `customer`; a customer accrues `customer_transactions` and `customer_support_cases`. `lead_status_history` and `opportunity_stage_history` are append-only audit trails of every stage/status change. `activities` fans in from every stage — a single activity can be tied to a lead, an opportunity, or a customer (whichever context it belongs to), always to the sales rep who performed it, and to no entity at all for a general internal task. Full FK map, cardinalities, and the complete text ER diagram: [`docs/er_documentation.md`](docs/er_documentation.md) and [`docs/er_diagram.txt`](docs/er_diagram.txt).

## How to validate the dataset

Run the master validator, which checks all 24 tables against every category described in `docs/validation_report.md` (duplicates, FK integrity, categorical values, date logic, business-rule/state-machine transitions, revenue math, ML leakage, distributions, formatting, activities-specific checks, ML-dataset-specific checks, and more). Its final report is organized into eight explicit buckets — duplicate primary keys, exact duplicate rows, repeated foreign keys (informational, never an error), invalid foreign keys, acceptable null values (informational, never an error), unacceptable null values, warnings, and errors — specifically so a repeated foreign key (e.g. many contacts sharing one `company_id`) is never misread as a duplicate-record error:

```bash
pip install -r requirements.txt
python3 scripts/validation/validate_dataset.py
```

It prints a full JSON report and exits non-zero if anything fails. See [`docs/validation_report.md`](docs/validation_report.md) for the last known-good run's results (0 unresolved violations), [`docs/data_quality_report.md`](docs/data_quality_report.md) for the narrative write-up of every issue that was found and corrected during development, [`docs/activities_dedup_report.md`](docs/activities_dedup_report.md) for `activities.csv`'s duplicate-detection method and content-variety metrics specifically, [`docs/referential_integrity_report.md`](docs/referential_integrity_report.md) for the full FK/orphan/uniqueness results, and [`docs/ml_leakage_report.md`](docs/ml_leakage_report.md) for the ML-specific leakage checks. `MANIFEST.md` at the package root carries the final row counts and a one-page data-quality summary from the same run that produced this delivery.

## How to import it into PostgreSQL or MySQL

1. Create the schema: run [`sql/create_tables_postgres.sql`](sql/create_tables_postgres.sql) or [`sql/create_tables_mysql.sql`](sql/create_tables_mysql.sql) against an empty database.
2. Load the CSVs in dependency order (master → transactional → historical → ML) using [`scripts/preprocessing/load_postgres.py`](scripts/preprocessing/load_postgres.py) or [`scripts/preprocessing/load_mysql.py`](scripts/preprocessing/load_mysql.py).
3. Full step-by-step instructions, including encoding and date-format notes: [`docs/database_import_instructions.md`](docs/database_import_instructions.md).

## How to use it for ML

Each of the 5 files in `data/ml/` is already a flat, model-ready table with an explicit `dataset_split` column (`train`/`validation`/`test`, split chronologically, never randomly) and a `label_*` column. Read [`docs/ml_dataset_documentation.md`](docs/ml_dataset_documentation.md) for the business objective, feature definitions, and an example modeling plan per dataset, and [`docs/ml_leakage_prevention.md`](docs/ml_leakage_prevention.md) before engineering any additional features — it documents exactly which source columns are safe to join in at which observation time, and which are not. A suggested repository layout for a downstream ML project is in [`docs/ml_project_structure.md`](docs/ml_project_structure.md).

## Known limitations

- **Pilot scale.** 1,200 companies, ~1,100 leads, ~200 opportunities, 48 customers. Percentage-based statistics (win rate, conversion rate, tier mix) are realistic in shape but will shift somewhat at larger scale; treat exact figures as indicative, not final.
- **Tier ceiling.** Only `Bronze`/`Silver` customer tiers appear in this batch — no closed-won deal exceeded the `Gold` (₹50L+) threshold yet; the tier logic supports `Gold`/`Platinum` and will populate them at larger scale.
- **`customer_status` has no explicit "Churned" value.** Churn is a *derived* concept (see the churn ML dataset), computed from renewal-cycle transaction gaps, not stored as a status label — this is a deliberate modeling choice, not a missing category.
- **Non-idempotent generator.** `scripts/preprocessing/generate_opps_customers.py` reads and rewrites `leads.csv`/`companies.csv` in place as part of its backfill step. If you regenerate the dataset yourself, always start from a fresh, unmodified output of the earlier phases — do not rerun this script twice against its own prior output.
- **Single-currency, single-country scope.** All monetary values are INR; there is no multi-currency or multi-country modeling.
- **No free-text fields.** There are no notes/description/email-body fields to mine for NLP — every column is structured, which keeps the dataset auditable but limits its use for text-based ML tasks.

## Ethical and privacy considerations

- **No real individuals appear anywhere.** All contact names, sales-rep names, emails, phone numbers, and LinkedIn handles are synthetic. Any resemblance to a real person is coincidental — the name pools are common Indian given/family names, not scraped from any real directory.
- **Real companies appear as identity anchors only**, per the "real/public reference" section above — never with real transactional, financial, or confidential data. Do not publish or represent any record in this dataset as documenting real business activity by a named real company.
- **Synthetic contact details are not deliverable/dialable.** Emails use a `.example` domain (reserved by RFC 2606 for documentation/testing) and are not real mailboxes; phone numbers are randomly generated within valid Indian mobile prefixes but are not verified to be unassigned — do not attempt to contact these numbers.
- **GSTINs are format-valid but fictitious.** They pass structural/checksum-shaped validation but are not registered with any tax authority; do not submit them in any real filing or KYC context.
- **Intended use:** ML training/evaluation, CRM application prototyping, teaching/demoing data engineering and CRM analytics. Not intended, and not suitable, for any use that treats its contents as evidence of real commercial relationships, real financial performance, or real individuals' data.

---

## Package contents

```
FINAL_INDIAN_B2B_CRM_DATASET/
├── MANIFEST.md                        final file listing, row counts, data-quality summary
├── README.md                          this file
├── requirements.txt
├── docs/
│   ├── data_dictionary.md             complete column-level data dictionary
│   ├── er_documentation.md            entity-relationship documentation
│   ├── er_diagram.txt                 text-based ER diagram
│   ├── generation_methodology.md      dataset-generation methodology
│   ├── business_rules.md              business rules document
│   ├── data_quality_report.md         data-quality report (issues found + fixed)
│   ├── activities_dedup_report.md     activities.csv duplicate-detection & content-variety report
│   ├── referential_integrity_report.md referential-integrity report
│   ├── validation_report.md           validation report (scripts + results)
│   ├── ml_dataset_documentation.md    ML dataset documentation
│   ├── ml_leakage_prevention.md       ML leakage-prevention rules/guidance
│   ├── ml_leakage_report.md           ML leakage report (results)
│   ├── database_import_instructions.md
│   ├── project_structure.md
│   ├── recommended_schema.md
│   ├── recommended_api_endpoints.md
│   ├── recommended_dashboard_kpis.md
│   └── ml_project_structure.md
├── sql/
│   ├── create_tables_postgres.sql     SQL table-creation script (Postgres)
│   └── create_tables_mysql.sql        SQL table-creation script (MySQL)
├── scripts/
│   ├── generate_master_tables.py      Phase 1 generator (master/reference tables)
│   ├── generate_contacts_leads.py     Phase 2 generator (contacts, leads, history)
│   ├── generate_opps_customers.py     Phase 3 generator (opportunities, customers)
│   ├── generate_ml_datasets.py        Phase 4 generator (5 ML-ready datasets)
│   ├── generate_activities.py         Phase 5 generator (activities; read-only against all prior phases)
│   ├── load_postgres.py               CSV import script (Postgres)
│   ├── load_mysql.py                  CSV import script (MySQL)
│   └── validate_dataset.py            validation script (25-category + activities end-to-end audit)
└── data/
    ├── source/  19 CRM source-table CSVs (8 master + 10 transactional + 2 historical — see below)
    └── ml/      5 ML-ready dataset CSVs
```

`MANIFEST.md` is generated fresh from the final validation run and is the authoritative record of exactly what this ZIP contains — see it for the complete file listing and row counts.
