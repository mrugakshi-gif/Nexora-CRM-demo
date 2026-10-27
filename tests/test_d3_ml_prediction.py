import pytest
from fastapi.testclient import TestClient
from backend.main import app
from tests.conftest import get_test_firebase_token

client = TestClient(app)

def get_auth_headers():
    token = get_test_firebase_token(uid="firebase-admin-uid", email="mrugakshi759@gmail.com")
    return {"Authorization": f"Bearer {token}"}

def test_ml_lead_conversion_unauthenticated():
    response = client.get("/api/ml/leads/LEAD-000001/conversion")
    assert response.status_code == 401

def test_ml_lead_conversion_success():
    # Attempting with a known valid lead from the standard seed data (e.g. LEAD-000001)
    response = client.get("/api/ml/leads/LEAD-000001/conversion", headers=get_auth_headers())
    if response.status_code == 404:
        pytest.skip("LEAD-000001 not found in test DB")
    if response.status_code != 200:
        print(response.json())
    assert response.status_code == 200
    data = response.json()
    assert "lead_id" in data
    assert "conversion_probability" in data
    assert "prediction" in data
    assert data["conversion_probability"] >= 0.0 and data["conversion_probability"] <= 1.0

def test_ml_lead_scoring_success():
    response = client.get("/api/ml/leads/LEAD-000001/score", headers=get_auth_headers())
    if response.status_code == 404:
        pytest.skip("LEAD-000001 not found in test DB")
    assert response.status_code == 200
    data = response.json()
    assert "score_probability" in data

def test_ml_nonexistent_lead():
    response = client.get("/api/ml/leads/INVALID-999/conversion", headers=get_auth_headers())
    assert response.status_code == 404

def test_ml_customer_segmentation_success():
    response = client.get("/api/ml/customers/CUST-000001/segment", headers=get_auth_headers())
    if response.status_code == 404:
        pytest.skip("CUST-000001 not found in test DB")
    assert response.status_code == 200
    data = response.json()
    assert "cluster_id" in data

def test_ml_customer_churn_success():
    response = client.get("/api/ml/customers/CUST-000001/churn", headers=get_auth_headers())
    if response.status_code == 404:
        pytest.skip("CUST-000001 not found in test DB")
    assert response.status_code == 200
    data = response.json()
    assert "churn_probability" in data
    assert "warnings" in data

def test_ml_nonexistent_customer():
    response = client.get("/api/ml/customers/INVALID-999/churn", headers=get_auth_headers())
    assert response.status_code == 404

def test_ml_sales_forecast_success():
    response = client.get("/api/ml/sales/forecast", headers=get_auth_headers())
    assert response.status_code == 200
    data = response.json()
    assert "forecast_amount_inr" in data
    assert data["forecast_amount_inr"] >= 0
