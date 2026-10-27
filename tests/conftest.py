"""Global test configuration.

Authentication strategy:
- D1 contract tests use app.dependency_overrides to inject a mock user
  (no real auth needed for regression testing existing endpoints)
- D2 tests use real JWT authentication via CRM_AUTH_MODE=demo

Database Isolation:
- An isolated copy of backend/crm.db is created per test session.
- CRM_DB_URL is injected so both TestClient and internal SessionLocal() use the isolated copy.
- The dev DB is completely untouched by tests.
"""
import os
import tempfile
import pytest

# 1. Prepare test DB path
fd, temp_db_path = tempfile.mkstemp(suffix=".db")
os.close(fd)

orig_db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", "crm.db"))
if not os.path.exists(orig_db_path):
    raise FileNotFoundError(f"Source database not found at {orig_db_path}")

import sqlite3

try:
    with sqlite3.connect(orig_db_path) as source_conn, sqlite3.connect(temp_db_path) as target_conn:
        source_conn.backup(target_conn)

    # Clear firebase_uid in the test DB to prevent 403 Conflicting Mapping errors
    conn = sqlite3.connect(temp_db_path)
    conn.execute("UPDATE users SET firebase_uid = NULL")
    conn.commit()
    conn.close()
except Exception as e:
    raise RuntimeError(f"Failed to create isolated test database backup: {e}") from e

# 2. Set environment variables BEFORE importing backend modules
os.environ["CRM_DB_URL"] = f"sqlite:///{temp_db_path}"
os.environ["CRM_AUTH_MODE"] = "demo"
os.environ["CRM_DEMO_PASSWORD"] = "testpass123"

# 3. Import backend modules
from backend.main import app
from backend.deps import get_current_user
from backend.database import SessionLocal
from backend.models import User

def _mock_user():
    return User(user_id="test-user", email="test@example.com", role="System Admin", is_active=True)

@pytest.fixture(scope="session", autouse=True)
def isolated_test_db():
    """Session cleanup for the isolated DB."""
    yield
    # Cleanup after all tests
    if os.path.exists(temp_db_path):
        try:
            os.remove(temp_db_path)
            if os.path.exists(temp_db_path + "-wal"):
                os.remove(temp_db_path + "-wal")
            if os.path.exists(temp_db_path + "-shm"):
                os.remove(temp_db_path + "-shm")
        except OSError:
            pass

@pytest.fixture
def db_session():
    """Yield a database session for test setup/assertions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

_test_firebase_claims = {}

def get_test_firebase_token(uid: str, email: str, email_verified: bool = True) -> str:
    """Helper to generate an opaque test token and register its claims."""
    token = f"test-firebase-token-{uid}"
    _test_firebase_claims[token] = {
        "uid": uid,
        "email": email,
        "email_verified": email_verified
    }
    return token

@pytest.fixture(autouse=True)
def manage_auth_override(request):
    """Automatically apply/clear auth overrides based on the test module.

    - D1 contract tests → inject mock user (no real credentials needed)
    - All other tests → mock firebase_admin.auth.verify_id_token directly
    """
    module_name = request.module.__name__
    if "test_d1_api_contracts" in module_name or "test_d1_frontend_regression" in module_name:
        app.dependency_overrides[get_current_user] = _mock_user
        yield
        app.dependency_overrides.pop(get_current_user, None)
    else:
        app.dependency_overrides.pop(get_current_user, None)
        
        from unittest.mock import patch
        
        def mock_verify(token):
            if token in _test_firebase_claims:
                return _test_firebase_claims[token]
            
            # Fallback for old tests that might not use the explicit helper yet,
            # though we are migrating them all to use get_test_firebase_token.
            if token.startswith("test-firebase-token-"):
                raise ValueError("Token not registered in test claims.")
                
            raise ValueError("Invalid token")
            
        with patch('firebase_admin.auth.verify_id_token', side_effect=mock_verify):
            yield
