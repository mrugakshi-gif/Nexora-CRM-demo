import os
import shutil
import sqlite3
import datetime
from sqlalchemy import inspect
from backend.database import engine
from backend import models

DB_PATH = "backend/crm.db"
CSV_DIR = "data/source"

AI_TABLES = ["chat_sessions", "chat_messages", "company_documents"]

CRM_TABLES = [
    "industries", "territories", "departments", "lead_sources",
    "products", "sales_reps", "companies", "campaigns",
    "contacts", "users", "leads", "lead_status_history",
    "campaign_responses", "opportunities", "opportunity_products",
    "opportunity_stage_history", "customers", "customer_transactions",
    "customer_support_cases", "activities"
]

def verify_csv_sources():
    print("[1] Verifying CSV sources...")
    for table in CRM_TABLES:
        csv_path = os.path.join(CSV_DIR, f"{table}.csv")
        if not os.path.isfile(csv_path):
            raise FileNotFoundError(f"Missing source CSV for table {table}: {csv_path}")
    print("    All 20 CSV sources verified.")

def backup_database() -> str:
    print("[2] Creating database backup...")
    if not os.path.isfile(DB_PATH):
        raise FileNotFoundError(f"Database not found at {DB_PATH}")
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"backend/crm_backup_{timestamp}.db"
    
    shutil.copy2(DB_PATH, backup_path)
    
    if not os.path.isfile(backup_path) or os.path.getsize(backup_path) == 0:
        raise RuntimeError(f"Backup failed or is empty: {backup_path}")
        
    print(f"    Backup created successfully: {backup_path}")
    return backup_path

def record_ai_state(conn: sqlite3.Connection) -> dict:
    print("[3] Recording AI/RAG preservation state...")
    cursor = conn.cursor()
    state = {}
    for table in AI_TABLES:
        try:
            count = cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            schema = cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table}'").fetchone()[0]
            state[table] = {"count": count, "schema": schema}
            print(f"    {table}: {count} rows")
        except Exception:
            print(f"    WARNING: AI table {table} does not exist.")
            state[table] = None
    return state

def migrate_tables(conn: sqlite3.Connection):
    print("[4] Migrating CRM tables...")
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = OFF")
    
    for table in reversed(CRM_TABLES):
        try:
            cursor.execute(f'DROP TABLE IF EXISTS "{table}"')
        except Exception as e:
            raise RuntimeError(f"Failed to drop table {table}: {e}")
            
    conn.commit()
    
    print("    Recreating SQLAlchemy schema...")
    models.Base.metadata.create_all(bind=engine)
    print("    Schema recreation complete.")
    cursor.execute("PRAGMA foreign_keys = ON")
    conn.commit()

def verify_ai_state(conn: sqlite3.Connection, before_state: dict):
    print("[5] Verifying AI/RAG preservation...")
    cursor = conn.cursor()
    for table, pre_migration in before_state.items():
        if pre_migration is None:
            continue
        try:
            count = cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            
            if count != pre_migration["count"]:
                raise RuntimeError(f"AI table {table} row count changed! Expected {pre_migration['count']}, got {count}")
            
            print(f"    {table}: {count} rows verified intact.")
        except Exception as e:
            raise RuntimeError(f"AI table verification failed for {table}: {e}")

def run_migration():
    print("============================================================")
    print("Phase D1 — Database Schema Migration")
    print("============================================================")
    
    try:
        verify_csv_sources()
        backup_path = backup_database()
        
        conn = sqlite3.connect(DB_PATH)
        ai_state = record_ai_state(conn)
        
        migrate_tables(conn)
        
        verify_ai_state(conn, ai_state)
        conn.close()
        
        print("\n============================================================")
        print("MIGRATION SUCCESSFUL")
        print("============================================================")
        
    except Exception as e:
        print("\n============================================================")
        print("MIGRATION ABORTED")
        print(f"Error: {e}")
        print("============================================================")
        import sys
        sys.exit(1)

if __name__ == "__main__":
    run_migration()
