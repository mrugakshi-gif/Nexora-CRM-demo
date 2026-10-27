from fastapi.testclient import TestClient
from backend.main import app
from backend.deps import get_current_user
from backend.models import User
import pytest

@pytest.fixture
def auth_client():
    def mock_user():
        return User(user_id="test-admin", email="admin@nexora.com", role="System Admin", is_active=True)
    app.dependency_overrides[get_current_user] = mock_user
    client = TestClient(app)
    yield client
    app.dependency_overrides.pop(get_current_user, None)

def test_dashboard_kpis_endpoint(auth_client):
    res = auth_client.get("/api/analytics/dashboard?start_date=2026-01-01&end_date=2026-12-31")
    assert res.status_code == 200
    data = res.json()
    assert "pipeline_value_inr" in data
    assert "won_revenue_inr" in data
    assert data["total_companies"] == 1200
    assert data["open_opportunities"] == 52
    assert data["won_opportunities"] == 21
    assert data["won_revenue_inr"] == 2845561.05
    assert data["total_opportunities"] == 101

def test_dashboard_pipeline_endpoint(auth_client):
    res = auth_client.get("/api/analytics/opportunities/pipeline?start_date=2026-01-01&end_date=2026-12-31")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) > 0

def test_dashboard_top_customers_endpoint(auth_client):
    res = auth_client.get("/api/analytics/revenue/top-customers?start_date=2026-01-01&end_date=2026-12-31")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) == 5
    for c in data:
        assert "customer_id" in c
        assert "company_name" in c

def test_dashboard_health_summaries(auth_client):
    for endpoint in ["account", "company", "product"]:
        res = auth_client.get(f"/api/health/{endpoint}/summary?period=this_year")
        assert res.status_code == 200
        data = res.json()
        assert "status" in data
        assert "average_score" in data

def test_dashboard_retention_intelligence(auth_client):
    res = auth_client.get("/api/intelligence/next-best-actions/retention?period=this_year")
    assert res.status_code == 200
    data = res.json()
    assert "actions" in data

def test_dashboard_this_month_october_2026(auth_client):
    """Test October 2026 (This Month) exact metrics and stage values."""
    res = auth_client.get("/api/analytics/dashboard?start_date=2026-10-01&end_date=2026-10-31")
    assert res.status_code == 200
    data = res.json()
    # Total companies must remain 1200
    assert data["total_companies"] == 1200
    # 13 open deals closing in October
    assert data["open_opportunities"] == 13
    assert data["total_opportunities"] == 13
    assert data["pipeline_value_inr"] == 1375529.75
    assert data["weighted_pipeline_inr"] == 662500.76
    assert data["won_opportunities"] == 0
    assert data["won_revenue_inr"] == 0.0

    # Pipeline by stage in October 2026
    pipe_res = auth_client.get("/api/analytics/opportunities/pipeline?start_date=2026-10-01&end_date=2026-10-31")
    assert pipe_res.status_code == 200
    stages = pipe_res.json()
    assert len(stages) == 6
    stage_names = {s["stage"] for s in stages}
    assert "Proposal" in stage_names
    assert "Qualification" in stage_names
    assert "Negotiation" in stage_names
    total_val = sum(s["total_value_inr"] for s in stages)
    assert round(total_val, 2) == 1375529.75

def test_dashboard_this_quarter_q4_2026(auth_client):
    """Test Q4 2026 (This Quarter) exact metrics."""
    res = auth_client.get("/api/analytics/dashboard?start_date=2026-10-01&end_date=2026-12-31")
    assert res.status_code == 200
    data = res.json()
    assert data["total_companies"] == 1200
    assert data["open_opportunities"] == 21
    assert data["total_opportunities"] == 21
    assert data["pipeline_value_inr"] == 2830765.9
    assert data["weighted_pipeline_inr"] == 1041151.9

    pipe_res = auth_client.get("/api/analytics/opportunities/pipeline?start_date=2026-10-01&end_date=2026-12-31")
    assert pipe_res.status_code == 200
    stages = pipe_res.json()
    assert len(stages) == 6
    total_val = sum(s["total_value_inr"] for s in stages)
    assert round(total_val, 2) == 2830765.9

def test_dashboard_last_month_september_2026(auth_client):
    """Test September 2026 (Last Month) metrics."""
    res = auth_client.get("/api/analytics/dashboard?start_date=2026-09-01&end_date=2026-09-30")
    assert res.status_code == 200
    data = res.json()
    assert data["total_companies"] == 1200
    assert data["open_opportunities"] == 6
    assert data["won_opportunities"] == 3
    assert data["won_revenue_inr"] == 435994.1
    assert data["total_opportunities"] == 18

    # Top customers in September 2026
    top_cust = auth_client.get("/api/analytics/revenue/top-customers?start_date=2026-09-01&end_date=2026-09-30")
    assert top_cust.status_code == 200
    custs = top_cust.json()
    assert len(custs) == 4

def test_dashboard_all_time(auth_client):
    """Test All Time (no start_date / end_date)."""
    res = auth_client.get("/api/analytics/dashboard")
    assert res.status_code == 200
    data = res.json()
    assert data["total_companies"] == 1200
    assert data["open_opportunities"] == 89
    assert data["won_opportunities"] == 51
    assert data["total_opportunities"] == 199
    assert data["pipeline_value_inr"] == 11170244.0
    assert data["won_revenue_inr"] == 6947256.1

def test_date_boundary_exact_match_and_transitions(auth_client):
    """Test exact start/end date boundary filtering."""
    # OPP-000195 has expected_close_date = '2026-10-01'
    res_on_day = auth_client.get("/api/analytics/dashboard?start_date=2026-10-01&end_date=2026-10-01")
    assert res_on_day.status_code == 200
    data_on_day = res_on_day.json()
    assert data_on_day["open_opportunities"] == 1
    assert data_on_day["pipeline_value_inr"] == 85499.05

    # Day immediately before: 2026-09-30
    res_before = auth_client.get("/api/analytics/dashboard?start_date=2026-09-30&end_date=2026-09-30")
    assert res_before.status_code == 200
    data_before = res_before.json()
    # OPP-000195 should NOT be present on 2026-09-30
    assert data_before["pipeline_value_inr"] != 85499.05

def test_empty_period(auth_client):
    """Test a period with no matching records."""
    res = auth_client.get("/api/analytics/dashboard?start_date=2029-01-01&end_date=2029-01-31")
    assert res.status_code == 200
    data = res.json()
    assert data["total_companies"] == 1200
    assert data["total_opportunities"] == 0
    assert data["open_opportunities"] == 0
    assert data["won_opportunities"] == 0
    assert data["pipeline_value_inr"] == 0.0
    assert data["won_revenue_inr"] == 0.0

def test_pagination_limit_alias(auth_client):
    """Test that pagination params accept limit alias."""
    res = auth_client.get("/api/activities?limit=50")
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) == 50
    assert data["page_size"] == 50
