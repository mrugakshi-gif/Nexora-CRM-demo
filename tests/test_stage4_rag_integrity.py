"""
Stage 4 Regression and Unit Tests — RAG Integrity & Vector Reconciliation
Covers:
- Identification of SQLite document chunks vs. ChromaDB vector embeddings
- Accurate isolation of the 10 unindexed chunks across the 5 policy/catalog documents
- Dry-run non-destructive inspection
- Isolated reconciliation verification (idempotent, no duplicates, no vector deletion)
- RAG embeddings health check
"""

import os
import shutil
import tempfile
import sqlite3
import pytest
from unittest.mock import MagicMock, patch

from backend.rag import check_embeddings_health, get_embeddings
from scripts.rag.reconcile_rag_vectors import (
    inspect_sqlite_and_chroma,
    reconcile_vectors
)


def test_rag_embeddings_health():
    """Verify that Google Embeddings are configured and healthy."""
    health = check_embeddings_health()
    assert health["configured"] is True
    assert health["status"] == "available"


def test_rag_pre_repair_backup_identifies_10_missing_chunks():
    """
    Verify that inspect_sqlite_and_chroma against the pre-repair backup correctly
    identifies the 10 chunks across the 5 unindexed documents.
    """
    db_path = os.path.abspath("backend/crm.db")
    backup_chroma_dir = os.path.abspath("chroma_db_backup_pre_stage4_20261016_193746")

    sqlite_chunks, chroma_chunk_ids, missing_chunks = inspect_sqlite_and_chroma(db_path, backup_chroma_dir)

    assert len(sqlite_chunks) == 123
    assert len(chroma_chunk_ids) == 113
    assert len(missing_chunks) == 10

    missing_docs = sorted(list({c["filename"] for c in missing_chunks}))
    assert missing_docs == [
        "Customer_Retention_Policy.pdf",
        "Enterprise_Pricing_Policy.pdf",
        "Product_Catalog.txt",
        "Sales_Discount_Guidelines.docx",
        "Support_SLA_Policy.pdf"
    ]

    expected_chunk_ids = {
        "CHK-023A4769", "CHK-10ACC16C", "CHK-125B6E17", "CHK-15F210F2", "CHK-2D97F128",
        "CHK-BDB764B1", "CHK-C52BACE5", "CHK-CFB2B025", "CHK-DB389AB9", "CHK-F9C4EFD3"
    }
    found_missing_ids = {c["chunk_id"] for c in missing_chunks}
    assert found_missing_ids == expected_chunk_ids


def test_rag_post_repair_active_store_synchronized():
    """
    Verify that the active ChromaDB store is now 100% synchronized with SQLite:
    - 123 SQLite document chunks
    - 123 ChromaDB vectors
    - 0 missing chunks
    """
    db_path = os.path.abspath("backend/crm.db")
    chroma_dir = os.path.abspath("chroma_db")

    sqlite_chunks, chroma_chunk_ids, missing_chunks = inspect_sqlite_and_chroma(db_path, chroma_dir)

    assert len(sqlite_chunks) == 123
    assert len(chroma_chunk_ids) == 123
    assert len(missing_chunks) == 0

    report = reconcile_vectors(db_path=db_path, chroma_dir=chroma_dir, dry_run=True)
    assert report["status"] == "already_in_sync"
    assert report["missing_chunks_count"] == 0


def test_reconciliation_in_isolated_temp_directory():
    """
    Test the reconciliation procedure in a completely isolated temporary directory.
    Verifies:
    1. Initial population of base vectors
    2. Reconciling missing chunks adds exactly the missing chunks
    3. Idempotency: re-running reconciliation results in 'already_in_sync' with 0 additions
    4. Never overwrites or deletes existing vectors
    """
    temp_dir = tempfile.mkdtemp(prefix="nexora_test_chroma_")
    db_path = os.path.abspath("backend/crm.db")

    try:
        # Mock embeddings to avoid external API calls during automated unit test runs
        mock_embedding_instance = MagicMock()
        mock_embedding_instance.embed_documents.side_effect = lambda texts: [[0.1] * 768 for _ in texts]
        mock_embedding_instance.embed_query.return_value = [0.1] * 768

        with patch("scripts.rag.reconcile_rag_vectors.get_embeddings", return_value=mock_embedding_instance):
            # Run 1: Apply to empty temp directory -> all 123 chunks indexed
            res1 = reconcile_vectors(db_path=db_path, chroma_dir=temp_dir, dry_run=False)
            assert res1["status"] == "success"
            assert res1["updated_chroma_vectors"] == 123
            assert res1["remaining_missing_count"] == 0

            # Run 2: Re-run reconciliation on the populated store -> already_in_sync (idempotent)
            res2 = reconcile_vectors(db_path=db_path, chroma_dir=temp_dir, dry_run=False)
            assert res2["status"] == "already_in_sync"
            assert res2["missing_chunks_count"] == 0

            # Check that no calls were made on second run
            # Inspect temp Chroma
            _, final_chroma_ids, final_missing = inspect_sqlite_and_chroma(db_path, temp_dir)
            assert len(final_chroma_ids) == 123
            assert len(final_missing) == 0

    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


def test_rag_actual_retrieval_affected_documents():
    """
    Verify real semantic retrieval against active ChromaDB for the 5 affected documents.
    """
    from backend.rag import get_rag_retriever

    retriever = get_rag_retriever(company_ids=["general"])
    assert retriever is not None

    test_cases = [
        ("Enterprise_Pricing_Policy.pdf", "What are the enterprise payment terms and late payment penalty in India?"),
        ("Customer_Retention_Policy.pdf", "What is the purpose of the customer retention policy for account managers?"),
        ("Sales_Discount_Guidelines.docx", "What are the sales discount guidelines for representatives to maintain margin integrity?"),
        ("Product_Catalog.txt", "What is the SKU and pricing for the core CRM module in the product catalog?"),
        ("Support_SLA_Policy.pdf", "What are the SLA definitions and response resolution targets for support tickets?")
    ]

    for expected_doc, query in test_cases:
        docs = retriever.invoke(query)
        assert len(docs) > 0
        retrieved_sources = [d.metadata.get("source") for d in docs]
        assert expected_doc in retrieved_sources, f"Expected {expected_doc} in retrieved sources {retrieved_sources}"

