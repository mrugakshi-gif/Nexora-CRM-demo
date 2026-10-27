"""Analytics router — aggregated CRM metrics computed from the database."""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..deps import get_current_active_user
from ..services.analytics_service import (
    get_dashboard_kpis,
    get_lead_funnel,
    get_opportunity_pipeline,
    get_revenue_by_month,
    get_support_summary,
    get_top_customers,
    get_top_products,
    get_companies_by_state
)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/dashboard")
def dashboard_kpis(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """Top-level dashboard KPIs: companies, leads, opps, customers, revenue, support."""
    return get_dashboard_kpis(db, start_date, end_date)


@router.get("/leads/funnel")
def lead_funnel(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """Lead counts grouped by status."""
    return get_lead_funnel(db, start_date, end_date)


@router.get("/opportunities/pipeline")
def opportunity_pipeline(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """Opportunity count and value grouped by pipeline stage."""
    return get_opportunity_pipeline(db, start_date, end_date)


@router.get("/revenue/monthly")
def monthly_revenue(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """Monthly revenue aggregated from paid transactions."""
    return get_revenue_by_month(db, start_date, end_date)


@router.get("/revenue/top-customers")
def top_customers(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """Top customers by transaction revenue."""
    return get_top_customers(db, start_date, end_date, limit)


@router.get("/revenue/top-products")
def top_products(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """Top products by opportunity revenue."""
    return get_top_products(db, start_date, end_date, limit)


@router.get("/support/summary")
def support_summary(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """Support case counts by status and average satisfaction score."""
    return get_support_summary(db, start_date, end_date)

@router.get("/companies/state")
def companies_by_state(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """Company count grouped by state."""
    return get_companies_by_state(db, start_date, end_date)
