"""
Tests for idempotent demo RAG seeding and graceful startup fallback.
"""
import pytest
from unittest.mock import patch, MagicMock
from backend.seed_rag import seed_demo_rag, run_seed_rag_safely


def test_seed_demo_rag_idempotent_no_duplicates():
    """Verify that calling run_seed_rag_safely repeatedly is completely safe and idempotent."""
    res1 = run_seed_rag_safely(verbose=False)
    assert res1["status"] in ("OK", "DEGRADED")

    res2 = run_seed_rag_safely(verbose=False)
    assert res2["status"] in ("OK", "DEGRADED")
    # On the second call, no new documents should be added
    assert res2.get("indexed_docs", 0) == 0


def test_seed_demo_rag_graceful_missing_api_key():
    """Verify that when GOOGLE_API_KEY is not provided, seed_demo_rag still succeeds in creating SQLite rows."""
    with patch("backend.seed_rag.get_embeddings", return_value=None):
        res = seed_demo_rag(verbose=False)
        assert res["status"] == "OK"
        # Should gracefully skip or process without raising exceptions
        assert "indexed_docs" in res
