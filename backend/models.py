"""
SQLAlchemy ORM models for the Indian B2B CRM.

Schema source: data/source/*.csv (20 tables)
FK verification: data/full_audit_report.json  – section 6_7_invalid_fk_and_orphans (all 37 FK checks = 0 violations)
Soft-delete convention: deleted_at (nullable String/DateTime) on every mutable CRM table.
PK convention: source dataset PKs are preserved exactly (e.g. COMP-000001, LEAD-000001).

Table classification:
  REFERENCE (read-only in API): Industry, Territory, Department, LeadSource, Product
  CORE CRM   (full CRUD + soft-delete): Company, Contact, Lead, Opportunity, Customer,
             Activity, CustomerTransaction, SupportCase, Campaign, SalesRep, User
  HISTORY    (append-only, read via parent): LeadStatusHistory, OpportunityStageHistory,
             OpportunityProduct, CampaignResponse
  AI/RAG     (internal): ChatSession, ChatMessage, CompanyDocument
"""

from sqlalchemy import (
    Boolean, Column, ForeignKey, Integer, String, Float,
    DateTime, Text, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


# ---------------------------------------------------------------------------
# REFERENCE TABLES (no soft-delete; stable lookup data)
# ---------------------------------------------------------------------------

class Industry(Base):
    __tablename__ = "industries"

    industry_id    = Column(String, primary_key=True, index=True)
    industry_name  = Column(String, nullable=False)
    industry_category = Column(String)
    is_active      = Column(Boolean, default=True)

    # back-references
    companies  = relationship("Company",  back_populates="industry")
    campaigns  = relationship("Campaign", back_populates="target_industry", foreign_keys="Campaign.target_industry_id")
    leads      = relationship("Lead",     back_populates="industry_interest", foreign_keys="Lead.industry_interest_id")


class Territory(Base):
    __tablename__ = "territories"

    territory_id           = Column(String, primary_key=True, index=True)
    territory_name         = Column(String, nullable=False)
    region                 = Column(String)
    primary_industry_focus = Column(String)

    sales_reps = relationship("SalesRep", back_populates="territory")


class Department(Base):
    __tablename__ = "departments"

    department_id   = Column(String, primary_key=True, index=True)
    department_name = Column(String, nullable=False)
    region_focus    = Column(String)
    created_at      = Column(String)

    sales_reps = relationship("SalesRep",  back_populates="department")
    campaigns  = relationship("Campaign",  back_populates="owner_department", foreign_keys="Campaign.owner_department_id")


class LeadSource(Base):
    __tablename__ = "lead_sources"

    lead_source_id  = Column(String, primary_key=True, index=True)
    source_name     = Column(String, nullable=False)
    source_category = Column(String)

    leads = relationship("Lead", back_populates="lead_source")


class Product(Base):
    __tablename__ = "products"

    product_id       = Column(String, primary_key=True, index=True)
    product_name     = Column(String, nullable=False, unique=True)
    product_category = Column(String)
    pricing_model    = Column(String)
    list_price_inr   = Column(Float)
    is_active        = Column(Boolean, default=True)
    created_by       = Column(String)
    updated_by       = Column(String)
    updated_at       = Column(String)
    deleted_at       = Column(String, nullable=True)

    opportunity_products = relationship("OpportunityProduct", back_populates="product")


# ---------------------------------------------------------------------------
# SALES REP  (org-chart entity; also used for auth via User)
# ---------------------------------------------------------------------------

class SalesRep(Base):
    __tablename__ = "sales_reps"

    rep_id           = Column(String, primary_key=True, index=True)
    full_name        = Column(String, nullable=False)
    email            = Column(String, nullable=False, unique=True)
    phone            = Column(String)
    department_id    = Column(String, ForeignKey("departments.department_id"), nullable=False)
    manager_rep_id   = Column(String, ForeignKey("sales_reps.rep_id"),        nullable=True)
    role             = Column(String, nullable=False)
    territory_id     = Column(String, ForeignKey("territories.territory_id"),  nullable=False)
    hire_date        = Column(String, nullable=False)
    is_active        = Column(Boolean, default=True)
    termination_date = Column(String, nullable=True)

    department  = relationship("Department",  back_populates="sales_reps")
    territory   = relationship("Territory",   back_populates="sales_reps")
    manager     = relationship("SalesRep",    remote_side="SalesRep.rep_id", foreign_keys=[manager_rep_id])
    user        = relationship("User",        back_populates="sales_rep", uselist=False)

    owned_companies   = relationship("Company",     back_populates="account_owner", foreign_keys="Company.account_owner_rep_id")
    assigned_leads    = relationship("Lead",        back_populates="assigned_rep",  foreign_keys="Lead.assigned_rep_id")
    owned_opps        = relationship("Opportunity", back_populates="owner_rep",     foreign_keys="Opportunity.owner_rep_id")
    managed_customers = relationship("Customer",    back_populates="csm_rep",       foreign_keys="Customer.csm_rep_id")
    activities        = relationship("Activity",    back_populates="sales_rep",     foreign_keys="Activity.sales_rep_id")


# ---------------------------------------------------------------------------
# USER  (authentication; 1:1 with SalesRep where rep exists)
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    user_id       = Column(String, primary_key=True, index=True)
    firebase_uid  = Column(String, unique=True, nullable=True, index=True)
    rep_id        = Column(String, ForeignKey("sales_reps.rep_id"), nullable=True, unique=True)
    email         = Column(String, nullable=False, unique=True, index=True)
    password_hash = Column(String)
    role          = Column(String, nullable=False)
    is_active     = Column(Boolean, default=True)
    created_at    = Column(String)

    updated_at    = Column(String)
    deleted_at    = Column(String, nullable=True)

    sales_rep     = relationship("SalesRep",        back_populates="user")
    chat_sessions = relationship("ChatSession",     back_populates="user")
    documents     = relationship("CompanyDocument", back_populates="uploaded_by_user", foreign_keys="CompanyDocument.uploaded_by")


# ---------------------------------------------------------------------------
# COMPANY  (core CRM account entity)
# ---------------------------------------------------------------------------

class Company(Base):
    __tablename__ = "companies"

    company_id             = Column(String, primary_key=True, index=True)
    company_name           = Column(String, nullable=False, index=True)
    name_is_real_entity    = Column(Boolean, default=True)
    industry_id            = Column(String, ForeignKey("industries.industry_id"), nullable=False)
    sub_industry           = Column(String, nullable=True)
    company_size_band      = Column(String)
    annual_revenue_band_inr= Column(String)
    gstin                  = Column(String, nullable=True)
    city                   = Column(String, nullable=False)
    state                  = Column(String, nullable=False)
    region                 = Column(String)
    pincode                = Column(String)
    website_domain         = Column(String, nullable=True)
    company_type           = Column(String)
    founded_year           = Column(Integer, nullable=True)
    account_owner_rep_id   = Column(String, ForeignKey("sales_reps.rep_id"), nullable=True)
    account_status         = Column(String, nullable=False)
    created_at             = Column(String)
    created_by             = Column(String)
    updated_by             = Column(String)
    updated_at             = Column(String)
    deleted_at             = Column(String, nullable=True)

    industry        = relationship("Industry",  back_populates="companies")
    account_owner   = relationship("SalesRep",  back_populates="owned_companies", foreign_keys=[account_owner_rep_id])

    contacts        = relationship("Contact",     back_populates="company")
    leads           = relationship("Lead",        back_populates="company")
    opportunities   = relationship("Opportunity", back_populates="company")
    customer        = relationship("Customer",    back_populates="company",  uselist=False)
    activities      = relationship("Activity",    back_populates="company",  foreign_keys="Activity.company_id")
    documents       = relationship("CompanyDocument", back_populates="company")

    __table_args__ = (
        Index("ix_companies_state", "state"),
        Index("ix_companies_industry", "industry_id"),
    )


# ---------------------------------------------------------------------------
# CONTACT  (person at a company)
# ---------------------------------------------------------------------------

class Contact(Base):
    __tablename__ = "contacts"

    contact_id         = Column(String, primary_key=True, index=True)
    company_id         = Column(String, ForeignKey("companies.company_id"), nullable=False)
    full_name          = Column(String, nullable=False)
    job_title          = Column(String, nullable=False)
    seniority_level    = Column(String)
    department         = Column(String)
    email              = Column(String, nullable=False, unique=True)
    phone              = Column(String)
    is_primary_contact = Column(Boolean, default=False)
    linkedin_handle    = Column(String, nullable=True)
    is_decision_maker  = Column(Boolean, default=False)
    created_at         = Column(String)
    created_by         = Column(String)
    updated_by         = Column(String)
    updated_at         = Column(String)
    deleted_at         = Column(String, nullable=True)

    company              = relationship("Company",            back_populates="contacts")
    leads                = relationship("Lead",               back_populates="contact",          foreign_keys="Lead.contact_id")
    opportunities        = relationship("Opportunity",        back_populates="primary_contact",   foreign_keys="Opportunity.primary_contact_id")
    campaign_responses   = relationship("CampaignResponse",  back_populates="contact")
    support_cases        = relationship("SupportCase",        back_populates="contact",           foreign_keys="SupportCase.contact_id")
    activities           = relationship("Activity",           back_populates="contact",           foreign_keys="Activity.contact_id")


# ---------------------------------------------------------------------------
# CAMPAIGN  (marketing campaign)
# ---------------------------------------------------------------------------

class Campaign(Base):
    __tablename__ = "campaigns"

    campaign_id         = Column(String, primary_key=True, index=True)
    campaign_name       = Column(String, nullable=False)
    campaign_type       = Column(String, nullable=False)
    start_date          = Column(String, nullable=False)
    end_date            = Column(String, nullable=True)
    budget_inr          = Column(Float)
    target_industry_id  = Column(String, ForeignKey("industries.industry_id"), nullable=True)
    owner_department_id = Column(String, ForeignKey("departments.department_id"), nullable=False)
    created_by          = Column(String)
    updated_by          = Column(String)
    updated_at          = Column(String)
    deleted_at          = Column(String, nullable=True)

    target_industry  = relationship("Industry",          back_populates="campaigns",  foreign_keys=[target_industry_id])
    owner_department = relationship("Department",        back_populates="campaigns",  foreign_keys=[owner_department_id])
    responses        = relationship("CampaignResponse", back_populates="campaign")
    leads            = relationship("Lead",              back_populates="campaign",   foreign_keys="Lead.campaign_id")


# ---------------------------------------------------------------------------
# LEAD  (inbound / outbound prospect)
# ---------------------------------------------------------------------------

class Lead(Base):
    __tablename__ = "leads"

    lead_id                  = Column(String, primary_key=True, index=True)
    company_id               = Column(String, ForeignKey("companies.company_id"),     nullable=False)
    contact_id               = Column(String, ForeignKey("contacts.contact_id"),      nullable=True)
    lead_source_id           = Column(String, ForeignKey("lead_sources.lead_source_id"), nullable=False)
    campaign_id              = Column(String, ForeignKey("campaigns.campaign_id"),    nullable=True)
    assigned_rep_id          = Column(String, ForeignKey("sales_reps.rep_id"),        nullable=True)
    lead_status              = Column(String, nullable=False, index=True)
    disqualification_reason  = Column(String, nullable=True)
    industry_interest_id     = Column(String, ForeignKey("industries.industry_id"),   nullable=True)
    estimated_budget_inr     = Column(Float)
    company_size_at_lead_time= Column(String)
    created_at               = Column(String, nullable=False)
    first_contacted_at       = Column(String, nullable=True)
    qualified_at             = Column(String, nullable=True)
    converted_at             = Column(String, nullable=True)
    is_duplicate_of_lead_id  = Column(String, ForeignKey("leads.lead_id"),            nullable=True)
    created_by               = Column(String)
    updated_by               = Column(String)
    updated_at               = Column(String)
    deleted_at               = Column(String, nullable=True)

    company           = relationship("Company",         back_populates="leads")
    contact           = relationship("Contact",         back_populates="leads",           foreign_keys=[contact_id])
    lead_source       = relationship("LeadSource",      back_populates="leads")
    campaign          = relationship("Campaign",        back_populates="leads",           foreign_keys=[campaign_id])
    assigned_rep      = relationship("SalesRep",        back_populates="assigned_leads",  foreign_keys=[assigned_rep_id])
    industry_interest = relationship("Industry",        back_populates="leads",           foreign_keys=[industry_interest_id])
    duplicate_of      = relationship("Lead",            remote_side="Lead.lead_id",       foreign_keys=[is_duplicate_of_lead_id])

    status_history    = relationship("LeadStatusHistory", back_populates="lead")
    opportunity       = relationship("Opportunity",       back_populates="source_lead",   foreign_keys="Opportunity.source_lead_id", uselist=False)
    activities        = relationship("Activity",          back_populates="lead",          foreign_keys="Activity.lead_id")

    __table_args__ = (
        Index("ix_leads_assigned_rep_status", "assigned_rep_id", "lead_status"),
    )


# ---------------------------------------------------------------------------
# LEAD STATUS HISTORY  (append-only audit trail)
# ---------------------------------------------------------------------------

class LeadStatusHistory(Base):
    __tablename__ = "lead_status_history"

    history_id      = Column(String, primary_key=True, index=True)
    lead_id         = Column(String, ForeignKey("leads.lead_id"), nullable=False)
    status_from     = Column(String)
    status_to       = Column(String, nullable=False)
    changed_at      = Column(String, nullable=False)
    changed_by_rep_id = Column(String, ForeignKey("sales_reps.rep_id"), nullable=True)

    lead        = relationship("Lead",    back_populates="status_history")
    changed_by  = relationship("SalesRep", foreign_keys=[changed_by_rep_id])

    __table_args__ = (
        Index("ix_lead_status_history_lead_changed", "lead_id", "changed_at"),
    )


# ---------------------------------------------------------------------------
# CAMPAIGN RESPONSE
# ---------------------------------------------------------------------------

class CampaignResponse(Base):
    __tablename__ = "campaign_responses"

    response_id         = Column(String, primary_key=True, index=True)
    campaign_id         = Column(String, ForeignKey("campaigns.campaign_id"), nullable=False)
    contact_id          = Column(String, ForeignKey("contacts.contact_id"),   nullable=False)
    response_type       = Column(String)
    response_date       = Column(String)
    resulted_in_lead_id = Column(String, ForeignKey("leads.lead_id"),         nullable=True)

    campaign        = relationship("Campaign", back_populates="responses")
    contact         = relationship("Contact",  back_populates="campaign_responses")
    resulted_in_lead= relationship("Lead",     foreign_keys=[resulted_in_lead_id])


# ---------------------------------------------------------------------------
# OPPORTUNITY  (active deal in the sales pipeline)
# ---------------------------------------------------------------------------

class Opportunity(Base):
    __tablename__ = "opportunities"

    opportunity_id      = Column(String, primary_key=True, index=True)
    company_id          = Column(String, ForeignKey("companies.company_id"),  nullable=False)
    primary_contact_id  = Column(String, ForeignKey("contacts.contact_id"),   nullable=True)
    source_lead_id      = Column(String, ForeignKey("leads.lead_id"),         nullable=True)
    owner_rep_id        = Column(String, ForeignKey("sales_reps.rep_id"),     nullable=False)
    opportunity_name    = Column(String)
    pipeline_stage      = Column(String, nullable=False, index=True)
    forecast_category   = Column(String)
    deal_value_inr      = Column(Float, nullable=False)
    probability_pct     = Column(Float, nullable=False)
    expected_close_date = Column(String)
    actual_close_date   = Column(String, nullable=True)
    close_outcome       = Column(String, nullable=True)
    loss_reason         = Column(String, nullable=True)
    competitor_name     = Column(String, nullable=True)
    opportunity_type    = Column(String)
    created_at          = Column(String, nullable=False)
    created_by          = Column(String)
    updated_by          = Column(String)
    updated_at          = Column(String)
    deleted_at          = Column(String, nullable=True)

    company          = relationship("Company",    back_populates="opportunities")
    primary_contact  = relationship("Contact",   back_populates="opportunities",   foreign_keys=[primary_contact_id])
    source_lead      = relationship("Lead",      back_populates="opportunity",      foreign_keys=[source_lead_id])
    owner_rep        = relationship("SalesRep",  back_populates="owned_opps",       foreign_keys=[owner_rep_id])
    customer         = relationship("Customer",  back_populates="originating_opp",  foreign_keys="Customer.originating_opportunity_id", uselist=False)

    stage_history    = relationship("OpportunityStageHistory", back_populates="opportunity")
    products         = relationship("OpportunityProduct",      back_populates="opportunity")
    transactions     = relationship("CustomerTransaction",     back_populates="opportunity", foreign_keys="CustomerTransaction.opportunity_id")
    activities       = relationship("Activity",                back_populates="opportunity", foreign_keys="Activity.opportunity_id")

    __table_args__ = (
        Index("ix_opp_rep_stage", "owner_rep_id", "pipeline_stage"),
        Index("ix_opp_close_date", "expected_close_date"),
    )


# ---------------------------------------------------------------------------
# OPPORTUNITY STAGE HISTORY  (append-only)
# ---------------------------------------------------------------------------

class OpportunityStageHistory(Base):
    __tablename__ = "opportunity_stage_history"

    history_id            = Column(String, primary_key=True, index=True)
    opportunity_id        = Column(String, ForeignKey("opportunities.opportunity_id"), nullable=False)
    stage_from            = Column(String)
    stage_to              = Column(String, nullable=False)
    changed_at            = Column(String, nullable=False)
    days_in_previous_stage= Column(Float)

    opportunity = relationship("Opportunity", back_populates="stage_history")

    __table_args__ = (
        Index("ix_opp_stage_history_opp_changed", "opportunity_id", "changed_at"),
    )


# ---------------------------------------------------------------------------
# OPPORTUNITY PRODUCT  (line items)
# ---------------------------------------------------------------------------

class OpportunityProduct(Base):
    __tablename__ = "opportunity_products"

    opportunity_product_id = Column(String, primary_key=True, index=True)
    opportunity_id         = Column(String, ForeignKey("opportunities.opportunity_id"), nullable=False)
    product_id             = Column(String, ForeignKey("products.product_id"),          nullable=False)
    quantity               = Column(Integer, nullable=False)
    unit_price_inr         = Column(Float, nullable=False)
    discount_pct           = Column(Float, default=0.0)
    line_total_inr         = Column(Float, nullable=False)

    opportunity = relationship("Opportunity", back_populates="products")
    product     = relationship("Product",     back_populates="opportunity_products")


# ---------------------------------------------------------------------------
# CUSTOMER  (converted / paying account)
# ---------------------------------------------------------------------------

class Customer(Base):
    __tablename__ = "customers"

    customer_id                = Column(String, primary_key=True, index=True)
    company_id                 = Column(String, ForeignKey("companies.company_id"),      nullable=False, unique=True)
    originating_opportunity_id = Column(String, ForeignKey("opportunities.opportunity_id"), nullable=False, unique=True)
    customer_since             = Column(String, nullable=False)
    csm_rep_id                 = Column(String, ForeignKey("sales_reps.rep_id"),         nullable=False)
    customer_tier              = Column(String)
    contract_type              = Column(String)
    renewal_date               = Column(String, nullable=True)
    customer_status            = Column(String, nullable=False, index=True)
    created_by                 = Column(String)
    updated_by                 = Column(String)
    updated_at                 = Column(String)
    deleted_at                 = Column(String, nullable=True)

    company          = relationship("Company",     back_populates="customer")
    originating_opp  = relationship("Opportunity", back_populates="customer",         foreign_keys=[originating_opportunity_id])
    csm_rep          = relationship("SalesRep",    back_populates="managed_customers", foreign_keys=[csm_rep_id])

    transactions  = relationship("CustomerTransaction", back_populates="customer")
    support_cases = relationship("SupportCase",         back_populates="customer",   foreign_keys="SupportCase.customer_id")
    activities    = relationship("Activity",             back_populates="customer",  foreign_keys="Activity.customer_id")


# ---------------------------------------------------------------------------
# CUSTOMER TRANSACTION
# ---------------------------------------------------------------------------

class CustomerTransaction(Base):
    __tablename__ = "customer_transactions"

    transaction_id   = Column(String, primary_key=True, index=True)
    customer_id      = Column(String, ForeignKey("customers.customer_id"),      nullable=False)
    opportunity_id   = Column(String, ForeignKey("opportunities.opportunity_id"), nullable=True)
    transaction_date = Column(String, nullable=False)
    transaction_type = Column(String, nullable=False)
    amount_inr       = Column(Float, nullable=False)
    payment_status   = Column(String)
    invoice_number   = Column(String)
    created_by       = Column(String)
    updated_by       = Column(String)
    updated_at       = Column(String)
    deleted_at       = Column(String, nullable=True)

    customer    = relationship("Customer",    back_populates="transactions")
    opportunity = relationship("Opportunity", back_populates="transactions", foreign_keys=[opportunity_id])

    __table_args__ = (
        Index("ix_txn_customer_date", "customer_id", "transaction_date"),
    )


# ---------------------------------------------------------------------------
# SUPPORT CASE
# ---------------------------------------------------------------------------

class SupportCase(Base):
    __tablename__ = "customer_support_cases"

    case_id            = Column(String, primary_key=True, index=True)
    customer_id        = Column(String, ForeignKey("customers.customer_id"), nullable=False)
    contact_id         = Column(String, ForeignKey("contacts.contact_id"),   nullable=True)
    case_type          = Column(String)
    priority           = Column(String)
    status             = Column(String, nullable=False, index=True)
    opened_at          = Column(String, nullable=False)
    resolved_at        = Column(String, nullable=True)
    satisfaction_score = Column(Float, nullable=True)
    created_by         = Column(String)
    updated_by         = Column(String)
    updated_at         = Column(String)
    deleted_at         = Column(String, nullable=True)

    customer = relationship("Customer", back_populates="support_cases",  foreign_keys=[customer_id])
    contact  = relationship("Contact",  back_populates="support_cases",  foreign_keys=[contact_id])


# ---------------------------------------------------------------------------
# ACTIVITY  (all CRM touchpoints — calls, emails, meetings, tasks, etc.)
# ---------------------------------------------------------------------------

class Activity(Base):
    __tablename__ = "activities"

    activity_id        = Column(String, primary_key=True, index=True)
    activity_type      = Column(String, nullable=False)
    subject            = Column(String, nullable=False)
    description        = Column(String)
    activity_date      = Column(String, nullable=False)
    due_date           = Column(String, nullable=False)
    status             = Column(String, nullable=False, index=True)
    priority           = Column(String, nullable=False)
    # nullable FKs: an activity may link to any combination of the five entities below
    lead_id            = Column(String, ForeignKey("leads.lead_id"),                  nullable=True)
    contact_id         = Column(String, ForeignKey("contacts.contact_id"),            nullable=True)
    company_id         = Column(String, ForeignKey("companies.company_id"),           nullable=True)
    opportunity_id     = Column(String, ForeignKey("opportunities.opportunity_id"),   nullable=True)
    customer_id        = Column(String, ForeignKey("customers.customer_id"),          nullable=True)
    sales_rep_id       = Column(String, ForeignKey("sales_reps.rep_id"),             nullable=False)
    outcome            = Column(String, nullable=True)
    next_follow_up_date= Column(String, nullable=True)
    completed_at       = Column(String, nullable=True)
    created_at         = Column(String, nullable=False)
    updated_at         = Column(String, nullable=False)
    created_by         = Column(String)
    updated_by         = Column(String)
    deleted_at         = Column(String, nullable=True)

    lead        = relationship("Lead",        back_populates="activities",  foreign_keys=[lead_id])
    contact     = relationship("Contact",     back_populates="activities",  foreign_keys=[contact_id])
    company     = relationship("Company",     back_populates="activities",  foreign_keys=[company_id])
    opportunity = relationship("Opportunity", back_populates="activities",  foreign_keys=[opportunity_id])
    customer    = relationship("Customer",    back_populates="activities",  foreign_keys=[customer_id])
    sales_rep   = relationship("SalesRep",    back_populates="activities",  foreign_keys=[sales_rep_id])

    @property
    def resolved_company_name(self):
        if self.company: return self.company.company_name
        if self.customer and self.customer.company: return self.customer.company.company_name
        if self.opportunity and self.opportunity.company: return self.opportunity.company.company_name
        if self.lead and self.lead.company: return self.lead.company.company_name
        return None

    @property
    def resolved_contact_name(self):
        if self.contact: return self.contact.full_name
        if self.lead and self.lead.contact: return self.lead.contact.full_name
        if self.opportunity and self.opportunity.primary_contact: return self.opportunity.primary_contact.full_name
        return None

    @property
    def resolved_opportunity_name(self):
        if self.opportunity: return self.opportunity.opportunity_name
        if self.customer and self.customer.originating_opportunity: return self.customer.originating_opportunity.opportunity_name
        return None

    __table_args__ = (
        Index("ix_activity_rep_status", "sales_rep_id", "status"),
        Index("ix_activity_due_date",   "due_date"),
    )


# ---------------------------------------------------------------------------
# AI / RAG  (internal — not part of CRM data import)
# ---------------------------------------------------------------------------

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    session_id = Column(String, primary_key=True)
    user_id    = Column(String, ForeignKey("users.user_id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    user     = relationship("User",        back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    message_id = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey("chat_sessions.session_id"))
    role       = Column(String)   # 'user' | 'assistant' | 'tool'
    content    = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("ChatSession", back_populates="messages")


class CompanyDocument(Base):
    __tablename__ = "company_documents"

    doc_id      = Column(String, primary_key=True)
    company_id  = Column(String, ForeignKey("companies.company_id"), nullable=True)
    filename    = Column(String)
    title       = Column(String, nullable=True)
    file_type   = Column(String, nullable=True)
    file_size   = Column(Integer, nullable=True)
    processing_status = Column(String, default="Uploaded")
    chunk_count = Column(Integer, default=0)
    index_status = Column(String, nullable=True)
    uploaded_by = Column(String, ForeignKey("users.user_id"))
    created_at  = Column(DateTime, default=datetime.utcnow)

    company          = relationship("Company",  back_populates="documents")
    uploaded_by_user = relationship("User",     back_populates="documents", foreign_keys=[uploaded_by])
    chunks           = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    chunk_id        = Column(String, primary_key=True)
    document_id     = Column(String, ForeignKey("company_documents.doc_id", ondelete="CASCADE"))
    chunk_index     = Column(Integer)
    original_text   = Column(Text)
    section         = Column(String, nullable=True)
    subsection      = Column(String, nullable=True)
    source_file_type = Column(String, nullable=True)
    text            = Column(Text)
    page_number     = Column(Integer, nullable=True)
    character_count = Column(Integer)
    token_count     = Column(Integer, nullable=True)
    indexing_status = Column(String, default="Pending")
    created_at      = Column(DateTime, default=datetime.utcnow)

    document = relationship("CompanyDocument", back_populates="chunks")


# ---------------------------------------------------------------------------
# SETTINGS & AUTOMATION LOGS
# ---------------------------------------------------------------------------

class UserSettings(Base):
    __tablename__ = "user_settings"

    setting_id          = Column(String, primary_key=True)
    user_id             = Column(String, ForeignKey("users.user_id"), nullable=False, unique=True)
    email_notifications = Column(Boolean, default=True)
    updated_at          = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id])


class EmailHistory(Base):
    __tablename__ = "email_history"

    id              = Column(String, primary_key=True)
    recipient_email = Column(String, nullable=False, index=True)
    subject         = Column(String, nullable=False)
    email_type      = Column(String, nullable=False)
    status          = Column(String, nullable=False)  # e.g., 'Sent', 'Failed'
    sent_at         = Column(DateTime, default=datetime.utcnow)
    error_message   = Column(Text, nullable=True)

class SystemSettings(Base):
    __tablename__ = "system_settings"

    setting_key   = Column(String, primary_key=True)
    setting_value = Column(String, nullable=False)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id         = Column(String, ForeignKey("users.user_id"), nullable=True)

    user = relationship("User", foreign_keys=[user_id])
