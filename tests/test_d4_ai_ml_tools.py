import pytest
from backend.models import User, Lead, Customer, SalesRep
from backend.ai_tools import get_ml_tools

@pytest.fixture
def auth_test_users(db_session):
    manager = db_session.query(User).filter(User.role == "System Admin").first()
    reps = db_session.query(User).filter(User.rep_id != None).limit(2).all()
    rep1 = reps[0]
    rep2 = reps[1]
    return manager, rep1, rep2

@pytest.fixture
def auth_test_entities(db_session, auth_test_users):
    _, rep1, rep2 = auth_test_users
    
    lead1 = db_session.query(Lead).first()
    lead2 = db_session.query(Lead).filter(Lead.lead_id != lead1.lead_id).first()
    
    lead1.assigned_rep_id = rep1.rep_id
    lead2.assigned_rep_id = rep2.rep_id
    
    cust1 = db_session.query(Customer).first()
    cust2 = db_session.query(Customer).filter(Customer.customer_id != cust1.customer_id).first()
    
    cust1.csm_rep_id = rep1.rep_id
    cust2.csm_rep_id = rep2.rep_id
    
    db_session.commit()
    
    return lead1, lead2, cust1, cust2

def test_ml_tools_auth_sales_rep_owns_entity(db_session, auth_test_users, auth_test_entities):
    _, rep1, _ = auth_test_users
    lead1, _, _, _ = auth_test_entities
    tools = get_ml_tools(rep1.user_id, rep1.role)
    
    predict_lead_score = next(t for t in tools if t.name == "predict_lead_score")
    
    res = predict_lead_score.invoke({"lead_id": lead1.lead_id})
    assert "Unauthorized" not in res
    
def test_ml_tools_auth_sales_rep_does_not_own_entity(db_session, auth_test_users, auth_test_entities):
    _, rep1, _ = auth_test_users
    _, lead2, _, _ = auth_test_entities
    tools = get_ml_tools(rep1.user_id, rep1.role)
    
    predict_lead_score = next(t for t in tools if t.name == "predict_lead_score")
    
    res = predict_lead_score.invoke({"lead_id": lead2.lead_id})
    assert "Unauthorized" in res
    
def test_ml_tools_auth_manager_can_access_any_entity(db_session, auth_test_users, auth_test_entities):
    manager, _, _ = auth_test_users
    _, _, _, cust2 = auth_test_entities
    tools = get_ml_tools(manager.user_id, manager.role)
    
    predict_churn = next(t for t in tools if t.name == "predict_churn")
    
    res = predict_churn.invoke({"customer_id": cust2.customer_id})
    assert "Unauthorized" not in res
    
def test_ml_tools_auth_nonexistent_entity(db_session, auth_test_users):
    manager, _, _ = auth_test_users
    tools = get_ml_tools(manager.user_id, manager.role)
    
    customer_segmentation = next(t for t in tools if t.name == "customer_segmentation")
    
    res = customer_segmentation.invoke({"customer_id": "CUST-INVALID"})
    assert "Unauthorized or customer not found" in res

def test_ml_tools_sales_forecasting_no_entity_auth_needed(db_session, auth_test_users):
    _, rep1, _ = auth_test_users
    tools = get_ml_tools(rep1.user_id, rep1.role)
    
    sales_forecasting = next(t for t in tools if t.name == "sales_forecasting")
    
    res = sales_forecasting.invoke({})
    assert "Unauthorized" not in res
