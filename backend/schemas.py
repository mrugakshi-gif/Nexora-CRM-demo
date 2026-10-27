"""
Pydantic v1-compatible schemas for the Indian B2B CRM API.

Conventions:
  - *Base: shared fields between create/update/response
  - *Create: fields accepted on POST (no auto-generated ID/timestamps)
  - *Update: fields accepted on PUT/PATCH (all Optional)
  - *Response: fields returned to clients (includes id + timestamps)
  - orm_mode = True on all *Response classes

Reference entities (read-only in API): Industry, Territory, Department,
  LeadSource, Product — only *Response schemas needed.
"""

from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, List
from datetime import datetime


# ===========================================================================
# AUTH
# ===========================================================================

class Token(BaseModel):
    access_token: str
    token_type: str


class UserResponse(BaseModel):
    user_id: str
    rep_id: Optional[str] = None
    email: str
    role: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


# ===========================================================================
# REFERENCE ENTITIES  (read-only)
# ===========================================================================

class IndustryResponse(BaseModel):
    industry_id: str
    industry_name: str
    industry_category: Optional[str] = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class TerritoryResponse(BaseModel):
    territory_id: str
    territory_name: str
    region: Optional[str] = None
    primary_industry_focus: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DepartmentResponse(BaseModel):
    department_id: str
    department_name: str
    region_focus: Optional[str] = None
    created_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class LeadSourceResponse(BaseModel):
    lead_source_id: str
    source_name: str
    source_category: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ProductBase(BaseModel):
    product_name: str
    product_category: Optional[str] = None
    pricing_model: Optional[str] = None
    list_price_inr: Optional[float] = None
    is_active: Optional[bool] = True


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    product_name: Optional[str] = None
    product_category: Optional[str] = None
    pricing_model: Optional[str] = None
    list_price_inr: Optional[float] = None
    is_active: Optional[bool] = None


class ProductResponse(ProductBase):
    product_id: str
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    updated_at: Optional[str] = None
    deleted_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ===========================================================================
# SALES REP
# ===========================================================================

class SalesRepResponse(BaseModel):
    rep_id: str
    full_name: str
    email: str
    phone: Optional[str] = None
    department_id: str
    manager_rep_id: Optional[str] = None
    role: str
    territory_id: str
    hire_date: str
    is_active: bool
    termination_date: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ===========================================================================
# COMPANY
# ===========================================================================

class CompanyBase(BaseModel):
    company_name: str
    industry_id: Optional[str] = None
    sub_industry: Optional[str] = None
    company_size_band: Optional[str] = None
    annual_revenue_band_inr: Optional[str] = None
    gstin: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    region: Optional[str] = None
    pincode: Optional[str] = None
    website_domain: Optional[str] = None
    company_type: Optional[str] = None
    founded_year: Optional[int] = None
    account_owner_rep_id: Optional[str] = None
    account_status: Optional[str] = None


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    company_name: Optional[str] = None
    industry_id: Optional[str] = None
    sub_industry: Optional[str] = None
    company_size_band: Optional[str] = None
    annual_revenue_band_inr: Optional[str] = None
    gstin: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    region: Optional[str] = None
    pincode: Optional[str] = None
    website_domain: Optional[str] = None
    company_type: Optional[str] = None
    founded_year: Optional[int] = None
    account_owner_rep_id: Optional[str] = None
    account_status: Optional[str] = None


class CompanyResponse(CompanyBase):
    company_id: str
    name_is_real_entity: Optional[bool] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    deleted_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ===========================================================================
# CONTACT
# ===========================================================================

class ContactBase(BaseModel):
    company_id: str
    full_name: str
    job_title: Optional[str] = None
    seniority_level: Optional[str] = None
    department: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    is_primary_contact: Optional[bool] = False
    linkedin_handle: Optional[str] = None
    is_decision_maker: Optional[bool] = False


class ContactCreate(ContactBase):
    pass


