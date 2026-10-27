from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Any

from ..database import get_db
from ..deps import get_current_user
from ..services import health_service
from ..services import health_service_summary
from ..schemas import AccountHealthResponse, CompanyHealthResponse, ProductHealthResponse, HealthSummaryResponse, DealHealthResponse

router = APIRouter(prefix="/api/health", tags=["health"])

@router.get("/account/summary", response_model=HealthSummaryResponse)
def get_account_health_summary(period: str = "all_time", db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    try:
        return health_service_summary.calculate_account_health_summary(db, current_user, period)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/company/summary", response_model=HealthSummaryResponse)
def get_company_health_summary(period: str = "all_time", db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    try:
        return health_service_summary.calculate_company_health_summary(db, current_user, period)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/product/summary", response_model=HealthSummaryResponse)
def get_product_health_summary(period: str = "all_time", db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    try:
        return health_service_summary.calculate_product_health_summary(db, current_user, period)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/account/{customer_id}", response_model=AccountHealthResponse)
def get_account_health(customer_id: str, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    try:
        return health_service.calculate_account_health(db, customer_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/company/{company_id}", response_model=CompanyHealthResponse)
def get_company_health(company_id: str, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    try:
        return health_service.calculate_company_health(db, company_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/product/{product_id}", response_model=ProductHealthResponse)
def get_product_health(product_id: str, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    try:
        return health_service.calculate_product_health(db, product_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/deal/{opportunity_id}", response_model=DealHealthResponse)
def get_deal_health(opportunity_id: str, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    try:
        return health_service.calculate_deal_health(db, opportunity_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


