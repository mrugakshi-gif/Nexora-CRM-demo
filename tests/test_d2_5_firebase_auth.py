import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from backend.main import app
from backend.models import User
from backend.database import get_db
from sqlalchemy import text

client = TestClient(app)

@pytest.fixture
def clean_users(db_session):
    # Ensure our test users don't have firebase_uids before each test
    db_session.execute(text("UPDATE users SET firebase_uid = NULL;"))
    db_session.commit()
    yield
    db_session.execute(text("UPDATE users SET firebase_uid = NULL;"))
    db_session.commit()

class TestFirebaseAuth:
    # 1. Missing token -> 401
    def test_missing_token_returns_401(self):
        response = client.get("/api/auth/me")
        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"]

    # 2. Invalid token -> 401
    def test_invalid_token_returns_401(self):
        with patch('firebase_admin.auth.verify_id_token', side_effect=Exception("Invalid")):
            response = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid_token"})
            assert response.status_code == 401

    # 3. Expired token -> 401
    def test_expired_token_returns_401(self):
        with patch('firebase_admin.auth.verify_id_token', side_effect=Exception("Token expired")):
            response = client.get("/api/auth/me", headers={"Authorization": "Bearer expired_token"})
            assert response.status_code == 401

    # 4. Valid Firebase token -> authenticated
    def test_valid_firebase_token_returns_authenticated(self, clean_users):
        mock_decoded = {"uid": "new_uid", "email": "aarohi.kelkar45@crmvendor-india.example", "email_verified": True}
        with patch('firebase_admin.auth.verify_id_token', return_value=mock_decoded):
            response = client.get("/api/auth/me", headers={"Authorization": "Bearer valid"})
            assert response.status_code == 200
            assert response.json()["email"] == "aarohi.kelkar45@crmvendor-india.example"

    # 5. Valid token + unknown CRM email -> 403
    def test_unknown_crm_email_returns_403(self):
        mock_decoded = {"uid": "new_uid", "email": "unknown@example.com", "email_verified": True}
        with patch('firebase_admin.auth.verify_id_token', return_value=mock_decoded):
            response = client.get("/api/auth/me", headers={"Authorization": "Bearer valid"})
            assert response.status_code == 403
            assert "CRM account not found" in response.json()["detail"]

    # 6. First login with verified email -> firebase_uid linked
    def test_first_login_verified_email_links_uid(self, clean_users, db_session):
        mock_decoded = {"uid": "first_login_uid", "email": "aarohi.kelkar45@crmvendor-india.example", "email_verified": True}
        with patch('firebase_admin.auth.verify_id_token', return_value=mock_decoded):
            response = client.get("/api/auth/me", headers={"Authorization": "Bearer valid"})
            assert response.status_code == 200
            
            user = db_session.query(User).filter_by(email="aarohi.kelkar45@crmvendor-india.example").first()
            assert user.firebase_uid == "first_login_uid"

    # 7. First login with unverified email -> rejected
    def test_first_login_unverified_email_rejected(self, clean_users):
        mock_decoded = {"uid": "first_login_uid", "email": "aarohi.kelkar45@crmvendor-india.example", "email_verified": False}
        with patch('firebase_admin.auth.verify_id_token', return_value=mock_decoded):
            response = client.get("/api/auth/me", headers={"Authorization": "Bearer valid"})
            assert response.status_code == 403
            assert "verified email" in response.json()["detail"]

    # 8. Existing firebase_uid -> successful lookup
    def test_existing_firebase_uid_lookup(self, clean_users, db_session):
        user = db_session.query(User).filter_by(email="aarohi.kelkar45@crmvendor-india.example").first()
        user.firebase_uid = "existing_uid"
        db_session.commit()
        
        mock_decoded = {"uid": "existing_uid", "email": "irrelevant@test.com", "email_verified": False}
        with patch('firebase_admin.auth.verify_id_token', return_value=mock_decoded):
            response = client.get("/api/auth/me", headers={"Authorization": "Bearer valid"})
            assert response.status_code == 200
            assert response.json()["email"] == "aarohi.kelkar45@crmvendor-india.example"

    # 9. Conflicting firebase_uid -> rejected
    def test_conflicting_firebase_uid_rejected(self, clean_users, db_session):
        user = db_session.query(User).filter_by(email="aarohi.kelkar45@crmvendor-india.example").first()
        user.firebase_uid = "existing_uid"
        db_session.commit()
        
        mock_decoded = {"uid": "different_uid", "email": "aarohi.kelkar45@crmvendor-india.example", "email_verified": True}
        with patch('firebase_admin.auth.verify_id_token', return_value=mock_decoded):
            response = client.get("/api/auth/me", headers={"Authorization": "Bearer valid"})
            assert response.status_code == 403
            assert "Conflicting mapping" in response.json()["detail"]

    # 10. Inactive CRM user -> rejected
    def test_inactive_crm_user_rejected(self, clean_users, db_session):
        user = db_session.query(User).filter_by(email="aarohi.kelkar45@crmvendor-india.example").first()
        user.is_active = False
        db_session.commit()
        
        mock_decoded = {"uid": "some_uid", "email": "aarohi.kelkar45@crmvendor-india.example", "email_verified": True}
        with patch('firebase_admin.auth.verify_id_token', return_value=mock_decoded):
            response = client.get("/api/auth/me", headers={"Authorization": "Bearer valid"})
            assert response.status_code == 400
            assert "Inactive user" in response.json()["detail"]
            
        user.is_active = True
        db_session.commit()

    # 11. Soft-deleted CRM user -> rejected
    def test_soft_deleted_crm_user_rejected(self, clean_users, db_session):
        user = db_session.query(User).filter_by(email="aarohi.kelkar45@crmvendor-india.example").first()
        user.deleted_at = "2026-09-17T12:00:00Z"
        db_session.commit()
        
        mock_decoded = {"uid": "some_uid", "email": "aarohi.kelkar45@crmvendor-india.example", "email_verified": True}
        with patch('firebase_admin.auth.verify_id_token', return_value=mock_decoded):
            response = client.get("/api/auth/me", headers={"Authorization": "Bearer valid"})
            assert response.status_code == 403
            assert "CRM account not found" in response.json()["detail"]
            
        user.deleted_at = None
        db_session.commit()

    # 12. Normal user -> restricted DELETE returns 403
    def test_normal_user_delete_restricted_403(self, clean_users):
        # We need a user with role="User"
        mock_decoded = {"uid": "normal_uid", "email": "alok.menon55@crmvendor-india.example", "email_verified": True}
        with patch('firebase_admin.auth.verify_id_token', return_value=mock_decoded):
            response = client.delete("/api/companies/COMP-123", headers={"Authorization": "Bearer valid"})
            assert response.status_code == 403
            assert "Operation not permitted" in response.json()["detail"]

    # 13. Admin -> restricted DELETE succeeds (or returns 404 because not found, but not 403)
    def test_admin_delete_succeeds(self, clean_users, db_session):
        user = db_session.query(User).filter_by(email="aditya.prasad5@crmvendor-india.example").first()
        user.role = "Admin"
        db_session.commit()
        
        mock_decoded = {"uid": "admin_uid", "email": "aditya.prasad5@crmvendor-india.example", "email_verified": True}
        with patch('firebase_admin.auth.verify_id_token', return_value=mock_decoded):
            response = client.delete("/api/companies/COMP-999", headers={"Authorization": "Bearer valid"})
            assert response.status_code == 404

    # 14. System Admin -> restricted DELETE succeeds
    def test_system_admin_delete_succeeds(self, clean_users, db_session):
        user = db_session.query(User).filter_by(email="aditya.prasad5@crmvendor-india.example").first()
        user.role = "System Admin"
        db_session.commit()
        
        mock_decoded = {"uid": "sysadmin_uid", "email": "aditya.prasad5@crmvendor-india.example", "email_verified": True}
        with patch('firebase_admin.auth.verify_id_token', return_value=mock_decoded):
            response = client.delete("/api/companies/COMP-999", headers={"Authorization": "Bearer valid"})
            assert response.status_code == 404

    # 15. Unauthenticated request -> 401
    def test_unauthenticated_request_401(self):
        response = client.get("/api/companies")
        assert response.status_code == 401

    # 16. Existing unrestricted endpoint -> authenticated normal user succeeds
    def test_normal_user_access_unrestricted(self, clean_users):
        mock_decoded = {"uid": "normal_uid", "email": "alok.menon55@crmvendor-india.example", "email_verified": True}
        with patch('firebase_admin.auth.verify_id_token', return_value=mock_decoded):
            response = client.get("/api/companies", headers={"Authorization": "Bearer valid"})
            assert response.status_code == 200

    # 17. Unknown CRM email returns 403 (never 500) and does NOT touch scratch/
    def test_unknown_crm_email_no_scratch_write(self, tmp_path, monkeypatch):
        # Even if cwd has no scratch directory, this must return 403 cleanly without raising FileNotFoundError
        monkeypatch.chdir(tmp_path)
        mock_decoded = {"uid": "unknown_uid", "email": "nonexistent.evaluator@example.com", "email_verified": True}
        with patch('firebase_admin.auth.verify_id_token', return_value=mock_decoded):
            response = client.get("/api/auth/me", headers={"Authorization": "Bearer valid"})
            assert response.status_code == 403
            assert response.json()["detail"] == "CRM account not found for this email: nonexistent.evaluator@example.com"
            assert not (tmp_path / "scratch").exists()

