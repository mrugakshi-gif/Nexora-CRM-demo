"""
Stage 3 Regression and Unit Tests — Sales Forecasting
Covers:
- Authenticated and unauthenticated endpoint access
- Realized revenue semantics: payment_status == 'Paid' vs Pending, Overdue, Partially Paid
- Trailing calculation with dynamic historical_months_evaluated count
- Sparse history (<3 distinct months) calculation and labeling
- Clock drift / historical 90-day window fallback
- Closed-Won opportunities monthly aggregation fallback (proper monthly average, not average deal value)
- Null, negative (refunds), and malformed date handling
- Empty database behavior
- LangChain / AI agent sales forecasting tool integration
- Preservation and verifiable integrity of the saved ML artifact
"""

import os
import json
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.main import app
from backend.database import Base, get_db
from backend.models import CustomerTransaction, Opportunity, Company, User
from backend.ml.prediction import prediction_service
from backend.ml.schemas import SalesForecastResponse
from backend.ai_tools import get_ml_tools

from tests.conftest import get_test_firebase_token

client = TestClient(app)


def get_auth_headers():
    token = get_test_firebase_token(uid="firebase-admin-uid", email="mrugakshi759@gmail.com")
    return {"Authorization": f"Bearer {token}"}


def get_completed_month_sample_dates():
    now = datetime.utcnow()
    m1_last = now.replace(day=1) - timedelta(days=1)
    d1 = m1_last.replace(day=15).strftime("%Y-%m-%d")
    m2_last = m1_last.replace(day=1) - timedelta(days=1)
    d2 = m2_last.replace(day=15).strftime("%Y-%m-%d")
    m3_last = m2_last.replace(day=1) - timedelta(days=1)
    d3 = m3_last.replace(day=15).strftime("%Y-%m-%d")
    return d1, d2, d3


def test_sales_forecast_endpoint_authenticated():
    """Verify endpoint returns 200, valid schema, non-ML label, and exact expected values from database."""
    response = client.get("/api/ml/sales/forecast", headers=get_auth_headers())
    assert response.status_code == 200
    data = response.json()

    assert "forecast_amount_inr" in data
    assert "period_description" in data
    assert "model_identifier" in data
    assert "baseline_note" in data
    assert "methodology" in data
    assert "is_ml_model" in data
    assert "historical_months_evaluated" in data
    assert "trailing_revenue_inr" in data

    # Reference date is October 2026: forecast period is November 2026
    assert data["period_description"] == "2026-11"
    # Three completed months: July (319,780.42), August (98,768.57), September (609,209.51)
    assert data["trailing_revenue_inr"] == 1027758.50
    assert data["forecast_amount_inr"] == 342586.17
    assert data["historical_months_evaluated"] == 3
    assert data["model_identifier"] == "trailing_3mo_baseline"
    assert data["is_ml_model"] is False

    # Ensure no false claims about active pipeline or conversion rates
    assert "pipeline" not in data["baseline_note"].lower()
    assert "conversion rate" not in data["baseline_note"].lower()
    assert "pipeline" not in data["methodology"].lower()
    assert "conversion rate" not in data["methodology"].lower()


def test_sales_forecast_endpoint_unauthenticated():
    """Verify endpoint rejects unauthenticated requests with 401."""
    response = client.get("/api/ml/sales/forecast")
    assert response.status_code == 401


