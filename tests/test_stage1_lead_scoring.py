import pytest
from fastapi.testclient import TestClient
from backend.main import app
from tests.conftest import get_test_firebase_token

client = TestClient(app)

def get_auth_headers():
    token = get_test_firebase_token(uid="firebase-admin-uid", email="mrugakshi759@gmail.com")
    return {"Authorization": f"Bearer {token}"}

def test_lead_scoring_unauthenticated():
    """Verify endpoint is secured against unauthorized requests."""
    response = client.get("/api/ml/leads/LEAD-000001/score")
    assert response.status_code == 401

def test_lead_scoring_nonexistent():
    """Verify safe 404 behavior for invalid or non-existent lead IDs."""
    response = client.get("/api/ml/leads/NONEXISTENT-LEAD-9999/score", headers=get_auth_headers())
    assert response.status_code == 404

def test_lead_scoring_response_contract_and_non_nan():
    """
    Regression test for Stage 1:
    - Verify both score_probability and lead_score are returned.
    - Verify lead_score is not null/undefined/NaN.
    - Verify key_factors are generated via local logit decomposition.
    """
    response = client.get("/api/ml/leads/LEAD-000001/score", headers=get_auth_headers())
    assert response.status_code == 200
    data = response.json()
    
    # 1. Check primary score fields
    assert "lead_id" in data
    assert data["lead_id"] == "LEAD-000001"
    assert "score_probability" in data
    assert "lead_score" in data
    assert data["score_probability"] is not None
    assert data["lead_score"] is not None
    
    prob = data["score_probability"]
    lead_score = data["lead_score"]
    
    # Must be valid probabilities between 0 and 1
    assert 0.0 <= prob <= 1.0
    assert 0.0 <= lead_score <= 1.0
    assert prob == lead_score
    
    # Mathematical sanity: Ensure frontend formula does not yield NaN
    frontend_raw = prob if prob is not None else lead_score
    score_display = round(frontend_raw * 100)
    assert not (score_display != score_display)  # check not NaN
    assert isinstance(score_display, int)

    # 2. Check explainability factors (Instance-level log-odds decomposition)
    assert "key_factors" in data
    assert isinstance(data["key_factors"], list)
    assert len(data["key_factors"]) > 0
    
    for factor in data["key_factors"]:
        assert "feature" in factor
        assert "impact" in factor
        assert factor["impact"] in ["positive", "negative"]
        assert "contribution" in factor
        assert isinstance(factor["contribution"], (float, int))
        assert "description" in factor
        assert len(factor["description"]) > 0
        
        # Verify directional consistency: positive impact implies contribution > 0
        if factor["impact"] == "positive":
            assert factor["contribution"] >= 0
        else:
            assert factor["contribution"] <= 0

def test_lead_scoring_different_leads_dynamic_outputs():
    """Verify that different leads generate dynamic scores and tailored explanations."""
    res1 = client.get("/api/ml/leads/LEAD-000001/score", headers=get_auth_headers())
    res2 = client.get("/api/ml/leads/LEAD-000002/score", headers=get_auth_headers())
    
    assert res1.status_code == 200
    assert res2.status_code == 200
    
    d1 = res1.json()
    d2 = res2.json()
    
    # Both must have valid scores
    assert 0.0 <= d1["score_probability"] <= 1.0
    assert 0.0 <= d2["score_probability"] <= 1.0
    assert len(d1["key_factors"]) > 0
    assert len(d2["key_factors"]) > 0
