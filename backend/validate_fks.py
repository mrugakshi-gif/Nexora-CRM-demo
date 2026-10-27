import sqlite3

import os

def validate_fks(db_path=None):
    if not db_path:
        db_path = os.environ.get("CRM_DB_URL", "sqlite:///backend/crm.db").replace("sqlite:///", "")
    print("============================================================")
    print("Phase D1 — Exhaustive FK Validation")
    print("============================================================")
    from backend.migrate_db import CRM_TABLES
    tables = CRM_TABLES
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    total_orphans = 0
    checked_relationships = 0
    
    for table in tables:
        fks = cursor.execute(f"PRAGMA foreign_key_list('{table}')").fetchall()
        for fk in fks:
            parent_table = fk[2]
            child_col = fk[3]
            parent_col = fk[4]
            
            if not parent_col:
                pk_info = cursor.execute(f"PRAGMA table_info('{parent_table}')").fetchall()
                parent_col = next((c[1] for c in pk_info if c[5] == 1), None)
                if not parent_col:
                    print(f"Warning: Could not determine primary key for parent table {parent_table}")
                    continue
            
            query = f"""
                SELECT COUNT(*) FROM "{table}" child
                WHERE child."{child_col}" IS NOT NULL
                AND NOT EXISTS (
                    SELECT 1 FROM "{parent_table}" parent WHERE parent."{parent_col}" = child."{child_col}"
                )
            """
            
            try:
                orphan_count = cursor.execute(query).fetchone()[0]
                print(f"[{table}.{child_col} -> {parent_table}.{parent_col}]: {orphan_count} orphans")
                total_orphans += orphan_count
                checked_relationships += 1
            except Exception as e:
                print(f"Error checking [{table}.{child_col} -> {parent_table}.{parent_col}]: {e}")
                
    conn.close()
    
    print("============================================================")
    print(f"Total relationships checked: {checked_relationships}")
    print(f"Total orphans found across all tables: {total_orphans}")
    print("============================================================")
    
    if total_orphans > 0:
        raise RuntimeError(f"FK Validation Failed! Found {total_orphans} orphan records.")
    
    return total_orphans

if __name__ == "__main__":
    validate_fks()