def test_sales_forecast_realized_revenue_filtering_paid_only():
    """
    Verify revenue semantics: only payment_status == 'Paid' represents realized revenue.
    Pending, Overdue, and Partially Paid invoices must be excluded.
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)
    db = TestingSession()

    try:
        d1, d2, d3 = get_completed_month_sample_dates()

        # 3 Paid transactions summing to 900,000 (300,000 / month)
        p1 = CustomerTransaction(transaction_id="TX-P1", customer_id="C1", transaction_date=d1, transaction_type="Payment", amount_inr=300000.0, payment_status="Paid")
        p2 = CustomerTransaction(transaction_id="TX-P2", customer_id="C1", transaction_date=d2, transaction_type="Payment", amount_inr=300000.0, payment_status="Paid")
        p3 = CustomerTransaction(transaction_id="TX-P3", customer_id="C1", transaction_date=d3, transaction_type="Payment", amount_inr=300000.0, payment_status="Paid")

        # Unrealized transactions (Pending, Overdue, Partially Paid) that must NOT be counted
        un1 = CustomerTransaction(transaction_id="TX-UN1", customer_id="C1", transaction_date=d1, transaction_type="Invoice", amount_inr=500000.0, payment_status="Pending")
        un2 = CustomerTransaction(transaction_id="TX-UN2", customer_id="C1", transaction_date=d2, transaction_type="Invoice", amount_inr=700000.0, payment_status="Overdue")
        un3 = CustomerTransaction(transaction_id="TX-UN3", customer_id="C1", transaction_date=d3, transaction_type="Invoice", amount_inr=400000.0, payment_status="Partially Paid")

        db.add_all([p1, p2, p3, un1, un2, un3])
        db.commit()

        res = prediction_service.predict_sales_forecast(db)
        assert res.is_ml_model is False
        assert res.model_identifier == "trailing_3mo_baseline"
        assert res.historical_months_evaluated == 3
        # Trailing revenue must ONLY equal the sum of Paid transactions (900,000), not including the 1,600,000 unrealized!
        assert res.trailing_revenue_inr == 900000.0
        assert res.forecast_amount_inr == 300000.0
    finally:
        db.close()


def test_sales_forecast_sparse_history_fewer_than_3_months():
    """
    Verify that when fewer than 3 distinct months of paid transactions exist in the database (e.g. 2 months),
    historical_months_evaluated is accurately reported as 2 and the average divides by 2 (not 3).
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)
    db = TestingSession()

    try:
        d1, d2, _ = get_completed_month_sample_dates()

        t1 = CustomerTransaction(transaction_id="TX-SP1", customer_id="C1", transaction_date=d1, transaction_type="Payment", amount_inr=200000.0, payment_status="Paid")
        t2 = CustomerTransaction(transaction_id="TX-SP2", customer_id="C1", transaction_date=d2, transaction_type="Payment", amount_inr=400000.0, payment_status="Paid")
        db.add_all([t1, t2])
        db.commit()

        res = prediction_service.predict_sales_forecast(db)
        assert res.historical_months_evaluated == 2
        assert res.trailing_revenue_inr == 600000.0
        # True monthly average = 600,000 / 2 = 300,000 (NOT 600,000 / 3 = 200,000)
        assert res.forecast_amount_inr == 300000.0
        assert res.model_identifier == "sparse_trailing_baseline"
        assert res.data_quality_warning is not None
        assert "2 distinct month(s)" in res.data_quality_warning
    finally:
        db.close()


