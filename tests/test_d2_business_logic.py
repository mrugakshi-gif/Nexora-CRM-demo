"""D2 Business Logic Tests — Lead Conversion, Opportunity Stage Transitions."""
import os
import pytest

os.environ.setdefault("CRM_AUTH_MODE", "demo")
os.environ.setdefault("CRM_DEMO_PASSWORD", "testpass123")

from fastapi.testclient import TestClient
from tests.conftest import get_test_firebase_token
from backend.main import app
from backend.database import SessionLocal
from backend import models
from backend.services.opportunity_service import PIPELINE_STAGES

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


@pytest.fixture(scope="module")
def test_lead_id():
    """Find a convertible lead (not already converted)."""
    db = SessionLocal()
    try:
        lead = db.query(models.Lead).filter(
            models.Lead.lead_status != "Converted",
            models.Lead.deleted_at == None,
        ).first()
        return lead.lead_id if lead else None
    finally:
        db.close()


@pytest.fixture(scope="module")
def test_rep_id():
    db = SessionLocal()
    try:
        rep = db.query(models.SalesRep).filter(models.SalesRep.is_active == True).first()
        return rep.rep_id if rep else None
    finally:
        db.close()


# -------------------------------------------------------------------------
# Lead Conversion Tests
# -------------------------------------------------------------------------

class TestLeadConversion:
    def test_lead_status_change_with_history(self, auth_headers, test_lead_id):
        if not test_lead_id:
            pytest.skip("No convertible lead available")
        # Change to Qualified first to test intermediate status
        resp = client.patch(
            f"/api/leads/{test_lead_id}/status?new_status=Qualified",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["new_status"] == "Qualified"
        assert "history_id" in data

        # Verify history in DB
        db = SessionLocal()
        try:
            history = db.query(models.LeadStatusHistory).filter(
                models.LeadStatusHistory.history_id == data["history_id"]
            ).first()
            assert history is not None
            assert history.status_to == "Qualified"
        finally:
            db.close()

    def test_lead_conversion_creates_opportunity(self, auth_headers, test_lead_id, test_rep_id):
        if not test_lead_id or not test_rep_id:
            pytest.skip("No lead or rep available")
        resp = client.post(
            f"/api/leads/{test_lead_id}/convert"
            f"?create_opportunity=true&owner_rep_id={test_rep_id}&deal_value_inr=500000",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["lead_status"] == "Converted"
        assert data["opportunity_id"] is not None
        assert data["lead_id"] == test_lead_id
        assert "history_id" in data

        # Verify lead status in DB
        db = SessionLocal()
        try:
            lead = db.query(models.Lead).filter(models.Lead.lead_id == test_lead_id).first()
            assert lead.lead_status == "Converted"
            assert lead.converted_at is not None

            # Verify opportunity has source_lead_id
            opp = db.query(models.Opportunity).filter(
                models.Opportunity.opportunity_id == data["opportunity_id"]
            ).first()
            assert opp is not None
            assert opp.source_lead_id == test_lead_id

            # Verify no transaction was created for this conversion
            tx = db.query(models.CustomerTransaction).filter(
                models.CustomerTransaction.opportunity_id == opp.opportunity_id
            ).first()
            assert tx is None, "Conversion must NOT create a transaction automatically"
        finally:
            db.close()

    def test_double_conversion_rejected(self, auth_headers, test_lead_id):
        if not test_lead_id:
            pytest.skip("No lead available")
        resp = client.post(
            f"/api/leads/{test_lead_id}/convert?create_opportunity=false",
            headers=auth_headers,
        )
        assert resp.status_code == 409  # Already converted

    def test_invalid_status_rejected(self, auth_headers):
        db = SessionLocal()
        try:
            lead = db.query(models.Lead).filter(models.Lead.deleted_at == None).first()
            lead_id = lead.lead_id if lead else None
        finally:
            db.close()
        if not lead_id:
            pytest.skip("No lead")
        resp = client.patch(
            f"/api/leads/{lead_id}/status?new_status=INVALID_STATUS",
            headers=auth_headers,
        )
        assert resp.status_code == 400


# -------------------------------------------------------------------------
# Opportunity Stage Transition Tests
# -------------------------------------------------------------------------

class TestOpportunityStageTransitions:
    @pytest.fixture(scope="class")
    def open_opp_id(self):
        db = SessionLocal()
        try:
            opp = db.query(models.Opportunity).filter(
                models.Opportunity.pipeline_stage == "Qualification",
                models.Opportunity.deleted_at == None,
            ).first()
            return opp.opportunity_id if opp else None
        finally:
            db.close()

    def test_valid_stage_transition(self, auth_headers, open_opp_id):
        if not open_opp_id:
            pytest.skip("No Qualification-stage opportunity")
        resp = client.post(
            f"/api/opportunities/{open_opp_id}/stage-transition",
            json={"new_stage": "Needs Analysis"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["stage_from"] == "Qualification"
        assert data["stage_to"] == "Needs Analysis"
        assert "history_id" in data

        # Verify history in DB
        db = SessionLocal()
        try:
            hist = db.query(models.OpportunityStageHistory).filter(
                models.OpportunityStageHistory.history_id == data["history_id"]
            ).first()
            assert hist is not None
            assert hist.stage_to == "Needs Analysis"
        finally:
            db.close()

    def test_invalid_stage_rejected(self, auth_headers, open_opp_id):
        if not open_opp_id:
            pytest.skip("No open opportunity")
        resp = client.post(
            f"/api/opportunities/{open_opp_id}/stage-transition",
            json={"new_stage": "NONEXISTENT_STAGE"},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_same_stage_rejected(self, auth_headers, open_opp_id):
        if not open_opp_id:
            pytest.skip("No open opportunity")
        # Get current stage first
        db = SessionLocal()
        try:
            opp = db.query(models.Opportunity).filter(
                models.Opportunity.opportunity_id == open_opp_id
            ).first()
            current_stage = opp.pipeline_stage
        finally:
            db.close()
        resp = client.post(
            f"/api/opportunities/{open_opp_id}/stage-transition",
            json={"new_stage": current_stage},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_terminal_stage_blocks_transition(self, auth_headers):
        """Force an opp to Closed Won then try to transition further."""
        db = SessionLocal()
        try:
            opp = db.query(models.Opportunity).filter(
                models.Opportunity.close_outcome == "Won",
                models.Opportunity.deleted_at == None,
            ).first()
            if not opp:
                pytest.skip("No won opportunity in DB")
            opp_id = opp.opportunity_id
        finally:
            db.close()
        resp = client.post(
            f"/api/opportunities/{opp_id}/stage-transition",
            json={"new_stage": "Qualification"},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_product_line_item_calculation(self, auth_headers):
        """Verify line_total_inr = quantity * unit_price * (1 - discount/100)."""
        db = SessionLocal()
        try:
            opp = db.query(models.Opportunity).filter(
                models.Opportunity.deleted_at == None
            ).first()
            product = db.query(models.Product).first()
        finally:
            db.close()
        if not opp or not product:
            pytest.skip("No opportunity/product available")
        resp = client.post(
            f"/api/opportunities/{opp.opportunity_id}/products",
            json={
                "product_id": product.product_id,
                "quantity": 3,
                "unit_price_inr": 10000.0,
                "discount_pct": 10.0,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        expected = round(3 * 10000.0 * (1 - 10.0 / 100), 2)
        assert data["line_total_inr"] == expected
