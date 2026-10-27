from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class LeadConversionResponse(BaseModel):
    lead_id: str
    conversion_probability: float = Field(..., description="0-1 probability of conversion")
    prediction: int = Field(..., description="0 or 1 binary prediction")
    model_identifier: str = Field(..., description="Model artifact name used")

class KeyFactorItem(BaseModel):
    feature: str = Field(..., description="Feature code name")
    impact: str = Field(..., description="'positive' (increases score) or 'negative' (decreases score)")
    contribution: float = Field(..., description="Local log-odds contribution (beta * x)")
    description: str = Field(..., description="Human-readable explanation of the effect")

class LeadScoringResponse(BaseModel):
    lead_id: str
    score_probability: float = Field(..., description="0-1 probability of conversion representing the score")
    lead_score: Optional[float] = Field(None, description="0-1 score representing conversion probability (alias for score_probability)")
    key_factors: list[KeyFactorItem] = Field(default_factory=list, description="Top positive and negative local factors driving the score based on instance logit decomposition")
    model_identifier: str = Field(..., description="Model artifact name used")

class CustomerSegmentationResponse(BaseModel):
    customer_id: str
    cluster_id: int
    cluster_info: str = Field(..., description="General description of the cluster mapping (if available)")
    model_identifier: str

class CustomerChurnResponse(BaseModel):
    customer_id: str
    churn_probability: float = Field(..., description="0-1 probability of churn")
    prediction: int = Field(..., description="0 or 1 binary prediction")
    model_identifier: str
    warnings: Optional[str] = Field(None, description="Warnings related to model performance limitations")

class SalesForecastResponse(BaseModel):
    period_description: str
    forecast_amount_inr: float
    model_identifier: str
    baseline_note: Optional[str] = None
    methodology: Optional[str] = Field("Trailing 3-Month Moving Average Baseline", description="Forecasting method used")
    is_ml_model: bool = Field(False, description="Flag indicating if the forecast is from a trained ML model")
    confidence_level: Optional[str] = Field("Low (Statistical Baseline)", description="Confidence rating")
    historical_months_evaluated: Optional[int] = Field(3, description="Number of historical months evaluated")
    trailing_revenue_inr: Optional[float] = Field(None, description="Total revenue realized in the trailing evaluation window")
    data_quality_warning: Optional[str] = Field(None, description="Data quality or sparsity notice if applicable")

class LeadAggregateItem(BaseModel):
    lead_id: str
    company_name: str
    score_probability: float
    conversion_probability: float

class LeadIntelligenceAggregateResponse(BaseModel):
    top_leads: list[LeadAggregateItem]
    model_identifier: str

class CustomerRiskAggregateItem(BaseModel):
    customer_id: str
    company_name: str
    churn_probability: float

class CustomerRiskAggregateResponse(BaseModel):
    top_at_risk_customers: list[CustomerRiskAggregateItem]
    model_identifier: str

class CustomerSegmentDistributionResponse(BaseModel):
    distribution: dict[int, int]
    model_identifier: str