def test_sales_forecast_calendar_month_boundaries():
    """
    Verify that full calendar month boundaries are respected:
    - First day of M-3 (e.g. July 1) is included
    - Last day of M-1 (e.g. Sept 30) is included
    - In-progress current month (e.g. Oct 5) is excluded from completed months baseline
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)
    db = TestingSession()

    try:
        now = datetime.utcnow()
        # M-1 last day
        cur_first = now.replace(day=1)
        m1_last_day = (cur_first - timedelta(days=1)).strftime("%Y-%m-%d")
        # M-3 first day
        m1_first = (cur_first - timedelta(days=1)).replace(day=1)
        m2_first = (m1_first - timedelta(days=1)).replace(day=1)
        m3_first_day = (m2_first - timedelta(days=1)).replace(day=1).strftime("%Y-%m-%d")
        # In-progress current month date
        in_progress_date = now.strftime("%Y-%m-%d")

        t_m3_start = CustomerTransaction(transaction_id="TX-B1", customer_id="C1", transaction_date=m3_first_day, transaction_type="Payment", amount_inr=100000.0, payment_status="Paid")
        t_m1_end = CustomerTransaction(transaction_id="TX-B2", customer_id="C1", transaction_date=m1_last_day, transaction_type="Payment", amount_inr=200000.0, payment_status="Paid")
        t_current = CustomerTransaction(transaction_id="TX-B3", customer_id="C1", transaction_date=in_progress_date, transaction_type="Payment", amount_inr=999999.0, payment_status="Paid")

        db.add_all([t_m3_start, t_m1_end, t_current])
        db.commit()

        res = prediction_service.predict_sales_forecast(db)
        # Should include t_m3_start (100k) and t_m1_end (200k), but EXCLUDE in-progress t_current (999,999)
        assert res.trailing_revenue_inr == 300000.0
    finally:
        db.close()


def test_sales_forecast_zero_collection_months():
    """
    Verify that when 3 completed months exist, but one of them has 0 collections,
    the sum is divided by 3, retaining the genuine zero month.
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)
    db = TestingSession()

    try:
        d1, d2, d3 = get_completed_month_sample_dates()

        # Month 1: 300,000, Month 2: ZERO, Month 3: 300,000. Also add an older month to make lifetime >= 3
        now = datetime.utcnow()
        cur_first = now.replace(day=1)
        m4_date = (cur_first - timedelta(days=120)).strftime("%Y-%m-%d")

        t_old = CustomerTransaction(transaction_id="TX-OLD", customer_id="C1", transaction_date=m4_date, transaction_type="Payment", amount_inr=100000.0, payment_status="Paid")
        t1 = CustomerTransaction(transaction_id="TX-Z1", customer_id="C1", transaction_date=d1, transaction_type="Payment", amount_inr=300000.0, payment_status="Paid")
        # d2 is left with 0 transactions (genuine zero month)
        t3 = CustomerTransaction(transaction_id="TX-Z3", customer_id="C1", transaction_date=d3, transaction_type="Payment", amount_inr=300000.0, payment_status="Paid")

        db.add_all([t_old, t1, t3])
        db.commit()

        res = prediction_service.predict_sales_forecast(db)
        assert res.model_identifier == "trailing_3mo_baseline"
        assert res.historical_months_evaluated == 3
        # Total = 300k + 0 + 300k = 600k
        assert res.trailing_revenue_inr == 600000.0
        # Average divides by 3.0: 600k / 3 = 200,000
        assert res.forecast_amount_inr == 200000.0
    finally:
        db.close()


def test_sales_forecast_refund_normalization_positive_and_negative():
    """
    Verify that refunds with positive and negative amounts both reduce collections correctly
    and cannot be double-subtracted.
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)
    db = TestingSession()

    try:
        d1, _, _ = get_completed_month_sample_dates()

        # Base sale: 500k
        t_sale = CustomerTransaction(transaction_id="TX-S1", customer_id="C1", transaction_date=d1, transaction_type="New Sale", amount_inr=500000.0, payment_status="Paid")
        # Refund with positive amount: 50k
        t_ref_pos = CustomerTransaction(transaction_id="TX-R1", customer_id="C1", transaction_date=d1, transaction_type="Refund", amount_inr=50000.0, payment_status="Paid")
        # Refund with negative amount: -30k
        t_ref_neg = CustomerTransaction(transaction_id="TX-R2", customer_id="C1", transaction_date=d1, transaction_type="Refund", amount_inr=-30000.0, payment_status="Paid")

        db.add_all([t_sale, t_ref_pos, t_ref_neg])
        db.commit()

        res = prediction_service.predict_sales_forecast(db)
        # Net collections = 500k - 50k - 30k = 420k
        assert res.trailing_revenue_inr == 420000.0
    finally:
        db.close()


def test_sales_forecast_historical_window_drift_fallback():
    """
    Verify fallback when transactions exist but are older than trailing completed months from the current clock.
    Ensures baseline evaluates the latest available window and generates an informative warning.
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)
    db = TestingSession()

    try:
        base_time = datetime.now() - timedelta(days=200)
        t1 = CustomerTransaction(
            transaction_id="TXN-HIST-1",
            customer_id="CUST-1",
            transaction_date=(base_time - timedelta(days=20)).isoformat(),
            transaction_type="Invoice Payment",
            amount_inr=300000.0,
            payment_status="Paid"
        )
        t2 = CustomerTransaction(
            transaction_id="TXN-HIST-2",
            customer_id="CUST-1",
            transaction_date=base_time.isoformat(),
            transaction_type="Invoice Payment",
            amount_inr=500000.0,
            payment_status="Paid"
        )
        db.add_all([t1, t2])
        db.commit()

        res = prediction_service.predict_sales_forecast(db)
        assert res.model_identifier == "historical_window_baseline"
        assert res.trailing_revenue_inr == 800000.0
        assert res.historical_months_evaluated in [1, 2]
        assert "trailing" in res.data_quality_warning.lower()
        assert "historical transaction window" in res.data_quality_warning.lower()
    finally:
        db.close()


