"""
test_stage5_firebase_auth_config.py — Stage 5 isolated mock test suite.

Validates backend/firebase_client.py initialization behavior, project ID resolution,
fallback AnonymousCredentials handling, mocked certificate loading, malformed credential
exception handling, and idempotency.

All tests run in-memory using mocks without making any external network requests or
accessing live Firebase accounts.
"""
import base64
import json
import os
import pytest
from unittest.mock import patch, MagicMock
from google.auth.credentials import AnonymousCredentials
import backend.firebase_client as fc


@pytest.fixture(autouse=True)
def reset_firebase_client_state():
    """Ensure module-level initialization state is reset before and after each test."""
    original_state = fc._initialized
    fc._initialized = False
    yield
    fc._initialized = original_state


def test_stage5_default_project_id_resolution():
    """1. Default Project ID: With credentials and project env unset, falls back to 'ai-enterprise-crm'."""
    with patch.dict(os.environ, {}, clear=True):
        with patch("firebase_admin.get_app", side_effect=ValueError("No app")):
            with patch("firebase_admin.initialize_app") as mock_init:
                fc.init_firebase()
                mock_init.assert_called_once()
                args, kwargs = mock_init.call_args
                assert isinstance(args[0], AnonymousCredentials)
                assert kwargs.get("options", {}).get("projectId") == "ai-enterprise-crm"


def test_stage5_environment_project_id_override():
    """2. Custom Project ID: With FIREBASE_PROJECT_ID set, passes configured project ID."""
    with patch.dict(os.environ, {"FIREBASE_PROJECT_ID": "custom-crm-project-id"}, clear=True):
        with patch("firebase_admin.get_app", side_effect=ValueError("No app")):
            with patch("firebase_admin.initialize_app") as mock_init:
                fc.init_firebase()
                mock_init.assert_called_once()
                args, kwargs = mock_init.call_args
                assert isinstance(args[0], AnonymousCredentials)
                assert kwargs.get("options", {}).get("projectId") == "custom-crm-project-id"


def test_stage5_service_account_certificate_path_mocked():
    """3. Certificate Path: With FIREBASE_CREDENTIALS_BASE64 set, decodes and initializes Certificate."""
    dummy_dict = {"type": "service_account", "project_id": "test-mock-project"}
    b64_val = base64.b64encode(json.dumps(dummy_dict).encode("utf-8")).decode("utf-8")
    
    with patch.dict(os.environ, {"FIREBASE_CREDENTIALS_BASE64": b64_val}, clear=True):
        with patch("firebase_admin.get_app", side_effect=ValueError("No app")):
            with patch("firebase_admin.credentials.Certificate") as mock_cert:
                mock_cert.return_value = "MOCK_CERTIFICATE_OBJECT"
                with patch("firebase_admin.initialize_app") as mock_init:
                    fc.init_firebase()
                    mock_cert.assert_called_once_with(dummy_dict)
                    mock_init.assert_called_once_with("MOCK_CERTIFICATE_OBJECT")


def test_stage5_malformed_base64_raises_exception():
    """4. Malformed Credentials: With invalid base64, init_firebase raises and does not initialize."""
    with patch.dict(os.environ, {"FIREBASE_CREDENTIALS_BASE64": "!!!invalid-base64!!!"}, clear=True):
        with patch("firebase_admin.get_app", side_effect=ValueError("No app")):
            with patch("firebase_admin.initialize_app") as mock_init:
                with pytest.raises(Exception):
                    fc.init_firebase()
                mock_init.assert_not_called()


def test_stage5_idempotent_initialization():
    """5. Idempotency: When already initialized, init_firebase returns cleanly without calling initialize_app."""
    # Sub-case A: Module-level _initialized flag is True
    fc._initialized = True
    with patch("firebase_admin.initialize_app") as mock_init:
        fc.init_firebase()
        mock_init.assert_not_called()

    # Sub-case B: Module flag is False, but firebase_admin.get_app() returns an active app
    fc._initialized = False
    with patch("firebase_admin.get_app", return_value=MagicMock()):
        with patch("firebase_admin.initialize_app") as mock_init:
            fc.init_firebase()
            mock_init.assert_not_called()
            assert fc._initialized is True
