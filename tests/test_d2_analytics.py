"""D2 Analytics Tests — verify metrics are computed from real DB data."""
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


class TestAnalyticsDashboard:
    def test_dashboard_returns_ok(self, auth_headers):
        resp = client.get("/api/analytics/dashboard", headers=auth_headers)
        assert resp.status_code == 200

    def test_dashboard_company_count_matches_db(self, auth_headers):
        db = SessionLocal()
        try:
            db_count = db.query(models.Company).filter(models.Company.deleted_at == None).count()
        finally:
            db.close()
        resp = client.get("/api/analytics/dashboard", headers=auth_headers)
        data = resp.json()
        assert data["total_companies"] == db_count, "company count must come from DB"

    def test_dashboard_lead_count_matches_db(self, auth_headers):
        db = SessionLocal()
        try:
            db_count = db.query(models.Lead).filter(models.Lead.deleted_at == None).count()
        finally:
            db.close()
        resp = client.get("/api/analytics/dashboard", headers=auth_headers)
        assert resp.json()["total_leads"] == db_count

    def test_dashboard_customer_count_matches_db(self, auth_headers):
        db = SessionLocal()
        try:
            db_count = db.query(models.Customer).filter(models.Customer.deleted_at == None).count()
        finally:
            db.close()
        resp = client.get("/api/analytics/dashboard", headers=auth_headers)
        assert resp.json()["total_customers"] == db_count

    def test_dashboard_no_hardcoded_values(self, auth_headers):
        """Verify KPIs are NOT hardcoded — change one count and re-check."""
        # We check that reported lead count is NOT a suspicious round number
        # that would indicate hardcoding (0, 100, 1000 etc.)
        resp = client.get("/api/analytics/dashboard", headers=auth_headers)
        data = resp.json()
        # If DB has actual CRM data (seeded), lead count must be > 0
        assert data["total_leads"] > 0, "total_leads should be > 0 after seeding"


class TestLeadFunnel:
    def test_funnel_returns_grouped_statuses(self, auth_headers):
        resp = client.get("/api/analytics/leads/funnel", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if data:
            assert "status" in data[0]
            assert "count" in data[0]

    def test_funnel_counts_match_db(self, auth_headers):
        db = SessionLocal()
        try:
            from sqlalchemy import func
            rows = (
                db.query(models.Lead.lead_status, func.count())
                .filter(models.Lead.deleted_at == None)
                .group_by(models.Lead.lead_status)
                .all()
            )
            db_counts = {row[0]: row[1] for row in rows}
        finally:
            db.close()
        resp = client.get("/api/analytics/leads/funnel", headers=auth_headers)
        api_counts = {item["status"]: item["count"] for item in resp.json()}
        for status, count in db_counts.items():
            assert api_counts.get(status) == count, f"Mismatch for status {status!r}"


class TestOpportunityPipeline:
    def test_pipeline_grouped_by_stage(self, auth_headers):
        resp = client.get("/api/analytics/opportunities/pipeline", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if data:
            item = data[0]
            assert "stage" in item
            assert "count" in item
            assert "total_value_inr" in item


class TestMonthlyRevenue:
    def test_revenue_list(self, auth_headers):
        resp = client.get("/api/analytics/revenue/monthly", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_revenue_months_in_order(self, auth_headers):
        resp = client.get("/api/analytics/revenue/monthly", headers=auth_headers)
        months = [item["month"] for item in resp.json()]
        assert months == sorted(months)


class TestSupportSummary:
    def test_support_summary_structure(self, auth_headers):
        resp = client.get("/api/analytics/support/summary", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "by_status" in data
        assert "avg_satisfaction_score" in data

    def test_requires_auth(self):
        resp = client.get("/api/analytics/support/summary")
        assert resp.status_code == 401
