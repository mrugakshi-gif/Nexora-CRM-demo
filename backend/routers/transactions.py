"""Customer Transactions router — read-only with soft-delete and pagination."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_active_user, RoleChecker
from ..rbac import apply_rbac_filter, verify_assignment
from ..query_params import pagination_params, paginate_query, PageParams, PaginatedResponse

router = APIRouter(prefix="/api/transactions", tags=["transactions"])

SORT_FIELDS = {
    "transaction_date": models.CustomerTransaction.transaction_date,
    "amount_inr": models.CustomerTransaction.amount_inr,
    "payment_status": models.CustomerTransaction.payment_status,
}


@router.get("", response_model=PaginatedResponse)
def list_transactions(
    customer_id: Optional[str] = None,
    opportunity_id: Optional[str] = None,
    payment_status: Optional[str] = None,
    transaction_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
    params: PageParams = Depends(pagination_params),
):
    q = db.query(models.CustomerTransaction).filter(
        models.CustomerTransaction.deleted_at == None  # noqa: E711
    )
    q = q.join(models.Customer, models.CustomerTransaction.customer_id == models.Customer.customer_id)
    q = apply_rbac_filter(db, q, current_user, models.Customer, 'csm_rep_id')
    if customer_id:
        q = q.filter(models.CustomerTransaction.customer_id == customer_id)
    if opportunity_id:
        q = q.filter(models.CustomerTransaction.opportunity_id == opportunity_id)
    if payment_status:
        q = q.filter(models.CustomerTransaction.payment_status == payment_status)
    if transaction_type:
        q = q.filter(models.CustomerTransaction.transaction_type == transaction_type)
    return paginate_query(q, params, SORT_FIELDS, schemas.CustomerTransactionResponse)


@router.get("/summary", response_model=schemas.CustomerTransactionSummary)
def get_transaction_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    from sqlalchemy import func
    
    # Base query for active transactions
    base_q = db.query(models.CustomerTransaction).filter(
        models.CustomerTransaction.deleted_at == None
    )
    
    # Calculate aggregates
    total_tx = base_q.count()
    total_rev = db.query(func.sum(models.CustomerTransaction.amount_inr)).filter(
        models.CustomerTransaction.deleted_at == None
    ).scalar() or 0.0
    paid_tx = base_q.filter(models.CustomerTransaction.payment_status == "Paid").count()
    
    avg_val = total_rev / total_tx if total_tx > 0 else 0.0
    
    # Group by transaction_type
    counts = db.query(
        models.CustomerTransaction.transaction_type, 
        func.count(models.CustomerTransaction.transaction_id)
    ).filter(
        models.CustomerTransaction.deleted_at == None
    ).group_by(models.CustomerTransaction.transaction_type).all()
    
    category_counts = [{"category": row[0], "count": row[1]} for row in counts]
    
    return schemas.CustomerTransactionSummary(
        total_transactions=total_tx,
        total_revenue=total_rev,
        avg_transaction_value=avg_val,
        paid_transactions=paid_tx,
        category_counts=category_counts
    )


@router.get("/{transaction_id}", response_model=schemas.CustomerTransactionResponse)
def get_transaction(
    transaction_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    obj = db.query(models.CustomerTransaction).filter(
        models.CustomerTransaction.transaction_id == transaction_id,
        models.CustomerTransaction.deleted_at == None  # noqa: E711
    )
    obj = obj.join(models.Customer, models.CustomerTransaction.customer_id == models.Customer.customer_id)
    obj = apply_rbac_filter(db, obj, current_user, models.Customer, 'csm_rep_id').first()
    if not obj:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return obj


@router.post("", response_model=schemas.CustomerTransactionResponse, status_code=201)
def create_transaction(
    data: schemas.CustomerTransactionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    import uuid
    from datetime import datetime
    now = datetime.utcnow().isoformat()
    if getattr(data, 'customer_id', None):
        cust = apply_rbac_filter(db, db.query(models.Customer), current_user, models.Customer, 'csm_rep_id').filter(models.Customer.customer_id == data.customer_id).first()
        if not cust:
            raise HTTPException(status_code=403, detail='Not authorized for this customer')
    obj = models.CustomerTransaction(
        **data.dict(),
        transaction_id=f"TXN-{uuid.uuid4().hex[:6].upper()}",
        updated_at=now,
        created_by=current_user.user_id,
        updated_by=current_user.user_id,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/{transaction_id}", response_model=schemas.CustomerTransactionResponse)
def update_transaction(
    transaction_id: str,
    data: schemas.CustomerTransactionUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    from datetime import datetime
    obj = db.query(models.CustomerTransaction).filter(
        models.CustomerTransaction.transaction_id == transaction_id,
        models.CustomerTransaction.deleted_at == None
    )
    obj = obj.join(models.Customer, models.CustomerTransaction.customer_id == models.Customer.customer_id)
    obj = apply_rbac_filter(db, obj, current_user, models.Customer, 'csm_rep_id').first()
    if not obj:
        raise HTTPException(status_code=404, detail="Transaction not found")
        
    for k, v in data.dict(exclude_unset=True).items():
        setattr(obj, k, v)
        
    obj.updated_at = datetime.utcnow().isoformat()
    obj.updated_by = current_user.user_id
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{transaction_id}", status_code=200)
def delete_transaction(
    transaction_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(RoleChecker(["Admin", "System Admin"])),
):
    from datetime import datetime
    obj = db.query(models.CustomerTransaction).filter(
        models.CustomerTransaction.transaction_id == transaction_id,
        models.CustomerTransaction.deleted_at == None
    )
    obj = obj.join(models.Customer, models.CustomerTransaction.customer_id == models.Customer.customer_id)
    obj = apply_rbac_filter(db, obj, current_user, models.Customer, 'csm_rep_id').first()
    if not obj:
        raise HTTPException(status_code=404, detail="Transaction not found")
    obj.deleted_at = datetime.utcnow().isoformat()
    obj.updated_by = current_user.user_id
    db.commit()
    return {"message": "Transaction archived", "transaction_id": transaction_id}
