"""D2 Customer 360 and Relationship Tests."""
import os
import pytest

os.environ.setdefault("CRM_AUTH_MODE", "demo")
os.environ.setdefault("CRM_DEMO_PASSWORD", "testpass123")

from fastapi.testclient import TestClient
from tests.conftest import get_test_firebase_token
from backend.main import app
from backend.database import SessionLocal
from backend import models

client = TestClient(app)


def _get_first_user_email():
    db = SessionLocal()
    try:
        u = db.query(models.User).filter(models.User.is_active == True, models.User.deleted_at == None, models.User.role == "Admin").first()
        return u.email if u else None
    finally:
        db.close()


@pytest.fixture(scope="module")
def auth_headers():
    email = _get_first_user_email()
    # Using the new opaque token that the mock verify_id_token recognizes
    # Note: we need to use get_test_firebase_token, but it's cleaner to just format the string since it's deterministic
    token = f"test-firebase-token-{email}"
    # Register the claims in the global mock dict in conftest
    from tests.conftest import get_test_firebase_token
    get_test_firebase_token(uid=email, email=email, email_verified=True)
    return {"Authorization": f"Bearer {token}"}


class TestCustomer360:
    @pytest.fixture(scope="class")
    def customer_id(self):
        db = SessionLocal()
        try:
            c = db.query(models.Customer).filter(models.Customer.deleted_at == None).first()
            return c.customer_id if c else None
        finally:
            db.close()

    def test_360_returns_ok(self, auth_headers, customer_id):
        if not customer_id:
            pytest.skip("No customer in DB")
        resp = client.get(f"/api/customers/{customer_id}/360", headers=auth_headers)
        assert resp.status_code == 200

    def test_360_contains_summary_fields(self, auth_headers, customer_id):
        if not customer_id:
            pytest.skip("No customer in DB")
        resp = client.get(f"/api/customers/{customer_id}/360", headers=auth_headers)
        data = resp.json()
        assert "customer_id" in data
        assert "company_id" in data
        assert "transactions_count" in data
        assert "support_cases_count" in data
        assert "activities_count" in data
        assert "transactions" in data
        assert isinstance(data["transactions"], list)
        assert "support_cases" in data
        assert isinstance(data["support_cases"], list)
        assert "activities" in data
        assert isinstance(data["activities"], list)

    def test_360_transactions_count_matches_db(self, auth_headers, customer_id):
        if not customer_id:
            pytest.skip("No customer in DB")
        db = SessionLocal()
        try:
            db_count = db.query(models.CustomerTransaction).filter(
                models.CustomerTransaction.customer_id == customer_id,
                models.CustomerTransaction.deleted_at == None,
            ).count()
        finally:
            db.close()
        resp = client.get(f"/api/customers/{customer_id}/360", headers=auth_headers)
        # The 360 view returns up to 20 transactions
        assert resp.json()["transactions_count"] == min(db_count, 20)
        assert len(resp.json()["transactions"]) == min(db_count, 20)

    def test_360_requires_auth(self, customer_id):
        if not customer_id:
            pytest.skip("No customer in DB")
        resp = client.get(f"/api/customers/{customer_id}/360")
        assert resp.status_code == 401


class TestCompanyRelationships:
    @pytest.fixture(scope="class")
    def company_id(self):
        db = SessionLocal()
        try:
            c = db.query(models.Company).filter(models.Company.deleted_at == None).first()
            return c.company_id if c else None
        finally:
            db.close()

    def test_company_contacts(self, auth_headers, company_id):
        if not company_id:
            pytest.skip("No company")
        resp = client.get(f"/api/companies/{company_id}/contacts", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_company_leads(self, auth_headers, company_id):
        if not company_id:
            pytest.skip("No company")
        resp = client.get(f"/api/companies/{company_id}/leads", headers=auth_headers)
        assert resp.status_code == 200

    def test_company_opportunities(self, auth_headers, company_id):
        if not company_id:
            pytest.skip("No company")
        resp = client.get(f"/api/companies/{company_id}/opportunities", headers=auth_headers)
        assert resp.status_code == 200

    def test_contacts_only_non_deleted(self, auth_headers, company_id):
        if not company_id:
            pytest.skip("No company")
        db = SessionLocal()
        try:
            db_count = db.query(models.Contact).filter(
                models.Contact.company_id == company_id,
                models.Contact.deleted_at == None,
            ).count()
        finally:
            db.close()
        resp = client.get(f"/api/companies/{company_id}/contacts", headers=auth_headers)
        assert len(resp.json()) == db_count
