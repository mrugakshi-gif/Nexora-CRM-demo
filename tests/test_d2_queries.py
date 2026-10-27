"""D2 Pagination, Sorting, Filtering, and Soft-Delete Tests."""
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
    from tests.conftest import get_test_firebase_token
    token = get_test_firebase_token(uid=email, email=email, email_verified=True)
    return {"Authorization": f"Bearer {token}"}


class TestPagination:
    def test_companies_returns_paginated_structure(self, auth_headers):
        resp = client.get("/api/companies?page=1&page_size=10", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "page" in data
        assert "page_size" in data
        assert "total" in data
        assert "total_pages" in data
        assert data["page"] == 1
        assert data["page_size"] == 10
        assert len(data["items"]) <= 10

    def test_page_size_respected(self, auth_headers):
        resp = client.get("/api/companies?page=1&page_size=5", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) <= 5

    def test_second_page_differs_from_first(self, auth_headers):
        r1 = client.get("/api/companies?page=1&page_size=5", headers=auth_headers)
        r2 = client.get("/api/companies?page=2&page_size=5", headers=auth_headers)
        assert r1.status_code == 200
        assert r2.status_code == 200
        ids1 = [i["company_id"] for i in r1.json()["items"]]
        ids2 = [i["company_id"] for i in r2.json()["items"]]
        if r2.json()["total"] > 5:
            assert ids1 != ids2

    def test_total_matches_db(self, auth_headers):
        db = SessionLocal()
        try:
            db_count = db.query(models.Company).filter(models.Company.deleted_at == None).count()
        finally:
            db.close()
        resp = client.get("/api/companies?page=1&page_size=1", headers=auth_headers)
        assert resp.json()["total"] == db_count

    def test_leads_pagination(self, auth_headers):
        resp = client.get("/api/leads?page=1&page_size=10", headers=auth_headers)
        assert resp.status_code == 200
        assert "items" in resp.json()

    def test_opportunities_pagination(self, auth_headers):
        resp = client.get("/api/opportunities?page=1&page_size=10", headers=auth_headers)
        assert resp.status_code == 200
        assert "items" in resp.json()


class TestSearch:
    def test_company_search_returns_matching(self, auth_headers):
        # Get a company name from DB to search for
        db = SessionLocal()
        try:
            c = db.query(models.Company).filter(models.Company.deleted_at == None).first()
            search_term = c.company_name[:5] if c else "Test"
        finally:
            db.close()
        resp = client.get(f"/api/companies?search={search_term}&page_size=50", headers=auth_headers)
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            matched = any([
                item.get("company_name") and search_term.lower() in item["company_name"].lower(),
                item.get("company_id") and search_term.lower() in item["company_id"].lower(),
                item.get("state") and search_term.lower() in item["state"].lower(),
                item.get("city") and search_term.lower() in item["city"].lower(),
                item.get("account_status") and search_term.lower() in item["account_status"].lower(),
                item.get("industry_id") and search_term.lower() in item["industry_id"].lower()
            ])
            assert matched, f"Search term '{search_term}' not found in {item}"


class TestSorting:
    def test_valid_sort_field(self, auth_headers):
        resp = client.get("/api/companies?sort_by=company_name&sort_order=asc", headers=auth_headers)
        assert resp.status_code == 200

    def test_invalid_sort_field_rejected(self, auth_headers):
        resp = client.get("/api/companies?sort_by=DROP TABLE companies", headers=auth_headers)
        assert resp.status_code == 400


class TestSoftDelete:
    def test_soft_delete_hides_from_list(self, auth_headers):
        """Create a company, soft-delete it, verify it disappears from GET /api/companies."""
        # Create
        payload = {
            "company_name": "SoftDeleteTestCo",
            "industry_id": None,
            "city": "Mumbai",
            "state": "Maharashtra",
            "account_status": "Active",
        }
        # Get a valid industry_id first
        db = SessionLocal()
        try:
            ind = db.query(models.Industry).first()
            payload["industry_id"] = ind.industry_id if ind else None
        finally:
            db.close()

        create_resp = client.post("/api/companies", json=payload, headers=auth_headers)
        assert create_resp.status_code == 201
        company_id = create_resp.json()["company_id"]

        # Verify visible
        list_resp = client.get(f"/api/companies/{company_id}", headers=auth_headers)
        assert list_resp.status_code == 200

        # Soft-delete
        del_resp = client.delete(f"/api/companies/{company_id}", headers=auth_headers)
        assert del_resp.status_code == 200

        # Verify hidden from GET
        get_resp = client.get(f"/api/companies/{company_id}", headers=auth_headers)
        assert get_resp.status_code == 404

        # Verify still in DB with deleted_at set
        db = SessionLocal()
        try:
            row = db.query(models.Company).filter(models.Company.company_id == company_id).first()
            assert row is not None, "Row was hard-deleted — expected soft-delete"
            assert row.deleted_at is not None, "deleted_at should be set"
        finally:
            db.close()