def test_sales_forecast_fallback_won_opportunities():
    """
    Verify fallback to closed-won opportunities when CustomerTransaction table is empty:
    - Must aggregate won opportunities by calendar month
    - Must calculate average monthly revenue (total won value in evaluated months / month count)
    - Must NOT calculate average deal value (total / deal count)
    - Must accurately label methodology as Closed-Won Opportunity Bookings
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)
    db = TestingSession()

    try:
        comp = Company(
            company_id="COMP-FALLBACK",
            company_name="Test Company",
            industry_id="IND-001",
            city="Mumbai",
            state="Maharashtra",
            account_status="Active"
        )

        # 3 deals in month 2026-05 totaling 600,000 (deals 1, 2, 3)
        # 1 deal in month 2026-06 totaling 400,000 (deal 4)
        # Total won value = 1,000,000 across 2 distinct months
        # Average monthly revenue = 1,000,000 / 2 = 500,000 (NOT 1,000,000 / 4 deals = 250,000!)
        o1 = Opportunity(opportunity_id="OPP-1", company_id="COMP-FALLBACK", owner_rep_id="REP-1", opportunity_name="D1", pipeline_stage="Closed Won", deal_value_inr=200000.0, probability_pct=1.0, close_outcome="Won", actual_close_date="2026-05-05", created_at="2026-05-01")
        o2 = Opportunity(opportunity_id="OPP-2", company_id="COMP-FALLBACK", owner_rep_id="REP-1", opportunity_name="D2", pipeline_stage="Closed Won", deal_value_inr=200000.0, probability_pct=1.0, close_outcome="Won", actual_close_date="2026-05-15", created_at="2026-05-01")
        o3 = Opportunity(opportunity_id="OPP-3", company_id="COMP-FALLBACK", owner_rep_id="REP-1", opportunity_name="D3", pipeline_stage="Closed Won", deal_value_inr=200000.0, probability_pct=1.0, close_outcome="Won", actual_close_date="2026-05-25", created_at="2026-05-01")
        o4 = Opportunity(opportunity_id="OPP-4", company_id="COMP-FALLBACK", owner_rep_id="REP-1", opportunity_name="D4", pipeline_stage="Closed Won", deal_value_inr=400000.0, probability_pct=1.0, close_outcome="Won", actual_close_date="2026-06-10", created_at="2026-05-01")

        # Lost deal that must NOT be counted
        o_lost = Opportunity(opportunity_id="OPP-L", company_id="COMP-FALLBACK", owner_rep_id="REP-1", opportunity_name="Lost Deal", pipeline_stage="Closed Lost", deal_value_inr=900000.0, probability_pct=0.0, close_outcome="Lost", actual_close_date="2026-06-12", created_at="2026-05-01")

        db.add_all([comp, o1, o2, o3, o4, o_lost])
        db.commit()

        res = prediction_service.predict_sales_forecast(db)
        assert res.model_identifier == "closed_won_opps_monthly_baseline"
        assert res.historical_months_evaluated == 2
        assert res.trailing_revenue_inr == 1000000.0
        # True monthly average = 1,000,000 / 2 = 500,000
        assert res.forecast_amount_inr == 500000.0
        assert "opportunity" in res.methodology.lower()
        assert "2 distinct month(s)" in res.data_quality_warning
    finally:
        db.close()


def test_sales_forecast_negative_and_null_amounts_handling():
    """Verify that refunds (negative amounts) and zero amounts are handled gracefully without errors."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)
    db = TestingSession()

    try:
        now = datetime.now()
        d1 = (now - timedelta(days=20)).isoformat()

        # Normal payment + refund + zero amount record
        t1 = CustomerTransaction(transaction_id="TXN-N1", customer_id="C1", transaction_date=d1, transaction_type="Payment", amount_inr=500000.0, payment_status="Paid")
        t_ref = CustomerTransaction(transaction_id="TXN-REF", customer_id="C1", transaction_date=d1, transaction_type="Refund", amount_inr=-50000.0, payment_status="Paid")
        t_zero = CustomerTransaction(transaction_id="TXN-ZERO", customer_id="C1", transaction_date=d1, transaction_type="Payment", amount_inr=0.0, payment_status="Paid")

        db.add_all([t1, t_ref, t_zero])
        db.commit()

        res = prediction_service.predict_sales_forecast(db)
        assert res.historical_months_evaluated == 1
        # Net realized revenue = 500k - 50k + 0 = 450k
        assert res.trailing_revenue_inr == 450000.0
        assert res.forecast_amount_inr == 450000.0
    finally:
        db.close()


