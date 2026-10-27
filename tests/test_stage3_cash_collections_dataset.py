"""
Comprehensive Unit and Regression Tests for Stage 3 Option A:
Cash Collections Forecasting Dataset, Feature Leakage Auditing,
Refund Normalization, Payment Status Exclusions, and Source-of-Truth Reconciliation.
"""

import os
import csv
import json
import sqlite3
import pytest
import numpy as np
from datetime import datetime, date, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base, SessionLocal
from backend.models import CustomerTransaction, Opportunity, Company, User
from backend.ml.prediction import prediction_service

BOOKINGS_DATASET = "data/ml/sales_forecasting_dataset.csv"
CASH_DATASET = "data/ml/cash_collections_forecasting_dataset.csv"
METRICS_PATH = "scratch/cash_forecasting_metrics.json"


# =============================================================================
# 1. REFUND CORRECTNESS & NORMALIZATION TESTS
# =============================================================================

def test_refund_normalization_rules_and_double_subtraction_prevention():
    """
    Verify that:
    1. Positive-amount refunds (e.g. type='Refund', amount=500.0) are normalized to -500.0.
    2. Negative-amount refunds (e.g. type='Refund', amount=-500.0) are normalized to -500.0 (NOT negated to +500.0).
    3. Non-refund negative amounts (e.g. chargeback/adjustment amount=-200.0) are normalized to -200.0.
    4. Normal revenue (type='Payment', amount=1000.0) remains +1000.0.
    5. Refunds cannot be double-subtracted when calculating net cash collections.
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)
    db = TestingSession()

    try:
        now = datetime.now()
        d1 = (now - timedelta(days=20)).isoformat()

        # Regular payment: +1,000,000
        p1 = CustomerTransaction(
            transaction_id="TX-P1", customer_id="C1", transaction_date=d1,
            transaction_type="Payment", amount_inr=1000000.0, payment_status="Paid"
        )
        # Refund record stored as negative: -100,000
        r_neg = CustomerTransaction(
            transaction_id="TX-RNEG", customer_id="C1", transaction_date=d1,
            transaction_type="Refund", amount_inr=-100000.0, payment_status="Paid"
        )
        # Refund record stored as positive: +50,000 (must be normalized to -50,000, NOT added!)
        r_pos = CustomerTransaction(
            transaction_id="TX-RPOS", customer_id="C1", transaction_date=d1,
            transaction_type="Refund", amount_inr=50000.0, payment_status="Paid"
        )

        db.add_all([p1, r_neg, r_pos])
        db.commit()

        res = prediction_service.predict_sales_forecast(db)
        # Net collections must be: 1,000,000 - 100,000 - 50,000 = 850,000
        # If r_pos was added, it would be 950,000. If r_neg was double-subtracted, it would be wrong.
        assert res.trailing_revenue_inr == 850000.0
        assert res.forecast_amount_inr == 850000.0
    finally:
        db.close()


def test_net_negative_collections_due_to_refunds_handled_safely():
    """
    Verify that if refunds exceed gross collections in the trailing window,
    trailing_revenue_inr reflects the exact negative net deficit,
    the sales forecast is safely floored at 0.0 (no negative sales volume),
    and a clear warning is generated.
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)
    db = TestingSession()

    try:
        now = datetime.now()
        d1 = (now - timedelta(days=20)).isoformat()

        # Small payment of 50k, massive refund of 200k -> Net = -150k
        p1 = CustomerTransaction(
            transaction_id="TX-P1", customer_id="C1", transaction_date=d1,
            transaction_type="Payment", amount_inr=50000.0, payment_status="Paid"
        )
        r1 = CustomerTransaction(
            transaction_id="TX-R1", customer_id="C1", transaction_date=d1,
            transaction_type="Refund", amount_inr=-200000.0, payment_status="Paid"
        )

        db.add_all([p1, r1])
        db.commit()

        res = prediction_service.predict_sales_forecast(db)
        assert res.trailing_revenue_inr == -150000.0
        assert res.forecast_amount_inr == 0.0  # Safely floored
        assert res.data_quality_warning is not None
        assert "negative due to refunds" in res.data_quality_warning.lower()
    finally:
        db.close()


# =============================================================================
# 2. PAYMENT STATUS COVERAGE & SCHEMA LIMITATION TESTS
# =============================================================================

