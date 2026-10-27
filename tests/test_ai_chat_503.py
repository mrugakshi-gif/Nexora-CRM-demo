import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from backend.main import app
from backend.deps import get_current_user
from backend.models import User
from backend.ai_agent import process_chat_query, is_transient_error


class MockGoogleAPIError(Exception):
    def __init__(self, code=503, status="UNAVAILABLE", message="This model is currently experiencing high demand."):
        self.code = code
        self.status = status
        self.message = message
        self.is_retryable = True
        super().__init__(f"{code} {status}. {message}")


@pytest.fixture
def mock_admin_user():
    return User(
        user_id="U-TEST-CHAT-ADMIN",
        email="chatadmin@example.com",
        role="Admin",
        is_active=True,
    )


@pytest.fixture
def client(mock_admin_user):
    app.dependency_overrides[get_current_user] = lambda: mock_admin_user
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.pop(get_current_user, None)


def test_process_chat_query_transient_503_returns_clean_message():
    mock_agent = MagicMock()
    mock_agent.invoke.side_effect = MockGoogleAPIError(
        code=503,
        status="UNAVAILABLE",
        message="This model is currently experiencing high demand. Spikes in demand are usually temporary."
    )

    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

    with patch("langchain.agents.create_agent", return_value=mock_agent), \
         patch("backend.ai_agent.get_llm", return_value=MagicMock()), \
         patch("time.sleep"):  # no delay in tests
        result = process_chat_query(
            query="Hello, list recent opportunities",
            session=mock_db,
            user_id="U-TEST-CHAT-ADMIN",
            role="Admin",
            chat_session_id="SESS-TEST1"
        )

        assert "temporarily unavailable" in result.lower()
        assert "high demand" in result.lower()
        # Verify bounded retry occurred (initial attempt + 2 retries = 3 calls)
        assert mock_agent.invoke.call_count == 3
        # Verify no raw Python tracebacks or dict dumps leaked
        assert "traceback" not in result.lower()
        assert "{'error':" not in result


def test_process_chat_query_recovers_on_retry():
    mock_agent = MagicMock()
    mock_agent.invoke.side_effect = [
        MockGoogleAPIError(code=503, status="UNAVAILABLE"),
        {"messages": [MagicMock(content="Here are your top leads: Tech Mahindra, Infosys.")]}
    ]

    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

    with patch("langchain.agents.create_agent", return_value=mock_agent), \
         patch("backend.ai_agent.get_llm", return_value=MagicMock()), \
         patch("time.sleep"):
        result = process_chat_query(
            query="top leads",
            session=mock_db,
            user_id="U-TEST-CHAT-ADMIN",
            role="Admin",
            chat_session_id="SESS-TEST2"
        )

        assert mock_agent.invoke.call_count == 2
        assert "Tech Mahindra" in result


def test_chat_endpoint_graceful_response_on_503(client):
    mock_agent = MagicMock()
    mock_agent.invoke.side_effect = MockGoogleAPIError(code=503, status="UNAVAILABLE")

    with patch("langchain.agents.create_agent", return_value=mock_agent), \
         patch("backend.ai_agent.get_llm", return_value=MagicMock()), \
         patch("time.sleep"):
        response = client.post(
            "/api/chat",
            json={"role": "user", "content": "Tell me about pipeline"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "assistant"
        assert "temporarily unavailable" in data["content"].lower()
        assert "high demand" in data["content"].lower()
        assert "{'error':" not in data["content"]