class ContactUpdate(BaseModel):
    company_id: Optional[str] = None
    full_name: Optional[str] = None
    job_title: Optional[str] = None
    seniority_level: Optional[str] = None
    department: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    is_primary_contact: Optional[bool] = None
    linkedin_handle: Optional[str] = None
    is_decision_maker: Optional[bool] = None


class ContactResponse(ContactBase):
    contact_id: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    deleted_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ===========================================================================
# CAMPAIGN
# ===========================================================================

from pydantic import BaseModel, ConfigDict, field_validator

class CampaignBase(BaseModel):
    campaign_name: str
    campaign_type: str
    start_date: str
    end_date: Optional[str] = None
    budget_inr: Optional[float] = None
    target_industry_id: Optional[str] = None
    owner_department_id: str

    @field_validator("campaign_type")
    @classmethod
    def validate_campaign_type(cls, v: str) -> str:
        allowed = [
            "Social Media", "Paid Search", "Email", "Partner Event", 
            "Webinar", "Content/SEO", "Trade Show"
        ]
        if v not in allowed:
            raise ValueError(f"Invalid campaign_type. Allowed: {allowed}")
        return v

class CampaignCreate(CampaignBase):
    pass

class CampaignUpdate(BaseModel):
    campaign_name: Optional[str] = None
    campaign_type: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    budget_inr: Optional[float] = None
    target_industry_id: Optional[str] = None
    owner_department_id: Optional[str] = None

    @field_validator("campaign_type")
    @classmethod
    def validate_campaign_type(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        allowed = [
            "Social Media", "Paid Search", "Email", "Partner Event", 
            "Webinar", "Content/SEO", "Trade Show"
        ]
        if v not in allowed:
            raise ValueError(f"Invalid campaign_type. Allowed: {allowed}")
        return v


class CampaignResponse(BaseModel):
    campaign_id: str
    campaign_name: str
    campaign_type: str
    start_date: str
    end_date: Optional[str] = None
    budget_inr: Optional[float] = None
    target_industry_id: Optional[str] = None
    owner_department_id: str

    model_config = ConfigDict(from_attributes=True)


class CampaignResponseItem(BaseModel):
    response_id: str
    campaign_id: str
    contact_id: str
    response_type: Optional[str] = None
    response_date: Optional[str] = None
    resulted_in_lead_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ===========================================================================
# LEAD
# ===========================================================================

class LeadBase(BaseModel):
    company_id: str
    contact_id: Optional[str] = None
    lead_source_id: Optional[str] = None
    campaign_id: Optional[str] = None
    assigned_rep_id: Optional[str] = None
    lead_status: str
    disqualification_reason: Optional[str] = None
    industry_interest_id: Optional[str] = None
    estimated_budget_inr: Optional[float] = None
    company_size_at_lead_time: Optional[str] = None


class LeadCreate(LeadBase):
    pass


class LeadUpdate(BaseModel):
    company_id: Optional[str] = None
    contact_id: Optional[str] = None
    lead_source_id: Optional[str] = None
    campaign_id: Optional[str] = None
    assigned_rep_id: Optional[str] = None
    lead_status: Optional[str] = None
    disqualification_reason: Optional[str] = None
    industry_interest_id: Optional[str] = None
    estimated_budget_inr: Optional[float] = None
    company_size_at_lead_time: Optional[str] = None
    first_contacted_at: Optional[str] = None
    qualified_at: Optional[str] = None
    converted_at: Optional[str] = None


class LeadResponse(LeadBase):
    lead_id: str
    first_contacted_at: Optional[str] = None
    qualified_at: Optional[str] = None
    converted_at: Optional[str] = None
    is_duplicate_of_lead_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    deleted_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class LeadStatusHistoryResponse(BaseModel):
    history_id: str
    lead_id: str
    status_from: Optional[str] = None
    status_to: str
    changed_at: str
    changed_by_rep_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ===========================================================================
# OPPORTUNITY
# ===========================================================================

class OpportunityBase(BaseModel):
    company_id: str
    primary_contact_id: Optional[str] = None
    source_lead_id: Optional[str] = None
    owner_rep_id: str
    opportunity_name: Optional[str] = None
    pipeline_stage: str
    forecast_category: Optional[str] = None
    deal_value_inr: float
    probability_pct: float
    expected_close_date: Optional[str] = None
    actual_close_date: Optional[str] = None
    close_outcome: Optional[str] = None
    loss_reason: Optional[str] = None
    competitor_name: Optional[str] = None
    opportunity_type: Optional[str] = None


class OpportunityCreate(OpportunityBase):
    pass


class OpportunityUpdate(BaseModel):
    company_id: Optional[str] = None
    primary_contact_id: Optional[str] = None
    owner_rep_id: Optional[str] = None
    opportunity_name: Optional[str] = None
    pipeline_stage: Optional[str] = None
    forecast_category: Optional[str] = None
    deal_value_inr: Optional[float] = None
    probability_pct: Optional[float] = None
    expected_close_date: Optional[str] = None
    actual_close_date: Optional[str] = None
    close_outcome: Optional[str] = None
    loss_reason: Optional[str] = None
    competitor_name: Optional[str] = None
    opportunity_type: Optional[str] = None


class OpportunityResponse(OpportunityBase):
    opportunity_id: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    deleted_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class OpportunityStageHistoryResponse(BaseModel):
    history_id: str
    opportunity_id: str
    stage_from: Optional[str] = None
    stage_to: str
    changed_at: str
    days_in_previous_stage: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class OpportunityProductResponse(BaseModel):
    opportunity_product_id: str
    opportunity_id: str
    product_id: str
    quantity: int
    unit_price_inr: float
    discount_pct: Optional[float] = None
    line_total_inr: float

    model_config = ConfigDict(from_attributes=True)


# ===========================================================================
# CUSTOMER
# ===========================================================================

class CustomerBase(BaseModel):
    company_id: str
    originating_opportunity_id: str
    customer_since: str
    csm_rep_id: str
    customer_tier: Optional[str] = None
    contract_type: Optional[str] = None
    renewal_date: Optional[str] = None
    customer_status: str


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    csm_rep_id: Optional[str] = None
    customer_tier: Optional[str] = None
    contract_type: Optional[str] = None
    renewal_date: Optional[str] = None
    customer_status: Optional[str] = None


class CustomerResponse(CustomerBase):
    customer_id: str
    updated_at: Optional[str] = None
    deleted_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ===========================================================================
# CUSTOMER TRANSACTION
# ===========================================================================

class CustomerTransactionBase(BaseModel):
    customer_id: str
    opportunity_id: Optional[str] = None
    transaction_date: str
    transaction_type: str
    amount_inr: float
    payment_status: Optional[str] = None
    invoice_number: Optional[str] = None

class CustomerTransactionCreate(CustomerTransactionBase):
    pass

class CustomerTransactionUpdate(BaseModel):
    customer_id: Optional[str] = None
    opportunity_id: Optional[str] = None
    transaction_date: Optional[str] = None
    transaction_type: Optional[str] = None
    amount_inr: Optional[float] = None
    payment_status: Optional[str] = None
    invoice_number: Optional[str] = None

class CustomerTransactionResponse(CustomerTransactionBase):
    transaction_id: str
    updated_at: Optional[str] = None
    deleted_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)