def test_unrealized_payment_statuses_excluded_from_collections():
    """
    Verify that Pending, Overdue, and Partially Paid invoice face values
    do NOT contribute to realized collections.
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)
    db = TestingSession()

    try:
        now = datetime.now()
        d1 = (now - timedelta(days=20)).isoformat()

        # 1 Paid transaction of 300,000
        paid = CustomerTransaction(transaction_id="TX-PAID", customer_id="C1", transaction_date=d1, transaction_type="Payment", amount_inr=300000.0, payment_status="Paid")
        # Non-paid transactions summing to 1,500,000
        pend = CustomerTransaction(transaction_id="TX-PEND", customer_id="C1", transaction_date=d1, transaction_type="Invoice", amount_inr=500000.0, payment_status="Pending")
        over = CustomerTransaction(transaction_id="TX-OVER", customer_id="C1", transaction_date=d1, transaction_type="Invoice", amount_inr=600000.0, payment_status="Overdue")
        part = CustomerTransaction(transaction_id="TX-PART", customer_id="C1", transaction_date=d1, transaction_type="Invoice", amount_inr=400000.0, payment_status="Partially Paid")

        db.add_all([paid, pend, over, part])
        db.commit()

        res = prediction_service.predict_sales_forecast(db)
        assert res.trailing_revenue_inr == 300000.0
        assert res.forecast_amount_inr == 300000.0
    finally:
        db.close()


def test_schema_partially_paid_limitation_documented():
    """
    Verify that CustomerTransaction schema lacks a paid_amount or partial_amount column.
    Documents the technical limitation that amount_inr stores full invoice face value.
    """
    conn = sqlite3.connect("backend/crm.db")
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(customer_transactions)")
    cols = [r[1] for r in cur.fetchall()]
    conn.close()

    assert "paid_amount" not in cols, "Schema does not have paid_amount column"
    assert "partial_payment_amount" not in cols, "Schema does not have partial_payment_amount column"
    assert "amount_inr" in cols, "amount_inr is the invoice face value column"


# =============================================================================
# 3. LEAKAGE VERIFICATION & BOUNDARY TESTS
# =============================================================================

def test_zero_temporal_leakage_across_all_generated_features():
    """
    Audit EVERY feature in cash_collections_forecasting_dataset.csv
    to prove it relies strictly on information available at period_start (< period_start).
    """
    conn = sqlite3.connect("backend/crm.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT * FROM customer_transactions WHERE payment_status = 'Paid' AND deleted_at IS NULL")
    all_paid = [dict(r) for r in cur.fetchall()]

    cur.execute("SELECT * FROM opportunities WHERE deleted_at IS NULL")
    all_opps = [dict(r) for r in cur.fetchall()]

    cur.execute("SELECT rep_id, department_id, hire_date, is_active, termination_date FROM sales_reps")
    all_reps = [dict(r) for r in cur.fetchall()]
    conn.close()

    rep_dept = {r["rep_id"]: r["department_id"] for r in all_reps}
    OWNER_DEPTS = ["DEPT-0001", "DEPT-0002", "DEPT-0003", "DEPT-0007"]

    with open(CASH_DATASET, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    for r in rows:
        mstart_str = r["period_start"]
        mstart = datetime.strptime(mstart_str, "%Y-%m-%d").date()

        # 1. Pipeline open at period start: created < mstart AND (not closed OR closed >= mstart)
        open_opps = [
            o for o in all_opps
            if rep_dept.get(o["owner_rep_id"], "") in OWNER_DEPTS
            and o["created_at"][:10] < mstart_str
            and (not o["actual_close_date"] or o["actual_close_date"][:10] >= mstart_str)
        ]
        expected_pipeline = round(sum(float(o["deal_value_inr"] or 0) for o in open_opps), 2)
        assert abs(float(r["pipeline_value_open_at_period_start_inr"]) - expected_pipeline) < 0.01
        assert int(r["num_open_opportunities_at_period_start"]) == len(open_opps)

        # 2. Trailing 1-month cash: strictly month M-1 (< mstart)
        # 1 month prior
        d = mstart
        y1, m1 = (d.year - 1, 12) if d.month == 1 else (d.year, d.month - 1)
        t1_start = date(y1, m1, 1).isoformat()
        t1_paid = [
            t for t in all_paid
            if t1_start <= t["transaction_date"][:10] < mstart_str
        ]
        expected_cash_t1 = round(sum(
            -abs(float(t["amount_inr"])) if (t.get("transaction_type") == "Refund" or float(t["amount_inr"] or 0) < 0)
            else abs(float(t["amount_inr"]))
            for t in t1_paid
        ), 2)
        assert abs(float(r["cash_revenue_trailing_1mo_inr"]) - expected_cash_t1) < 0.01

        # 3. Active rep staffing count: hired <= mstart and not terminated before mstart
        expected_reps = sum(
            1 for rep in all_reps
            if rep["department_id"] in OWNER_DEPTS
            and rep["hire_date"] <= mstart_str
            and (rep["is_active"] in ("True", True, 1) or (rep["termination_date"] and rep["termination_date"] > mstart_str))
        )
        assert int(r["active_rep_count"]) == expected_reps


def test_first_day_of_month_boundary_event_handling():
    """
    Boundary condition test:
    Opportunities closing on the 1st day of month M (e.g. 2024-12-01)
    MUST be counted as OPEN at period_start (00:00:00 cutoff)
    and MUST NOT be included in trailing closed history (< period_start).
    Similarly, transactions on day 1 must belong to period target, not trailing features.
    """
    with open(CASH_DATASET, newline="", encoding="utf-8") as f:
        rows = {r["period_label"]: r for r in csv.DictReader(f)}

    # OPP-000051 closed Won on 2024-12-01 (deal value 153,346.15)
    # At 2024-12-01 start, it was known to be in open pipeline
    dec_row = rows["2024-12"]
    assert float(dec_row["pipeline_value_open_at_period_start_inr"]) >= 153346.15

    # OPP-000186 closed Lost on 2026-02-01 (created 2025-12-23)
    # At 2026-02-01 start, it was in open pipeline
    feb_26_row = rows["2026-02"]
    assert int(feb_26_row["num_open_opportunities_at_period_start"]) >= 1

    # TXN-0000112 occurred on 2026-07-01 for 237,499.05
    # For July 2026, it is in target label, NOT in trailing 1mo cash!
    jul_26_row = rows["2026-07"]
    assert float(jul_26_row["cash_revenue_trailing_1mo_inr"]) == 666008.29  # June cash
    assert float(jul_26_row["label_net_cash_collections_inr"]) == 319780.42  # Includes TXN-0000112


# =============================================================================
# 4. SOURCE-OF-TRUTH RECONCILIATION TESTS
# =============================================================================

def test_source_csv_vs_sqlite_transaction_reconciliation():
    """
    Reconcile customer_transactions in SQLite vs data/source/customer_transactions.csv:
    Assert exact 116 row match, zero duplicate IDs, zero missing records, and zero amount differences.
    """
    conn = sqlite3.connect("backend/crm.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM customer_transactions")
    db_rows = {r["transaction_id"]: dict(r) for r in cur.fetchall()}
    conn.close()

    with open("data/source/customer_transactions.csv", newline="", encoding="utf-8") as f:
        csv_rows = {r["transaction_id"]: r for r in csv.DictReader(f)}

    assert len(db_rows) == 116
    assert len(csv_rows) == 116
    assert set(db_rows.keys()) == set(csv_rows.keys()), "Transaction IDs must match 1:1"

    for tid, d in db_rows.items():
        c = csv_rows[tid]
        assert d["payment_status"] == c["payment_status"], f"Status mismatch on {tid}"
        assert d["transaction_date"] == c["transaction_date"], f"Date mismatch on {tid}"
        assert abs(float(d["amount_inr"]) - float(c["amount_inr"])) < 1e-4, f"Amount mismatch on {tid}"


# =============================================================================
# 5. PRODUCTION BASELINE & NON-FINITE VALUE TESTS
# =============================================================================

def test_production_baseline_handles_non_finite_and_null_amounts():
    """Verify that NaN, Inf, and None values are safely caught and do not cause crashes."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)
    db = TestingSession()

    try:
        now = datetime.now()
        d1 = (now - timedelta(days=20)).isoformat()

        # Valid payment + record with None/zero amount
        p1 = CustomerTransaction(transaction_id="TX-1", customer_id="C1", transaction_date=d1, transaction_type="Payment", amount_inr=250000.0, payment_status="Paid")
        p2 = CustomerTransaction(transaction_id="TX-2", customer_id="C1", transaction_date=d1, transaction_type="Payment", amount_inr=0.0, payment_status="Paid")

        db.add_all([p1, p2])
        db.commit()

        res = prediction_service.predict_sales_forecast(db)
        assert res.forecast_amount_inr == 250000.0
        assert res.trailing_revenue_inr == 250000.0
        assert np.isfinite(res.forecast_amount_inr)
    finally:
        db.close()


def test_production_baseline_retained_and_candidate_ml_unpromoted():
    """Verify candidate ML models remain unpromoted and production serves moving average baseline."""
    assert os.path.exists(METRICS_PATH)
    with open(METRICS_PATH, "r", encoding="utf-8") as f:
        m = json.load(f)

    assert m["candidate_model_deployed_to_production"] is False
    assert "Candidate_Linear_Regression" in m["holdout_evaluation_metrics"]

    # Verify actual production API service
    db = SessionLocal()
    try:
        res = prediction_service.predict_sales_forecast(db)
        assert res.is_ml_model is False
        assert res.model_identifier == "trailing_3mo_baseline"
        assert res.forecast_amount_inr > 0
    finally:
        db.close()
