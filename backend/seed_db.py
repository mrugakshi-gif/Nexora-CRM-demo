"""
Phase D1 — Idempotent CRM Database Seeder
==========================================

Imports all 20 source CSV files into the SQLite database in dependency order.

Design principles:
  1. INSERT OR IGNORE: running this script twice produces the same result —
     existing rows are never overwritten or duplicated.
  2. Source PKs are preserved exactly (COMP-000001, LEAD-000001, etc.).
  3. Parent tables are imported before child tables (topological order).
  4. AI/RAG tables (chat_sessions, chat_messages, company_documents) are
     created by SQLAlchemy but never touched by this seeder.
  5. After import, row counts are compared to CSV counts and any mismatch
     is reported as a WARNING (not a fatal error).

Usage (run from project root):
    python -m backend.seed_db
    # or
    python backend/seed_db.py
"""

import os
import sys
import sqlite3
import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DIR  = os.path.join(BASE_DIR, "data", "source")
DB_PATH     = os.path.join(BASE_DIR, "backend", "crm.db")

# Import order respects FK dependencies (parents always before children)
IMPORT_ORDER = [
    # ── Reference / lookup tables (no FK dependencies) ──────────────────
    ("industries.csv",              "industries"),
    ("territories.csv",             "territories"),
    ("departments.csv",             "departments"),
    ("lead_sources.csv",            "lead_sources"),
    ("products.csv",                "products"),
    # ── Org-chart ────────────────────────────────────────────────────────
    ("sales_reps.csv",              "sales_reps"),
    # ── Core CRM masters ─────────────────────────────────────────────────
    ("companies.csv",               "companies"),
    ("campaigns.csv",               "campaigns"),
    ("contacts.csv",                "contacts"),
    ("users.csv",                   "users"),
    # ── Lead funnel ──────────────────────────────────────────────────────
    ("leads.csv",                   "leads"),
    ("lead_status_history.csv",     "lead_status_history"),
    ("campaign_responses.csv",      "campaign_responses"),
    # ── Opportunity funnel ───────────────────────────────────────────────
    ("opportunities.csv",           "opportunities"),
    ("opportunity_products.csv",    "opportunity_products"),
    ("opportunity_stage_history.csv","opportunity_stage_history"),
    # ── Post-conversion ──────────────────────────────────────────────────
    ("customers.csv",               "customers"),
    ("customer_transactions.csv",   "customer_transactions"),
    ("customer_support_cases.csv",  "customer_support_cases"),
    # ── Cross-cutting ────────────────────────────────────────────────────
    ("activities.csv",              "activities"),
]

# Columns that SQLite stores as TEXT but whose values are pandas booleans
# (True/False).  We convert them to 1/0 for consistency.
BOOL_COLUMNS = {
    "industries":  ["is_active"],
    "products":    ["is_active"],
    "companies":   ["name_is_real_entity"],
    "contacts":    ["is_primary_contact", "is_decision_maker"],
    "sales_reps":  ["is_active"],
    "users":       ["is_active"],
}

