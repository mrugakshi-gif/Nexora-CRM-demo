from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import User
from ..deps import get_current_user
from ..intelligence_schemas import IntelligenceResponse
from ..services.intelligence_service import get_retention_recommendations

router = APIRouter(prefix="/api/intelligence", tags=["intelligence"])

@router.get("/next-best-actions/retention", response_model=IntelligenceResponse)
def next_best_action_retention(
    period: str = Query("this_year", description="Time period filter"),
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    try:
        return get_retention_recommendations(db, current_user, period=period)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
