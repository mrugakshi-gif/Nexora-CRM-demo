# Database Import Instructions

## Prerequisites

```bash
pip install -r requirements.txt
```

You need a running PostgreSQL (≥ 12) or MySQL (≥ 8) instance and a database already created (e.g. `createdb crm_dataset` for Postgres, `CREATE DATABASE crm_dataset;` for MySQL).

## Step 1 — Create the schema

**PostgreSQL:**
```bash
psql -h localhost -U <user> -d crm_dataset -f sql/create_tables_postgres.sql
```

**MySQL:**
```bash
mysql -h localhost -u <user> -p crm_dataset < sql/create_tables_mysql.sql
```

Both scripts create all 24 tables (19 source + 5 ML-ready) in dependency order, with primary keys, foreign keys, and check constraints on the categorical enum columns. They are idempotent (`DROP TABLE IF EXISTS ... CASCADE` at the top) — safe to re-run against the same database.

## Step 2 — Load the CSVs

Loading must follow the same dependency order the schema was created in (parents before children), or foreign-key constraints will reject child rows. Use the provided Python loaders, which handle this automatically and cast the CSV's `True`/`False` strings to native booleans and blank strings to `NULL`:

**PostgreSQL** (uses `psycopg2` and native `COPY` for speed):
```bash
python3 scripts/preprocessing/load_postgres.py --host localhost --db crm_dataset --user <user> --password <password> --data-dir data
```

**MySQL** (uses `mysql-connector-python` and batched `INSERT`):
```bash
python3 scripts/preprocessing/load_mysql.py --host localhost --db crm_dataset --user <user> --password <password> --data-dir data
```

Both accept `--dsn`/connection-string style overrides — run with `--help` for the full option list. `--data-dir` should point at the `data/` folder containing `source/` and `ml/` subfolders (as shipped in this package).

## Step 3 — Verify the load

```sql
-- row counts should match docs/data_quality_report.md §3
SELECT 'companies', count(*) FROM companies
UNION ALL SELECT 'leads', count(*) FROM leads
UNION ALL SELECT 'opportunities', count(*) FROM opportunities
UNION ALL SELECT 'customers', count(*) FROM customers;
```

Or re-run the Python validator directly against the CSVs (independent of the database) at any time: `python3 scripts/validation/validate_dataset.py`.

## Notes on encoding, dates, and NULL handling

- All CSVs are UTF-8 (needed for Indian names/scripts in a few free-text fields and the ₹ symbol in `companies.annual_revenue_band_inr`). Ensure your client encoding matches (`SET client_encoding = 'UTF8';` in Postgres; `SET NAMES utf8mb4;` in MySQL — the MySQL DDL already defaults every table to `utf8mb4`).
- Timestamps are `YYYY-MM-DD HH:MM:SS` (no timezone — treat as naive/local, since this is a single-region synthetic dataset); date-only columns are `YYYY-MM-DD`. Both loaders parse these with `datetime.strptime`, matching the exact format the generators wrote.
- An empty CSV cell always means SQL `NULL`, never an empty string — the loaders convert `""` to `None` before binding parameters. This matters for every optional FK column (e.g. `leads.campaign_id`), or a `''` value would silently violate the foreign-key constraint instead of being accepted as "no campaign."
- Booleans (`is_active`, `is_primary_contact`, `is_decision_maker`, `name_is_real_entity`, etc.) are the literal strings `"True"`/`"False"` in the CSVs; the loaders cast them to native `BOOLEAN`/`TINYINT(1)`.

## Loading the ML datasets

The 5 files in `data/ml/` load the same way, into tables that carry foreign keys back into the source tables (`lead_id`, `customer_id`, `department_id`) purely for traceability — they are not meant to be queried as if they were another source of truth. Load them last, after all 19 source tables, since their FKs depend on the source tables already existing.

## If you change the schema

If you extend the schema (e.g. add a `notes` column, or the recommended additions in `docs/recommended_schema.md`), update `sql/create_tables_*.sql` first, then re-run `scripts/validation/validate_dataset.py` against the CSVs before loading — the validator checks the CSVs independently of any database, so it will catch a data/schema mismatch before you hit a load-time constraint violation.
