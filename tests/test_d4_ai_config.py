import os
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

def test_health_check_no_api_key():
    with patch.dict(os.environ, {}, clear=True):
        response = client.get("/api/chat/health")
        assert response.status_code == 200
        data = response.json()
        assert data["llm"]["configured"] is False
        assert data["llm"]["status"] == "unavailable"
        assert data["embeddings"]["configured"] is False
        assert data["embeddings"]["status"] == "unavailable"
        assert data["vector_store"]["configured"] is False
        assert data["vector_store"]["status"] == "unavailable"

@patch("backend.ai_agent.ChatGoogleGenerativeAI")
@patch("backend.rag.GoogleGenerativeAIEmbeddings")
@patch("backend.routers.chat.get_vector_store")
def test_health_check_with_api_key_success(mock_vs, mock_emb, mock_llm):
    mock_llm.return_value = MagicMock()
    mock_emb.return_value = MagicMock()
    mock_vs.return_value = MagicMock()
    
    with patch.dict(os.environ, {"GOOGLE_API_KEY": "fake_key"}):
        response = client.get("/api/chat/health")
        assert response.status_code == 200
        data = response.json()
        assert data["llm"]["configured"] is True
        assert data["llm"]["status"] == "available"
        assert data["embeddings"]["configured"] is True
        assert data["embeddings"]["status"] == "available"
        assert data["vector_store"]["status"] == "available"

@patch("backend.ai_agent.ChatGoogleGenerativeAI")
@patch("backend.rag.GoogleGenerativeAIEmbeddings")
def test_health_check_with_api_key_failure(mock_emb, mock_llm):
    mock_llm.side_effect = Exception("Invalid API key")
    mock_emb.side_effect = Exception("Invalid API key")
    
    with patch.dict(os.environ, {"GOOGLE_API_KEY": "fake_key"}):
        response = client.get("/api/chat/health")
        assert response.status_code == 200
        data = response.json()
        assert data["llm"]["configured"] is True
        assert data["llm"]["status"] == "error"
        assert data["embeddings"]["configured"] is True
        assert data["embeddings"]["status"] == "error"
        assert data["vector_store"]["status"] == "unavailable"
