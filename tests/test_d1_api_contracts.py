"""D1 API Contract & Regression Tests.

These tests verify that all frontend-consumed endpoints continue to work
after the D2 refactor. They override auth so no real credentials are needed.
"""
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)



# ---------------------------------------------------------
# Auth
# ---------------------------------------------------------

def test_auth_me():
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "test-user"


# ---------------------------------------------------------
# Core CRUD — now return paginated responses
# ---------------------------------------------------------

def _items(resp):
    """Extract items list from paginated response."""
    data = resp.json()
    # Support both paginated {"items": [...]} and plain list
    if isinstance(data, dict) and "items" in data:
        return data["items"]
    return data


def test_companies_endpoints():
    response = client.get("/api/companies/?page_size=1")
    assert response.status_code == 200
    items = _items(response)
    if items:
        cid = items[0]["company_id"]
        res2 = client.get(f"/api/companies/{cid}")
        assert res2.status_code == 200
        assert res2.json()["company_id"] == cid


def test_contacts_endpoints():
    response = client.get("/api/contacts/?page_size=1")
    assert response.status_code == 200
    items = _items(response)
    if items:
        cid = items[0]["contact_id"]
        res2 = client.get(f"/api/contacts/{cid}")
        assert res2.status_code == 200
        assert res2.json()["contact_id"] == cid


def test_leads_endpoints():
    response = client.get("/api/leads/?page_size=1")
    assert response.status_code == 200
    items = _items(response)
    if items:
        lid = items[0]["lead_id"]
        res2 = client.get(f"/api/leads/{lid}")
        assert res2.status_code == 200
        assert res2.json()["lead_id"] == lid


def test_opportunities_endpoints():
    response = client.get("/api/opportunities/?page_size=1")
    assert response.status_code == 200
    items = _items(response)
    if items:
        oid = items[0]["opportunity_id"]
        res2 = client.get(f"/api/opportunities/{oid}")
        assert res2.status_code == 200
        assert res2.json()["opportunity_id"] == oid


def test_activities_endpoints():
    response = client.get("/api/activities/?page_size=1")
    assert response.status_code == 200
    items = _items(response)
    if items:
        aid = items[0]["activity_id"]
        res2 = client.get(f"/api/activities/{aid}")
        assert res2.status_code == 200
        assert res2.json()["activity_id"] == aid


def test_customers_endpoints():
    response = client.get("/api/customers/?page_size=1")
    assert response.status_code == 200
    items = _items(response)
    if items:
        cid = items[0]["customer_id"]
        res2 = client.get(f"/api/customers/{cid}")
        assert res2.status_code == 200
        assert res2.json()["customer_id"] == cid


# ---------------------------------------------------------
# Reference data (read-only, no pagination)
# ---------------------------------------------------------

def test_industries_endpoint():
    resp = client.get("/api/industries/")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_lead_sources_endpoint():
    resp = client.get("/api/lead_sources/")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ---------------------------------------------------------
# AI / chat endpoints still work
# ---------------------------------------------------------

def test_chat_sessions_endpoint():
    resp = client.get("/api/chat/history")
    # 200 or 404 acceptable — just must not 500
    assert resp.status_code in (200, 404)
