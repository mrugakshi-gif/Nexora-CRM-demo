import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import SessionLocal
from backend.models import Opportunity
from tests.conftest import get_test_firebase_token

client = TestClient(app)

def get_auth_headers():
    token = get_test_firebase_token(uid="firebase-admin-uid", email="mrugakshi759@gmail.com")
    return {"Authorization": f"Bearer {token}"}

def test_deal_health_unauthenticated():
    """Verify deal health endpoints are secured against unauthorized access."""
    res1 = client.get("/api/health/deal/OPP-000001")
    assert res1.status_code == 401
    
    res2 = client.get("/api/opportunities/OPP-000001/health")
    assert res2.status_code == 401

def test_deal_health_invalid_opportunity_id():
    """Verify safe 404 behavior for invalid or non-existent opportunity IDs."""
    res1 = client.get("/api/health/deal/OPP-INVALID-9999", headers=get_auth_headers())
    assert res1.status_code == 404
    
    res2 = client.get("/api/opportunities/OPP-INVALID-9999/health", headers=get_auth_headers())
    assert res2.status_code == 404

def test_deal_health_closed_won():
    """Verify Closed Won deal evaluation: 100% health, 0% risk, Low risk level."""
    res = client.get("/api/health/deal/OPP-000001", headers=get_auth_headers())
    assert res.status_code == 200
    data = res.json()
    assert data["opportunity_id"] == "OPP-000001"
    assert data["is_closed"] is True
    assert data["close_outcome"] == "Won"
    assert data["health_score"] == 100.0
    assert data["risk_score"] == 0.0
    assert data["risk_level"] == "Low"
    assert data["status"] == "Excellent"
    assert data["scoring_method"] == "rule_based_heuristic"
    assert data["is_ml_model"] is False

def test_deal_health_closed_lost():
    """Verify Closed Lost deal evaluation: 0% health, 100% risk, Critical risk level."""
    res = client.get("/api/health/deal/OPP-000004", headers=get_auth_headers())
    assert res.status_code == 200
    data = res.json()
    assert data["opportunity_id"] == "OPP-000004"
    assert data["is_closed"] is True
    assert data["close_outcome"] == "Lost"
    assert data["health_score"] == 0.0
    assert data["risk_score"] == 100.0
    assert data["risk_level"] == "Critical"
    assert data["status"] == "Critical"
    assert data["scoring_method"] == "rule_based_heuristic"
    assert data["is_ml_model"] is False

def test_deal_health_high_risk_open_deal():
    """Verify open deal with overdue timeline and stale activity is flagged as high/critical risk."""
    res = client.get("/api/health/deal/OPP-000002", headers=get_auth_headers())
    assert res.status_code == 200
    data = res.json()
    assert data["opportunity_id"] == "OPP-000002"
    assert data["is_closed"] is False
    assert data["health_score"] < 60.0
    assert data["risk_score"] > 40.0
    assert data["risk_level"] in ["High", "Critical"]
    assert len(data["contributing_factors"]) > 0
    assert len(data["mitigation_recommendations"]) > 0
    
    # Check that contributing factors have required structure
    for factor in data["contributing_factors"]:
        assert "category" in factor
        assert "name" in factor
        assert "impact" in factor
        assert factor["impact"] in ["positive", "negative", "neutral"]
        assert "weight_score_impact" in factor
        assert "detail" in factor

    # Check that supporting metrics exist
    metrics = data["supporting_metrics"]
    assert "days_in_current_stage" in metrics
    assert "days_overdue" in metrics
    assert "max_discount_pct" in metrics
    assert "products_count" in metrics
    assert "activities_count" in metrics

def test_deal_health_missing_data_resilience():
    """Verify that an opportunity with missing critical fields is evaluated gracefully."""
    db = SessionLocal()
    test_opp_id = "OPP-TEST-MISSING-FIELDS"
    try:
        # Create an isolated test opportunity with intentionally missing fields
        test_opp = Opportunity(
            opportunity_id=test_opp_id,
            company_id="COMP-000001",
            primary_contact_id=None,  # Missing contact
            source_lead_id=None,       # Missing source lead
            owner_rep_id="REP-000001",
            opportunity_name="Test Missing Fields Deal",
            pipeline_stage="Qualification",
            deal_value_inr=50000.0,
            probability_pct=20.0,
            expected_close_date=None,  # Missing expected close date
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat()
        )
        db.add(test_opp)
        db.commit()

        res = client.get(f"/api/health/deal/{test_opp_id}", headers=get_auth_headers())
        assert res.status_code == 200
        data = res.json()
        assert data["opportunity_id"] == test_opp_id
        assert 0.0 <= data["health_score"] <= 100.0
        assert 0.0 <= data["risk_score"] <= 100.0
        
        # Verify that missing fields were caught as adverse factors
        factor_names = [f["name"] for f in data["contributing_factors"]]
        assert "Missing Expected Close Date" in factor_names
        assert "Missing Primary Contact" in factor_names
        assert "No Products Attached" in factor_names
        assert "Zero Touchpoints Recorded" in factor_names
    finally:
        # Clean up test opportunity
        db.query(Opportunity).filter(Opportunity.opportunity_id == test_opp_id).delete()
        db.commit()
        db.close()

def test_deal_health_read_only_does_not_modify_records():
    """Verify that calling deal health assessment does not modify any CRM database records."""
    db = SessionLocal()
    opp_before = db.query(Opportunity).filter(Opportunity.opportunity_id == "OPP-000003").first()
    assert opp_before is not None
    updated_at_before = opp_before.updated_at
    deal_value_before = opp_before.deal_value_inr
    stage_before = opp_before.pipeline_stage
    db.close()

    # Invoke deal health via both endpoints
    res1 = client.get("/api/health/deal/OPP-000003", headers=get_auth_headers())
    res2 = client.get("/api/opportunities/OPP-000003/health", headers=get_auth_headers())
    assert res1.status_code == 200
    assert res2.status_code == 200

    db2 = SessionLocal()
    opp_after = db2.query(Opportunity).filter(Opportunity.opportunity_id == "OPP-000003").first()
    assert opp_after.updated_at == updated_at_before
    assert opp_after.deal_value_inr == deal_value_before
    assert opp_after.pipeline_stage == stage_before
    db2.close()
