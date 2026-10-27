import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.models import User
from backend.database import get_db

client = TestClient(app)

@pytest.fixture
def test_users(db_session):
    # Create a normal user and an admin user, checking if they exist
    normal_user = db_session.query(User).filter_by(user_id="test-normal").first()
    if not normal_user:
        normal_user = User(
            user_id="test-normal",
            email="normal@test.com",
            role="User",
            is_active=True,
            password_hash="$2b$12$e/cO0o3d0JpE.ZJ9U0zM.O"  # dummy
        )
        db_session.add(normal_user)

    admin_user = db_session.query(User).filter_by(user_id="test-admin").first()
    if not admin_user:
        admin_user = User(
            user_id="test-admin",
            email="admin@test.com",
            role="Admin",
            is_active=True,
            password_hash="$2b$12$e/cO0o3d0JpE.ZJ9U0zM.O"  # dummy
        )
        db_session.add(admin_user)
    
    db_session.commit()
    return normal_user, admin_user

@pytest.fixture
def normal_token(test_users):
    from tests.conftest import get_test_firebase_token
    return get_test_firebase_token(uid="test-normal", email="normal@test.com", email_verified=True)

@pytest.fixture
def admin_token(test_users):
    from tests.conftest import get_test_firebase_token
    return get_test_firebase_token(uid="test-admin", email="admin@test.com", email_verified=True)

class TestRBACEnforcement:
    def test_unauthenticated_returns_401(self):
        # We know DELETE is protected by RoleChecker
        response = client.delete("/api/companies/COMP-999")
        assert response.status_code == 401

    def test_normal_user_returns_403(self, normal_token):
        headers = {"Authorization": f"Bearer {normal_token}"}
        response = client.delete("/api/companies/COMP-999", headers=headers)
        assert response.status_code == 403
        assert "Operation not permitted" in response.json()["detail"]

    def test_admin_user_succeeds(self, admin_token, db_session):
        # We need a real company to delete so it doesn't return 404 (which could mask success of RBAC)
        # Or wait, if RBAC passes, it goes to the endpoint logic and returns 404 for not found.
        # But 404 means RBAC succeeded.
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.delete("/api/companies/COMP-999", headers=headers)
        # It should return 404 because COMP-999 doesn't exist, which proves RBAC allowed access.
        assert response.status_code == 404
        
        payload = {
            "company_name": "Del Me Test Co",
            "industry_id": "IND-001",
            "city": "Mumbai",
            "state": "Maharashtra",
            "account_status": "Active"
        }
        create_resp = client.post("/api/companies", json=payload, headers=headers)
        assert create_resp.status_code == 201, f"Failed to create company: {create_resp.json()}"
        company_id = create_resp.json()["company_id"]
        
        response2 = client.delete(f"/api/companies/{company_id}", headers=headers)
        assert response2.status_code == 200

    def test_normal_user_can_access_unrestricted(self, normal_token, db_session):
        # Normal user should be able to GET companies
        headers = {"Authorization": f"Bearer {normal_token}"}
        response = client.get("/api/companies", headers=headers)
        assert response.status_code == 200
