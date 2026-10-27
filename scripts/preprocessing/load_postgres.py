#!/usr/bin/env python3
"""
Load the Indian B2B CRM synthetic dataset's CSVs into PostgreSQL.

Usage:
    python3 load_postgres.py --host localhost --db crm_dataset \\
        --user myuser --password mypass --data-dir /path/to/package/data

Requires: sql/create_tables_postgres.sql to have already been run against
the target database (see docs/database_import_instructions.md).
"""
import argparse
import csv
import sys
from pathlib import Path

try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:
    sys.exit("Missing dependency: run `pip install -r requirements.txt` first (needs psycopg2-binary).")

# Load order matters: parents before children (see docs/er_documentation.md
# "Generation / load order").
TABLE_ORDER = [
    ("source", "industries"), ("source", "territories"), ("source", "departments"),
    ("source", "lead_sources"), ("source", "products"), ("source", "sales_reps"),
    ("source", "campaigns"), ("source", "companies"), ("source", "contacts"),
    ("source", "leads"), ("source", "lead_status_history"), ("source", "campaign_responses"),
    ("source", "opportunities"), ("source", "opportunity_products"),
    ("source", "opportunity_stage_history"), ("source", "customers"),
    ("source", "customer_transactions"), ("source", "customer_support_cases"),
    ("source", "activities"),
    ("ml", "lead_conversion_dataset"), ("ml", "lead_scoring_dataset"),
    ("ml", "sales_forecasting_dataset"), ("ml", "customer_segmentation_dataset"),
    ("ml", "churn_prediction_dataset"),
]

# Columns that must be cast from the CSV's "True"/"False" strings to native
# booleans (Postgres will otherwise accept the strings directly, but this
# keeps behavior identical and explicit between the two loaders).
BOOLEAN_COLUMNS = {
    "sales_reps": {"is_active"},
    "campaigns": set(),
    "companies": {"name_is_real_entity"},
    "contacts": {"is_primary_contact", "is_decision_maker"},
    "products": {"is_active"},
    "industries": {"is_active"},
    "lead_conversion_dataset": {"campaign_sourced_flag", "contact_is_decision_maker",
                                 "estimated_budget_known", "rep_assigned_flag",
                                 "is_duplicate_lead", "label_converted"},
    "lead_scoring_dataset": {"campaign_sourced_flag", "contact_is_decision_maker", "label_converted"},
    "churn_prediction_dataset": {"label_churned_within_horizon"},
}


def coerce(value, col, table):
    if value == "":
        return None
    if col in BOOLEAN_COLUMNS.get(table, set()):
        return value == "True"
    return value


def load_table(conn, data_dir: Path, subdir: str, table: str):
    path = data_dir / subdir / f"{table}.csv"
    if not path.exists():
        print(f"  SKIP {table}: {path} not found")
        return
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames
        rows = [tuple(coerce(row[c], c, table) for c in cols) for row in reader]
    if not rows:
        print(f"  {table}: 0 rows")
        return
    col_list = ", ".join(f'"{c}"' for c in cols)
    sql = f'INSERT INTO "{table}" ({col_list}) VALUES %s'
    with conn.cursor() as cur:
        execute_values(cur, sql, rows, page_size=1000)
    conn.commit()
    print(f"  {table}: {len(rows)} rows")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--host", default="localhost")
    ap.add_argument("--port", type=int, default=5432)
    ap.add_argument("--db", required=True)
    ap.add_argument("--user", required=True)
    ap.add_argument("--password", required=True)
    ap.add_argument("--data-dir", required=True, help="Path to the package's data/ directory")
    args = ap.parse_args()

    data_dir = Path(args.data_dir)
    conn = psycopg2.connect(host=args.host, port=args.port, dbname=args.db,
                             user=args.user, password=args.password)
    print(f"Connected to postgres://{args.user}@{args.host}:{args.port}/{args.db}")
    try:
        for subdir, table in TABLE_ORDER:
            load_table(conn, data_dir, subdir, table)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    print("Done.")


if __name__ == "__main__":
    main()
