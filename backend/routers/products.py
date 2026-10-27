"""Products router — full CRUD with soft-delete."""
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user, RoleChecker

from ..query_params import pagination_params, paginate_query, PageParams, PaginatedResponse

router = APIRouter(prefix="/api/products", tags=["products"])

SORT_FIELDS = {
    "product_name": models.Product.product_name,
    "product_category": models.Product.product_category,
    "list_price_inr": models.Product.list_price_inr,
}

@router.get("", response_model=PaginatedResponse)
def list_products(
    category: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    params: PageParams = Depends(pagination_params),
):
    q = db.query(models.Product).filter(models.Product.deleted_at == None)
    if category:
        q = q.filter(models.Product.product_category == category)
    if is_active is not None:
        q = q.filter(models.Product.is_active == is_active)
    if search:
        q = q.filter(models.Product.product_name.ilike(f"%{search}%"))
    
    return paginate_query(q, params, SORT_FIELDS, schemas.ProductResponse)


@router.get("/{product_id}", response_model=schemas.ProductResponse)
def get_product(
    product_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    obj = db.query(models.Product).filter(
        models.Product.product_id == product_id,
        models.Product.deleted_at == None
    ).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Product not found")
    return obj


@router.post("", response_model=schemas.ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    data: schemas.ProductCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    now = datetime.utcnow().isoformat()
    obj = models.Product(
        **data.dict(),
        product_id=f"PROD-{uuid.uuid4().hex[:6].upper()}",
        updated_at=now,
        created_by=current_user.user_id,
        updated_by=current_user.user_id,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/{product_id}", response_model=schemas.ProductResponse)
def update_product(
    product_id: str,
    data: schemas.ProductUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    obj = db.query(models.Product).filter(
        models.Product.product_id == product_id,
        models.Product.deleted_at == None
    ).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Product not found")
        
    for k, v in data.dict(exclude_unset=True).items():
        setattr(obj, k, v)
        
    obj.updated_at = datetime.utcnow().isoformat()
    obj.updated_by = current_user.user_id
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{product_id}", status_code=status.HTTP_200_OK)
def delete_product(
    product_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(RoleChecker(["Admin", "System Admin"])),
):
    obj = db.query(models.Product).filter(
        models.Product.product_id == product_id,
        models.Product.deleted_at == None
    ).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Product not found")
    obj.deleted_at = datetime.utcnow().isoformat()
    obj.updated_by = current_user.user_id
    db.commit()
    return {"message": "Product archived", "product_id": product_id}
