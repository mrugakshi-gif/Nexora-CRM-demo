import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from backend.main import app
from backend.deps import get_current_active_user
from backend.models import User
from backend.services.ai_email_generator import (
    AIEmailGenerator,
    AIProviderUnavailableError,
    AIProviderConfigError,
    is_transient_error,
)
from langchain_core.messages import AIMessage


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
        user_id="U-TEST-ADMIN",
        email="admin@example.com",
        role="Admin",
        is_active=True,
    )


@pytest.fixture
def client(mock_admin_user):
    app.dependency_overrides[get_current_active_user] = lambda: mock_admin_user
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.pop(get_current_active_user, None)


def test_is_transient_error_detection():
    # 1. Error with code 503
    err_503 = MockGoogleAPIError(code=503, status="UNAVAILABLE")
    assert is_transient_error(err_503) is True

    # 2. Error with code 429
    err_429 = MockGoogleAPIError(code=429, status="RESOURCE_EXHAUSTED", message="Rate limit exceeded")
    assert is_transient_error(err_429) is True

    # 3. Generic Exception containing upstream 503 demand text
    err_text = Exception("503 UNAVAILABLE: This model is currently experiencing high demand. Spikes in demand are usually temporary.")
    assert is_transient_error(err_text) is True

    # 4. Standard non-transient error
    err_val = ValueError("Invalid input syntax")
    assert is_transient_error(err_val) is False


def test_ai_email_generator_503_bounded_retry_and_error():
    mock_llm = MagicMock()
    mock_llm.invoke.side_effect = MockGoogleAPIError(
        code=503,
        status="UNAVAILABLE",
        message="This model is currently experiencing high demand. Spikes in demand are usually temporary."
    )

    with patch("backend.services.ai_email_generator.get_llm", return_value=mock_llm):
        generator = AIEmailGenerator()
        with pytest.raises(AIProviderUnavailableError) as exc_info:
            generator.generate_email(
                alert_type="High Priority Support Alert",
                context={"ticket_id": "T-123"},
                recipient_name="Support Team",
                max_retries=1,
                retry_delay=0.01  # fast test
            )

        assert "high demand" in str(exc_info.value).lower()
        # Verify bounded retry executed exactly 2 times (1 initial + 1 retry)
        assert mock_llm.invoke.call_count == 2


def test_ai_email_generator_recovers_on_retry():
    mock_llm = MagicMock()
    # First call fails with 503, second call succeeds with valid JSON
    mock_llm.invoke.side_effect = [
        MockGoogleAPIError(code=503, status="UNAVAILABLE"),
        AIMessage(content='{"subject": "Alert Resolved", "text_body": "Issue resolved.", "html_body": "<p>Issue resolved.</p>"}')
    ]

    with patch("backend.services.ai_email_generator.get_llm", return_value=mock_llm):
        generator = AIEmailGenerator()
        result = generator.generate_email(
            alert_type="High Priority Support Alert",
            context={"ticket_id": "T-123"},
            recipient_name="Support Team",
            max_retries=1,
            retry_delay=0.01
        )

        assert mock_llm.invoke.call_count == 2
        assert result["subject"] == "Alert Resolved"
        assert result["text_body"] == "Issue resolved."


def test_ai_email_generator_success_first_attempt():
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(
        content='{"subject": "Urgent Ticket", "text_body": "Please review ticket.", "html_body": "<p>Please review ticket.</p>"}'
    )

    with patch("backend.services.ai_email_generator.get_llm", return_value=mock_llm):
        generator = AIEmailGenerator()
        result = generator.generate_email(
            alert_type="High Priority Support Alert",
            context={"ticket_id": "T-999"},
            recipient_name="Admin"
        )

        assert mock_llm.invoke.call_count == 1
        assert result["subject"] == "Urgent Ticket"
        assert result["text_body"] == "Please review ticket."
        assert result["html_body"] == "<p>Please review ticket.</p>"


def test_generate_endpoint_returns_503_on_upstream_unavailable(client):
    mock_llm = MagicMock()
    mock_llm.invoke.side_effect = MockGoogleAPIError(code=503, status="UNAVAILABLE")

    with patch("backend.services.ai_email_generator.get_llm", return_value=mock_llm):
        response = client.post(
            "/api/email/generate",
            json={
                "alert_type": "High Priority Support Alert",
                "context": {"ticket_id": "T-101", "priority": "P1"},
                "recipient_name": "Admin"
            }
        )

        assert response.status_code == 503
        data = response.json()
        assert "detail" in data
        assert "high demand" in data["detail"].lower()
        # Verify no raw python tracebacks or dict dumps leaked
        assert "traceback" not in data["detail"].lower()
        assert "{'error':" not in data["detail"]


def test_generate_endpoint_success(client):
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(
        content='{"subject": "Opportunity Closing", "text_body": "Deal closing soon.", "html_body": "<p>Deal closing soon.</p>"}'
    )

    with patch("backend.services.ai_email_generator.get_llm", return_value=mock_llm):
        response = client.post(
            "/api/email/generate",
            json={
                "alert_type": "Opportunity Closing Soon",
                "context": {"opp_id": "OPP-555", "value": 500000},
                "recipient_name": "Sales Rep"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["subject"] == "Opportunity Closing"
        assert data["text_body"] == "Deal closing soon."
        assert data["html_body"] == "<p>Deal closing soon.</p>"
        assert data["email_type"] == "Opportunity Closing Soon"
