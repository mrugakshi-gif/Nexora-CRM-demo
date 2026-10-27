"""Reference Routers — read-only."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user

# --- Industries ---
router_industries = APIRouter(prefix="/api/industries", tags=["industries"])

@router_industries.get("", response_model=List[schemas.IndustryResponse])
def list_industries(
    skip: int = Query(0, ge=0), limit: int = Query(100, le=500),
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user),
):
    return db.query(models.Industry).order_by(models.Industry.industry_name).offset(skip).limit(limit).all()

# --- Territories ---
router_territories = APIRouter(prefix="/api/territories", tags=["territories"])

@router_territories.get("", response_model=List[schemas.TerritoryResponse])
def list_territories(
    skip: int = Query(0, ge=0), limit: int = Query(100, le=500),
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user),
):
    return db.query(models.Territory).order_by(models.Territory.territory_name).offset(skip).limit(limit).all()

# --- Departments ---
router_departments = APIRouter(prefix="/api/departments", tags=["departments"])

@router_departments.get("", response_model=List[schemas.DepartmentResponse])
def list_departments(
    skip: int = Query(0, ge=0), limit: int = Query(100, le=500),
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user),
):
    return db.query(models.Department).order_by(models.Department.department_name).offset(skip).limit(limit).all()

# --- Lead Sources ---
router_lead_sources = APIRouter(prefix="/api/lead_sources", tags=["lead_sources"])

@router_lead_sources.get("", response_model=List[schemas.LeadSourceResponse])
def list_lead_sources(
    skip: int = Query(0, ge=0), limit: int = Query(100, le=500),
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user),
):
    return db.query(models.LeadSource).order_by(models.LeadSource.source_name).offset(skip).limit(limit).all()
