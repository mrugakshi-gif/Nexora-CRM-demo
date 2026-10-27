import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.models import User, Campaign
from tests.conftest import get_test_firebase_token

client = TestClient(app)

@pytest.fixture
def test_users(db_session):
    normal_user = db_session.query(User).filter_by(user_id="test-normal").first()
    if not normal_user:
        normal_user = User(
            user_id="test-normal",
            email="normal@test.com",
            role="User",
            is_active=True,
            password_hash="dummy"
        )
        db_session.add(normal_user)

    admin_user = db_session.query(User).filter_by(user_id="test-admin").first()
    if not admin_user:
        admin_user = User(
            user_id="test-admin",
            email="admin@test.com",
            role="Admin",
            is_active=True,
            password_hash="dummy"
        )
        db_session.add(admin_user)
    
    db_session.commit()
    return normal_user, admin_user

@pytest.fixture
def normal_token(test_users):
    return get_test_firebase_token(uid="test-normal", email="normal@test.com", email_verified=True)

@pytest.fixture
def admin_token(test_users):
    return get_test_firebase_token(uid="test-admin", email="admin@test.com", email_verified=True)


class TestCampaignCRUD:
    def test_create_campaign(self, normal_token, db_session):
        from backend.models import Department
        dept = db_session.query(Department).first()
        if not dept:
            dept = Department(department_id="DEPT-001", department_name="Marketing", description="test")
            db_session.add(dept)
            db_session.commit()
            
        headers = {"Authorization": f"Bearer {normal_token}"}
        payload = {
            "campaign_name": "New Test Campaign",
            "campaign_type": "Webinar",
            "start_date": "2026-10-01",
            "owner_department_id": dept.department_id
        }
        res = client.post("/api/campaigns", json=payload, headers=headers)
        assert res.status_code == 201, res.text
        data = res.json()
        assert data["campaign_name"] == "New Test Campaign"
        assert data["campaign_id"].startswith("CAMP-")
        self.__class__.campaign_id = data["campaign_id"]

    def test_update_campaign(self, normal_token):
        headers = {"Authorization": f"Bearer {normal_token}"}
        payload = {
            "campaign_name": "Updated Campaign",
            "campaign_type": "Social Media"
        }
        res = client.put(f"/api/campaigns/{self.campaign_id}", json=payload, headers=headers)
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["campaign_name"] == "Updated Campaign"
        assert data["campaign_type"] == "Social Media"

    def test_delete_campaign_normal_user_denied(self, normal_token):
        headers = {"Authorization": f"Bearer {normal_token}"}
        res = client.delete(f"/api/campaigns/{self.campaign_id}", headers=headers)
        assert res.status_code == 403

    def test_delete_campaign_admin_user_success(self, admin_token, db_session):
        headers = {"Authorization": f"Bearer {admin_token}"}
        res = client.delete(f"/api/campaigns/{self.campaign_id}", headers=headers)
        assert res.status_code == 200

        # Verify soft delete
        campaign = db_session.query(Campaign).filter_by(campaign_id=self.campaign_id).first()
        assert campaign.deleted_at is not None
