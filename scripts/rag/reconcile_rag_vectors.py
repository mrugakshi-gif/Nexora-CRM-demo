"""
scripts/rag/reconcile_rag_vectors.py

Idempotent reconciliation script to sync missing document chunks from SQLite into ChromaDB.
Preserves all existing vectors and database records.
Never recreates collections or drops data.
"""

import os
import sys
import argparse
import sqlite3
from typing import List, Dict, Any, Tuple

# Ensure project root is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, "backend", ".env"))

from langchain_core.documents import Document
from langchain_chroma import Chroma
from backend.rag import get_embeddings


def inspect_sqlite_and_chroma(
    db_path: str, 
    chroma_dir: str
) -> Tuple[List[Dict[str, Any]], set, List[Dict[str, Any]]]:
    """
    Inspects SQLite and ChromaDB to identify chunks present in SQLite but missing from Chroma.
    Returns:
        sqlite_chunks: list of all chunks from SQLite
        chroma_chunk_ids: set of chunk_ids already indexed in Chroma
        missing_chunks: list of chunk dicts that need to be indexed
    """
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"SQLite database not found at {db_path}")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    query = """
        SELECT 
            dc.chunk_id, 
            dc.document_id, 
            cd.filename, 
            cd.title,
            cd.company_id,
            dc.chunk_index, 
            dc.section, 
            dc.subsection, 
            dc.page_number, 
            dc.source_file_type,
            dc.character_count, 
            dc.indexing_status, 
            dc.text
        FROM document_chunks dc
        JOIN company_documents cd ON dc.document_id = cd.doc_id
        ORDER BY cd.doc_id, dc.chunk_index
    """
    rows = cur.execute(query).fetchall()
    conn.close()

    sqlite_chunks = []
    for r in rows:
        sqlite_chunks.append({
            "chunk_id": r[0],
            "document_id": r[1],
            "filename": r[2],
            "title": r[3] or r[2],
            "company_id": r[4] if r[4] else "general",
            "chunk_index": r[5],
            "section": r[6] or "",
            "subsection": r[7] or "",
            "page_number": r[8] if r[8] is not None else -1,
            "source_file_type": r[9] or os.path.splitext(r[2])[1].lower(),
            "character_count": r[10],
            "indexing_status": r[11],
            "text": r[12]
        })

    # Inspect ChromaDB
    chroma_sqlite = os.path.join(chroma_dir, "chroma.sqlite3")
    chroma_chunk_ids = set()

    if os.path.exists(chroma_sqlite):
        chroma_conn = sqlite3.connect(chroma_sqlite)
        chroma_cur = chroma_conn.cursor()
        meta_rows = chroma_cur.execute(
            "SELECT string_value FROM embedding_metadata WHERE key = 'chunk_id'"
        ).fetchall()
        chroma_chunk_ids = {r[0] for r in meta_rows if r[0]}
        chroma_conn.close()

    missing_chunks = [c for c in sqlite_chunks if c["chunk_id"] not in chroma_chunk_ids]
    return sqlite_chunks, chroma_chunk_ids, missing_chunks


def reconcile_vectors(
    db_path: str = os.path.join(BASE_DIR, "backend", "crm.db"),
    chroma_dir: str = os.path.join(BASE_DIR, "chroma_db"),
    dry_run: bool = True
) -> Dict[str, Any]:
    """
    Performs idempotent reconciliation of missing chunks into ChromaDB.
    """
    sqlite_chunks, chroma_chunk_ids, missing_chunks = inspect_sqlite_and_chroma(db_path, chroma_dir)

    report = {
        "total_sqlite_chunks": len(sqlite_chunks),
        "existing_chroma_vectors": len(chroma_chunk_ids),
        "missing_chunks_count": len(missing_chunks),
        "missing_chunk_ids": [c["chunk_id"] for c in missing_chunks],
        "missing_documents": sorted(list({c["filename"] for c in missing_chunks})),
        "status": "dry_run" if dry_run else "reconciled"
    }

    if not missing_chunks:
        report["status"] = "already_in_sync"
        report["message"] = "ChromaDB vector store is already 100% synchronized with SQLite document_chunks."
        return report

    if dry_run:
        report["message"] = (
            f"DRY RUN: {len(missing_chunks)} chunks across {len(report['missing_documents'])} documents "
            f"are missing from ChromaDB and would be indexed."
        )
        return report

    # Apply mode: Embed and add documents without deleting or modifying existing vectors
    emb = get_embeddings()
    if not emb:
        raise RuntimeError("Embeddings model could not be initialized. Check GOOGLE_API_KEY.")

    vectorstore = Chroma(persist_directory=chroma_dir, embedding_function=emb)

    docs_to_index: List[Document] = []
    for c in missing_chunks:
        metadata = {
            "source": c["filename"],
            "chunk_sequence": c["chunk_index"],
            "chunk_id": c["chunk_id"],
            "parent_doc_id": c["document_id"],
            "document_name": c["title"],
            "section": c["section"],
            "subsection": c["subsection"],
            "page_number": c["page_number"],
            "source_file_type": c["source_file_type"],
            "company_id": c["company_id"]
        }
        docs_to_index.append(Document(page_content=c["text"], metadata=metadata))

    # Add new documents to existing Chroma collection using their exact chunk IDs
    chunk_ids = [c["chunk_id"] for c in missing_chunks]
    vectorstore.add_documents(docs_to_index, ids=chunk_ids)

    # Verify updated Chroma count
    _, updated_chroma_ids, remaining_missing = inspect_sqlite_and_chroma(db_path, chroma_dir)
    report["updated_chroma_vectors"] = len(updated_chroma_ids)
    report["remaining_missing_count"] = len(remaining_missing)
    report["status"] = "success" if len(remaining_missing) == 0 else "partial_success"
    report["message"] = (
        f"Successfully indexed {len(missing_chunks)} chunks into ChromaDB. "
        f"Total vectors now: {len(updated_chroma_ids)}. Remaining missing: {len(remaining_missing)}."
    )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reconcile missing SQLite chunks into ChromaDB.")
    parser.add_argument("--db-path", default=os.path.join(BASE_DIR, "backend", "crm.db"), help="Path to SQLite DB")
    parser.add_argument("--chroma-dir", default=os.path.join(BASE_DIR, "chroma_db"), help="Path to ChromaDB directory")
    parser.add_argument("--apply", action="store_true", help="Apply changes (default is dry-run)")
    args = parser.parse_args()

    result = reconcile_vectors(db_path=args.db_path, chroma_dir=args.chroma_dir, dry_run=not args.apply)
    import json
    print(json.dumps(result, indent=2))
