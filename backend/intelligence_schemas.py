from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class ActionItem(BaseModel):
    customer_id: str
    entity_name: str
    
    # next best action fields
    action: Optional[str] = None
    priority: Optional[str] = None
    reasons: Optional[List[str]] = None
    supporting_metrics: Optional[Dict[str, Any]] = None
    
    # actions_taken fields
    activity_id: Optional[str] = None
    activity_type: Optional[str] = None
    activity_date: Optional[str] = None
    subject: Optional[str] = None
    description: Optional[str] = None

class IntelligenceResponse(BaseModel):
    mode: str
    actions: List[ActionItem]