# ===========================================================================
# SUPPORT CASE
# ===========================================================================

class SupportCaseBase(BaseModel):
    customer_id: str
    contact_id: Optional[str] = None
    case_type: Optional[str] = None
    priority: Optional[str] = None
    status: str
    opened_at: str
    resolved_at: Optional[str] = None
    satisfaction_score: Optional[float] = None


class SupportCaseCreate(SupportCaseBase):
    pass


class SupportCaseUpdate(BaseModel):
    contact_id: Optional[str] = None
    case_type: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    resolved_at: Optional[str] = None
    satisfaction_score: Optional[float] = None


class SupportCaseResponse(SupportCaseBase):
    case_id: str
    updated_at: Optional[str] = None
    deleted_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ===========================================================================
# ACTIVITY
# ===========================================================================

class ActivityBase(BaseModel):
    activity_type: str
    subject: str
    description: Optional[str] = None
    activity_date: Optional[str] = None
    due_date: Optional[str] = None
    status: str
    priority: str
    lead_id: Optional[str] = None
    contact_id: Optional[str] = None
    company_id: Optional[str] = None
    opportunity_id: Optional[str] = None
    customer_id: Optional[str] = None
    sales_rep_id: Optional[str] = None
    outcome: Optional[str] = None
    next_follow_up_date: Optional[str] = None