# Columns that pandas reads as float (because of NaN rows) but should be
# stored as nullable INTEGER.
INT_NULLABLE_COLUMNS = {
    "companies": ["founded_year"],
    "opportunity_products": ["quantity"],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean_df(df: pd.DataFrame, table_name: str) -> pd.DataFrame:
    """Standardise a CSV dataframe before insertion."""
    # Convert all pandas missing types to Python None
    df = df.replace({pd.NA: None, np.nan: None})
    df = df.where(pd.notnull(df), None)

    # Boolean normalisation → 1 / 0 / NULL
    for col in BOOL_COLUMNS.get(table_name, []):
        if col in df.columns:
            df[col] = df[col].map(
                lambda v: 1 if v in (True, 1, "True", "1", "true") else
                          (0 if v in (False, 0, "False", "0", "false") else None)
            )

    # Nullable integer normalisation
    for col in INT_NULLABLE_COLUMNS.get(table_name, []):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    return df


def _get_pk_column(table_name: str) -> str:
    """Return the primary-key column name for a table."""
    pk_map = {
        "industries":               "industry_id",
        "territories":              "territory_id",
        "departments":              "department_id",
        "lead_sources":             "lead_source_id",
        "products":                 "product_id",
        "sales_reps":               "rep_id",
        "companies":                "company_id",
        "campaigns":                "campaign_id",
        "contacts":                 "contact_id",
        "users":                    "user_id",
        "leads":                    "lead_id",
        "lead_status_history":      "history_id",
        "campaign_responses":       "response_id",
        "opportunities":            "opportunity_id",
        "opportunity_products":     "opportunity_product_id",
        "opportunity_stage_history":"history_id",
        "customers":                "customer_id",
        "customer_transactions":    "transaction_id",
        "customer_support_cases":   "case_id",
        "activities":               "activity_id",
    }
    return pk_map.get(table_name, "id")


# ---------------------------------------------------------------------------
# Core seeder
# ---------------------------------------------------------------------------

def ensure_schema(conn: sqlite3.Connection) -> None:
    """
    Ensure SQLAlchemy schema exists. 
    NOTE: Destructive schema migration (dropping old tables) is now 
    handled by migrate_db.py. This function just ensures tables exist.
    """
    try:
        from backend.database import engine
        from backend import models  # noqa: F401
        models.Base.metadata.create_all(bind=engine)
        print("  [schema] All SQLAlchemy tables ensured.")
    except Exception as exc:
        print(f"  [schema] WARNING: Could not run SQLAlchemy create_all: {exc}")



def seed_table(conn: sqlite3.Connection, csv_file: str, table_name: str) -> dict:
    """Import one CSV into one SQLite table using INSERT OR IGNORE."""
    csv_path = os.path.join(SOURCE_DIR, csv_file)

    if not os.path.exists(csv_path):
        return {"table": table_name, "csv_rows": 0, "inserted": 0,
                "skipped": 0, "status": "CSV_NOT_FOUND"}

    df = pd.read_csv(csv_path, low_memory=False)
    csv_rows = len(df)
    df = _clean_df(df, table_name)

    cursor = conn.cursor()

    # Check how many rows already exist
    cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
    existing_before = cursor.fetchone()[0]

    # Build INSERT OR IGNORE statement
    columns      = list(df.columns)
    placeholders = ", ".join(["?" for _ in columns])
    col_names    = ", ".join([f'"{c}"' for c in columns])
    sql          = f'INSERT OR IGNORE INTO "{table_name}" ({col_names}) VALUES ({placeholders})'

    # Execute row by row (small datasets — fine for seeding)
    inserted = 0
    errors   = 0
    for _, row in df.iterrows():
        values = []
        for v in row:
            if pd.isna(v) or v is pd.NA:
                values.append(None)
            elif hasattr(v, "item"):          # numpy scalar → Python native
                values.append(v.item())
            else:
                values.append(v)
        try:
            cursor.execute(sql, values)
            if cursor.rowcount > 0:
                inserted += 1
        except sqlite3.IntegrityError as e:
            err_msg = str(e)
            if "UNIQUE constraint failed" in err_msg or "PRIMARY KEY must be unique" in err_msg:
                pass  # Duplicate PK — expected on re-runs
            else:
                errors += 1
                if errors <= 3:
                    print(f"    [warn] Integrity error in {table_name}: {err_msg}")
        except Exception as exc:
            errors += 1
            if errors <= 3:
                print(f"    [warn] Row insert error in {table_name}: {exc}")

    conn.commit()

    cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
    existing_after = cursor.fetchone()[0]
    skipped = csv_rows - inserted

    status = "OK"
    if errors > 0:
        status = f"ERRORS:{errors}"
    elif existing_after < csv_rows:
        status = "PARTIAL"

    return {
        "table":    table_name,
        "csv_rows": csv_rows,
        "inserted": inserted,
        "skipped":  skipped,
        "db_total": existing_after,
        "status":   status,
    }


def seed_database(verbose: bool = True) -> list:
    """
    Main entry point.  Returns a list of result dicts (one per table).
    """
    if not os.path.exists(DB_PATH):
        print(f"  [seed] Database not found at {DB_PATH}. It will be created.")

    conn = sqlite3.connect(DB_PATH)

    # Ensure FK pragma is active for the connection (informational — SQLite
    # does not enforce FKs by default, but we want to know if violations exist)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")

    print("=" * 60)
    print("Phase D1 — CRM Database Seeder")
    print(f"  DB : {DB_PATH}")
    print(f"  CSV: {SOURCE_DIR}")
    print("=" * 60)

    # Ensure all SQLAlchemy-managed tables exist
    ensure_schema(conn)

    # Disable FKs during bulk insert to allow forward references
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = OFF")

    results = []
    total_inserted = 0

    for csv_file, table_name in IMPORT_ORDER:
        if verbose:
            print(f"  [seed] {table_name:<35} ", end="", flush=True)

        result = seed_table(conn, csv_file, table_name)
        results.append(result)
        total_inserted += result["inserted"]

        if verbose:
            s = result["status"]
            print(
                f"CSV:{result['csv_rows']:>5}  "
                f"inserted:{result['inserted']:>5}  "
                f"skipped:{result['skipped']:>5}  "
                f"db_total:{result.get('db_total', '?'):>5}  "
                f"[{s}]"
            )

    conn.close()

    # ── Summary ─────────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print("SEED SUMMARY")
    print("=" * 60)
    problems = [r for r in results if r["status"] not in ("OK", "CSV_NOT_FOUND")]
    if not problems:
        print(f"  ✅  All {len(results)} tables seeded successfully.")
        print(f"  ✅  Total rows inserted this run: {total_inserted}")
    else:
        print(f"  ⚠️   {len(problems)} table(s) had issues:")
        for p in problems:
            print(f"       {p['table']}: {p['status']}")

    # ── Row-count verification ───────────────────────────────────────────
    print()
    print("ROW COUNT VERIFICATION (CSV vs DB)")
    print("-" * 60)
    mismatches = []
    for r in results:
        db_total = r.get("db_total", "?")
        csv_rows = r["csv_rows"]
        match    = "✅" if db_total == csv_rows else "⚠️ MISMATCH"
        if db_total != csv_rows:
            mismatches.append(r)
        print(f"  {r['table']:<35} CSV:{csv_rows:>5}  DB:{db_total!s:>5}  {match}")

    if mismatches:
        print()
        print("MISMATCH DETAIL:")
        for m in mismatches:
            diff = m.get("db_total", 0) - m["csv_rows"]
            print(f"  {m['table']}: DB has {diff:+d} rows vs CSV")
    else:
        print()
        print("  ✅  All row counts match.")

    return results


if __name__ == "__main__":
    # Allow running from project root: python -m backend.seed_db
    # or directly:                     python backend/seed_db.py
    if os.getcwd() != BASE_DIR:
        os.chdir(BASE_DIR)
    seed_database()

    # Seed approved synthetic demo RAG documents and chunks (non-blocking, safe)
    try:
        from backend.seed_rag import run_seed_rag_safely
        print("\n" + "=" * 60)
        print("Phase D4 — Seeding Synthetic Demo Documents for RAG")
        print("=" * 60)
        run_seed_rag_safely(verbose=True)
    except Exception as _rag_exc:
        print(f"  [warn] Demo RAG seeding skipped: {_rag_exc}")

