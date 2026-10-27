import sqlite3
import shutil
import datetime
import os

DB_PATH = "backend/crm.db"

def backup_database() -> str:
    print("[1] Creating database backup before D2.5 migration...")
    if not os.path.isfile(DB_PATH):
        raise FileNotFoundError(f"Database not found at {DB_PATH}")
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"backend/crm_backup_d2_5_{timestamp}.db"
    
    shutil.copy2(DB_PATH, backup_path)
    print(f"    Backup created successfully: {backup_path}")
    return backup_path

def add_firebase_uid(conn: sqlite3.Connection):
    print("[2] Adding firebase_uid column to users table...")
    cursor = conn.cursor()
    
    # Check if column already exists
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if "firebase_uid" in columns:
        print("    Column 'firebase_uid' already exists. Skipping.")
        return

    cursor.execute("ALTER TABLE users ADD COLUMN firebase_uid VARCHAR;")
    cursor.execute("CREATE UNIQUE INDEX ix_users_firebase_uid ON users (firebase_uid);")
    conn.commit()
    print("    Successfully added firebase_uid column.")
    
def verify_users_count(conn: sqlite3.Connection):
    print("[3] Verifying users table integrity...")
    cursor = conn.cursor()
    count = cursor.execute("SELECT COUNT(*) FROM users;").fetchone()[0]
    
    if count != 81:
        raise RuntimeError(f"Data loss detected! Expected 81 users, got {count}")
    print(f"    Verified 81 users intact.")

def run():
    try:
        backup_path = backup_database()
        
        conn = sqlite3.connect(DB_PATH)
        add_firebase_uid(conn)
        verify_users_count(conn)
        conn.close()
        
        print("\n============================================================")
        print("D2.5 DATABASE MIGRATION SUCCESSFUL")
        print("============================================================")
        print("Rollback instructions:")
        print(f"To rollback, copy {backup_path} over {DB_PATH}")
    except Exception as e:
        print("\n============================================================")
        print("MIGRATION FAILED")
        print(f"Error: {e}")
        print("============================================================")
        import sys
        sys.exit(1)

if __name__ == "__main__":
    run()