class ActivityCreate(ActivityBase):
    pass


class ActivityUpdate(BaseModel):
    activity_type: Optional[str] = None
    subject: Optional[str] = None
    description: Optional[str] = None
    activity_date: Optional[str] = None
    due_date: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    lead_id: Optional[str] = None
    contact_id: Optional[str] = None
    company_id: Optional[str] = None
    opportunity_id: Optional[str] = None
    customer_id: Optional[str] = None
    sales_rep_id: Optional[str] = None
    outcome: Optional[str] = None
    next_follow_up_date: Optional[str] = None


class ActivityResponse(ActivityBase):
    activity_id: str
    completed_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_at: Optional[str] = None
    
    # Resolved relationships for UI
    resolved_company_name: Optional[str] = None
    resolved_contact_name: Optional[str] = None
    resolved_opportunity_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ===========================================================================
# CHAT / AI
# ===========================================================================

class ChatMessageBase(BaseModel):
    role: str
    content: str


class ChatMessageCreate(ChatMessageBase):
    session_id: Optional[str] = None


class ChatMessageResponse(ChatMessageBase):
    message_id: str
    session_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatSessionBase(BaseModel):
    pass


class ChatSessionCreate(ChatSessionBase):
    pass


class ChatSessionResponse(ChatSessionBase):
    session_id: str
    user_id: str
    created_at: datetime
    messages: List[ChatMessageResponse] = []

    model_config = ConfigDict(from_attributes=True)


# ===========================================================================
# DOCUMENTS
# ===========================================================================

class CompanyDocumentBase(BaseModel):
    filename: str
    company_id: Optional[str] = None
    title: Optional[str] = None
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    processing_status: Optional[str] = None
    chunk_count: Optional[int] = None
    index_status: Optional[str] = None


class CompanyDocumentCreate(CompanyDocumentBase):
    pass


class CompanyDocumentResponse(CompanyDocumentBase):
    doc_id: str
    uploaded_by: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentChunkResponse(BaseModel):
    chunk_id: str
    document_id: str
    chunk_index: int
    text: str
    page_number: Optional[int] = None
    character_count: int
    token_count: Optional[int] = None
    indexing_status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ===========================================================================
# PAGINATION WRAPPER (used by list endpoints)
# ===========================================================================

class PaginatedResponse(BaseModel):
    total: int
    skip: int
    limit: int
    data: list
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum

class HealthStatus(str, Enum):
    CRITICAL = "Critical"
    AT_RISK = "At Risk"
    HEALTHY = "Healthy"
    EXCELLENT = "Excellent"
    UNKNOWN = "Unknown"

class InsightInput(BaseModel):
    insight: str
    type: str  # 'positive', 'negative', 'neutral'

class AccountHealthResponse(BaseModel):
    customer_id: str
    entity_name: Optional[str] = None
    score: float = Field(..., description="0-100 health score")
    status: HealthStatus
    metrics: Dict[str, Any]
    insights: List[InsightInput]
    insufficient_data: bool = False

class CompanyHealthResponse(BaseModel):
    company_id: str
    entity_name: Optional[str] = None
    score: float = Field(..., description="0-100 health score")
    status: HealthStatus
    metrics: Dict[str, Any]
    insights: List[InsightInput]
    insufficient_data: bool = False