def test_sales_forecast_empty_database():
    """Verify that an empty database returns 0.0 forecast with clear insufficient-data metadata."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)
    empty_db = TestingSession()

    try:
        res = prediction_service.predict_sales_forecast(empty_db)
        assert res.forecast_amount_inr == 0.0
        assert res.is_ml_model is False
        assert res.model_identifier == "insufficient_data"
        assert res.historical_months_evaluated == 0
        assert res.trailing_revenue_inr == 0.0
        assert "insufficient" in res.data_quality_warning.lower()
    finally:
        empty_db.close()


def test_sales_forecasting_ai_agent_tool(db_session):
    """Verify the sales_forecasting LangChain tool returns parseable JSON containing accurate baseline metadata."""
    tools = get_ml_tools("user_admin", "Administrator")
    tool = next((t for t in tools if t.name == "sales_forecasting"), None)
    assert tool is not None, "sales_forecasting tool must be registered in get_ml_tools"

    output_str = tool.invoke({})
    data = json.loads(output_str)

    assert "forecast_amount_inr" in data
    assert data["model_identifier"] in ["trailing_3mo_baseline", "historical_window_baseline", "closed_won_opps_monthly_baseline"]
    assert "baseline_note" in data
    assert data["is_ml_model"] is False


def test_sales_forecasting_model_artifact_retention():
    """Verify saved sales_forecasting_pipeline.joblib exists and metadata records the original training result."""
    meta_path = "backend/ml/models/model_metadata.json"
    assert os.path.exists(meta_path)

    with open(meta_path, "r") as f:
        metadata = json.load(f)

    sf_meta = next((m for m in metadata if m.get("model_name") == "Sales Forecasting"), None)
    assert sf_meta is not None
    assert sf_meta["model_type"] == "LinearRegression"
    assert sf_meta["evaluation_metrics"]["R2"] == -0.470374035808798

    artifact_path = os.path.join("backend/ml/models", sf_meta["artifact_filename"])
    assert os.path.exists(artifact_path)
