import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "crm.db")

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Add new columns to company_documents
    columns_to_add = [
        ("title", "VARCHAR"),
        ("file_type", "VARCHAR"),
        ("file_size", "INTEGER"),
        ("processing_status", "VARCHAR DEFAULT 'Uploaded'"),
        ("chunk_count", "INTEGER DEFAULT 0"),
        ("index_status", "VARCHAR")
    ]
    
    for col_name, col_type in columns_to_add:
        try:
            cursor.execute(f"ALTER TABLE company_documents ADD COLUMN {col_name} {col_type}")
            print(f"Added column {col_name} to company_documents.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print(f"Column {col_name} already exists.")
            else:
                print(f"Error adding {col_name}: {e}")
                
    # 2. Create document_chunks table
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS document_chunks (
        chunk_id VARCHAR PRIMARY KEY,
        document_id VARCHAR REFERENCES company_documents(doc_id) ON DELETE CASCADE,
        chunk_index INTEGER,
        text TEXT,
        page_number INTEGER,
        character_count INTEGER,
        token_count INTEGER,
        indexing_status VARCHAR DEFAULT 'Pending',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """
    cursor.execute(create_table_sql)
    print("Created document_chunks table.")
    
    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