class ProductHealthResponse(BaseModel):
    product_id: str
    entity_name: Optional[str] = None
    score: float = Field(..., description="0-100 health score")
    status: HealthStatus
    metrics: Dict[str, Any]
    insights: List[InsightInput]
    insufficient_data: bool = False

class DealHealthFactor(BaseModel):
    category: str = Field(..., description="Category: Timeline, Velocity, Margin, Engagement, Completeness")
    name: str = Field(..., description="Short factor title")
    impact: str = Field(..., description="'positive', 'negative', 'neutral'")
    weight_score_impact: float = Field(..., description="Points added or deducted from health score")
    detail: str = Field(..., description="Detailed explanation of the indicator")

class DealHealthResponse(BaseModel):
    opportunity_id: str
    opportunity_name: str
    pipeline_stage: str
    is_closed: bool
    close_outcome: Optional[str] = None
    health_score: float = Field(..., description="0-100 overall health score (higher is healthier)")
    risk_score: float = Field(..., description="0-100 risk score (100 - health_score, higher is riskier)")
    risk_level: str = Field(..., description="'Low', 'Medium', 'High', 'Critical'")
    status: HealthStatus
    scoring_method: str = "rule_based_heuristic"
    is_ml_model: bool = False
    contributing_factors: List[DealHealthFactor] = []
    mitigation_recommendations: List[str] = []
    supporting_metrics: Dict[str, Any] = {}
    insufficient_data: bool = False

class RiskEntity(BaseModel):
    id: str
    name: str
    score: float
    status: HealthStatus
    key_signal: str

class HealthSummaryResponse(BaseModel):
    average_score: Optional[float] = Field(None, description="Average 0-100 health score. Null if no sufficient data.")
    status: HealthStatus
    total_evaluated: int
    healthy_count: int
    at_risk_count: int
    critical_count: int
    unknown_count: int
    health_distribution: Dict[str, int]
    insights: List[InsightInput]
    risk_entities: List[RiskEntity] = []
    insufficient_data: bool = False

class NextBestActionResponse(BaseModel):
    customer_id: str
    entity_name: str
    action: str
    priority: str
    reasons: List[str]
    supporting_metrics: dict

class CategoryCount(BaseModel):
    category: str
    count: int

class CustomerTransactionSummary(BaseModel):
    total_transactions: int
    total_revenue: float
    avg_transaction_value: float
    paid_transactions: int
    category_counts: List[CategoryCount]

class ActivitySummary(BaseModel):
    total_activities: int
    completed_activities: int
    pending_activities: int
    overdue_activities: int
    category_counts: List[CategoryCount]
    years: List[str] = []

class CampaignSummaryResponse(BaseModel):
    total_campaigns: int
    total_budget: float
    total_engagements: int
    demo_requests: int
    category_counts: List[CategoryCount]

class SupportSummaryResponse(BaseModel):
    total_cases: int
    open_cases: int
    resolved_cases: int
    high_priority_cases: int
    avg_resolution_hours: float
    avg_satisfaction: float
    category_counts: List[Dict[str, Any]]


# ===========================================================================
# SETTINGS & AUTOMATION LOGS
# ===========================================================================

class UserSettingsBase(BaseModel):
    email_notifications: bool

class UserSettingsUpdate(UserSettingsBase):
    pass

class UserSettingsResponse(UserSettingsBase):
    setting_id: str
    user_id: str
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EmailHistoryResponse(BaseModel):
    id: str
    recipient_email: str
    subject: str
    email_type: str
    status: str
    sent_at: datetime
    error_message: Optional[str] = None
    user_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TestEmailRequest(BaseModel):
    recipient_email: str

class EmailGenerationRequest(BaseModel):
    alert_type: str
    context: Dict[str, Any]
    recipient_name: Optional[str] = None

class EmailGenerationResponse(BaseModel):
    subject: str
    text_body: str
    html_body: str
    email_type: str

class SendDraftRequest(BaseModel):
    recipient_email: str
    subject: str
    text_body: str
    html_body: Optional[str] = None
    email_type: str = "General"
