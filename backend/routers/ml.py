from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..deps import get_current_user
from ..ml.prediction import prediction_service
from ..ml.schemas import (LeadConversionResponse, LeadScoringResponse, CustomerSegmentationResponse, CustomerChurnResponse, SalesForecastResponse, LeadIntelligenceAggregateResponse, CustomerRiskAggregateResponse, CustomerSegmentDistributionResponse)

router = APIRouter(prefix="/api/ml", tags=["ML Predictions"])

def _authorize(db: Session, user, entity_id: str, entity_type: str):
    if user.role in ["Admin", "Manager", "System Admin", "Sales Manager"]:
        return
    
    if entity_type == "lead":
        from ..models import Lead
        entity = db.query(Lead).filter(Lead.lead_id == entity_id).first()
        if entity and entity.assigned_rep_id != user.rep_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this lead")
    elif entity_type == "customer":
        from ..models import Customer
        entity = db.query(Customer).filter(Customer.customer_id == entity_id).first()
        if entity and entity.csm_rep_id != user.rep_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this customer")

@router.get("/leads/{lead_id}/conversion", response_model=LeadConversionResponse)
def get_lead_conversion_prediction(lead_id: str, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    try:
        _authorize(db, current_user, lead_id, "lead")
        return prediction_service.predict_lead_conversion(db, lead_id)
    except ValueError as e:
        if str(e) == "Lead not found":
            raise HTTPException(status_code=404, detail="Lead not found")
        raise HTTPException(status_code=500, detail=str(e))
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")

@router.get("/leads/{lead_id}/score", response_model=LeadScoringResponse)
def get_lead_scoring_prediction(lead_id: str, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    try:
        _authorize(db, current_user, lead_id, "lead")
        return prediction_service.predict_lead_scoring(db, lead_id)
    except ValueError as e:
        if str(e) == "Lead not found":
            raise HTTPException(status_code=404, detail="Lead not found")
        raise HTTPException(status_code=500, detail=str(e))
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")

@router.get("/customers/{customer_id}/segment", response_model=CustomerSegmentationResponse)
def get_customer_segmentation(customer_id: str, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    try:
        _authorize(db, current_user, customer_id, "customer")
        return prediction_service.predict_customer_segmentation(db, customer_id)
    except ValueError as e:
        if str(e) == "Customer not found":
            raise HTTPException(status_code=404, detail="Customer not found")
        raise HTTPException(status_code=500, detail=str(e))
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")

@router.get("/customers/{customer_id}/churn", response_model=CustomerChurnResponse)
def get_customer_churn(customer_id: str, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    try:
        _authorize(db, current_user, customer_id, "customer")
        return prediction_service.predict_customer_churn(db, customer_id)
    except ValueError as e:
        if str(e) == "Customer not found":
            raise HTTPException(status_code=404, detail="Customer not found")
        raise HTTPException(status_code=500, detail=str(e))
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")

@router.get("/sales/forecast", response_model=SalesForecastResponse)
def get_sales_forecast(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    try:
        return prediction_service.predict_sales_forecast(db)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")

@router.get("/aggregate/leads", response_model=LeadIntelligenceAggregateResponse)
def get_aggregate_leads(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    try:
        return prediction_service.predict_aggregate_leads(db, current_user)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")

@router.get("/aggregate/customers/risk", response_model=CustomerRiskAggregateResponse)
def get_aggregate_customers_risk(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    try:
        return prediction_service.predict_aggregate_customers_risk(db, current_user)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")

@router.get("/aggregate/customers/segments", response_model=CustomerSegmentDistributionResponse)
def get_aggregate_customers_segments(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    try:
        return prediction_service.predict_aggregate_segments(db, current_user)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")
