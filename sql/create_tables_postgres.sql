-- Indian B2B CRM Synthetic Dataset — PostgreSQL schema
-- Creates all 18 source tables + 5 ML-ready tables, in dependency order.
-- Idempotent: safe to re-run (drops and recreates everything below).

BEGIN;

DROP TABLE IF EXISTS churn_prediction_dataset CASCADE;
DROP TABLE IF EXISTS customer_segmentation_dataset CASCADE;
DROP TABLE IF EXISTS sales_forecasting_dataset CASCADE;
DROP TABLE IF EXISTS lead_scoring_dataset CASCADE;
DROP TABLE IF EXISTS lead_conversion_dataset CASCADE;
DROP TABLE IF EXISTS customer_support_cases CASCADE;
DROP TABLE IF EXISTS customer_transactions CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS opportunity_stage_history CASCADE;
DROP TABLE IF EXISTS opportunity_products CASCADE;
DROP TABLE IF EXISTS opportunities CASCADE;
DROP TABLE IF EXISTS campaign_responses CASCADE;
DROP TABLE IF EXISTS lead_status_history CASCADE;
DROP TABLE IF EXISTS leads CASCADE;
DROP TABLE IF EXISTS contacts CASCADE;
DROP TABLE IF EXISTS companies CASCADE;
DROP TABLE IF EXISTS campaigns CASCADE;
DROP TABLE IF EXISTS sales_reps CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS lead_sources CASCADE;
DROP TABLE IF EXISTS departments CASCADE;
DROP TABLE IF EXISTS territories CASCADE;
DROP TABLE IF EXISTS industries CASCADE;

-- =====================================================================
-- MASTER / REFERENCE TABLES
-- =====================================================================

CREATE TABLE industries (
    industry_id         VARCHAR(10)  PRIMARY KEY,
    industry_name        TEXT         NOT NULL,
    industry_category    TEXT         NOT NULL,
    is_active            BOOLEAN      NOT NULL
);

CREATE TABLE territories (
    territory_id            VARCHAR(10) PRIMARY KEY,
    territory_name           TEXT        NOT NULL,
    region                   TEXT        NOT NULL,
    primary_industry_focus   VARCHAR(10) REFERENCES industries(industry_id)
);

CREATE TABLE departments (
    department_id    VARCHAR(10) PRIMARY KEY,
    department_name  TEXT        NOT NULL,
    region_focus     TEXT,
    created_at       DATE        NOT NULL
);

CREATE TABLE lead_sources (
    lead_source_id   VARCHAR(10) PRIMARY KEY,
    source_name      TEXT        NOT NULL,
    source_category  TEXT        NOT NULL
);

CREATE TABLE products (
    product_id        VARCHAR(10)     PRIMARY KEY,
    product_name      TEXT            NOT NULL,
    product_category  TEXT            NOT NULL,
    pricing_model     TEXT            NOT NULL
        CHECK (pricing_model IN ('Monthly Subscription','Annual Subscription','One-time','Usage-based')),
    list_price_inr    NUMERIC(14,2)   NOT NULL,
    is_active         BOOLEAN         NOT NULL
);

CREATE TABLE sales_reps (
    rep_id            VARCHAR(10) PRIMARY KEY,
    full_name         TEXT        NOT NULL,
    email             TEXT        NOT NULL UNIQUE,
    phone             TEXT        NOT NULL,
    department_id     VARCHAR(10) NOT NULL REFERENCES departments(department_id),
    manager_rep_id    VARCHAR(10) REFERENCES sales_reps(rep_id),
    role              TEXT        NOT NULL,
    territory_id      VARCHAR(10) REFERENCES territories(territory_id),
    hire_date         DATE        NOT NULL,
    is_active         BOOLEAN     NOT NULL,
    termination_date  DATE
);

CREATE TABLE campaigns (
    campaign_id           VARCHAR(10)     PRIMARY KEY,
    campaign_name         TEXT            NOT NULL,
    campaign_type         TEXT            NOT NULL,
    start_date            DATE            NOT NULL,
    end_date              DATE,
    budget_inr            NUMERIC(14,2),
    target_industry_id    VARCHAR(10)     REFERENCES industries(industry_id),
    owner_department_id   VARCHAR(10)     NOT NULL REFERENCES departments(department_id)
);

CREATE TABLE companies (
    company_id                VARCHAR(15)     PRIMARY KEY,
    company_name              TEXT            NOT NULL,
    name_is_real_entity       BOOLEAN         NOT NULL,
    industry_id               VARCHAR(10)     NOT NULL REFERENCES industries(industry_id),
    sub_industry              TEXT,
    company_size_band         TEXT            NOT NULL
        CHECK (company_size_band IN ('Micro','Small','Mid','Large','Enterprise')),
    annual_revenue_band_inr   TEXT,
    gstin                     TEXT,
    city                      TEXT            NOT NULL,
    state                     TEXT            NOT NULL,
    region                    TEXT            NOT NULL,
    pincode                   TEXT,
    website_domain            TEXT,
    company_type              TEXT            NOT NULL
        CHECK (company_type IN ('Private Limited','Public Limited','LLP','Partnership','Proprietorship','PSU')),
    founded_year              INTEGER,
    account_owner_rep_id      VARCHAR(10)     REFERENCES sales_reps(rep_id),
    account_status            TEXT            NOT NULL
        CHECK (account_status IN ('Prospect','Active Customer','Inactive Customer','Lost')),
    created_at                TIMESTAMP       NOT NULL,
    UNIQUE (company_name, city)
);

-- =====================================================================
-- TRANSACTIONAL TABLES
-- =====================================================================

CREATE TABLE contacts (
    contact_id          VARCHAR(15) PRIMARY KEY,
    company_id          VARCHAR(15) NOT NULL REFERENCES companies(company_id),
    full_name           TEXT        NOT NULL,
    job_title           TEXT        NOT NULL,
    seniority_level     TEXT        NOT NULL
        CHECK (seniority_level IN ('Junior','Mid','Senior','Manager','Director','VP','C-Level')),
    department          TEXT        NOT NULL,
    email               TEXT        NOT NULL UNIQUE,
    phone               TEXT,
    is_primary_contact  BOOLEAN     NOT NULL,
    linkedin_handle     TEXT,
    is_decision_maker   BOOLEAN     NOT NULL,
    created_at          TIMESTAMP   NOT NULL
);

CREATE TABLE leads (
    lead_id                       VARCHAR(15)     PRIMARY KEY,
    company_id                    VARCHAR(15)     NOT NULL REFERENCES companies(company_id),
    contact_id                    VARCHAR(15)     NOT NULL REFERENCES contacts(contact_id),
    lead_source_id                VARCHAR(10)     NOT NULL REFERENCES lead_sources(lead_source_id),
    campaign_id                   VARCHAR(10)     REFERENCES campaigns(campaign_id),
    assigned_rep_id               VARCHAR(10)     REFERENCES sales_reps(rep_id),
    lead_status                   TEXT            NOT NULL
        CHECK (lead_status IN ('New','Contacted','Qualifying','Qualified (MQL)','Sales Qualified (SQL)',
                                'Converted','Disqualified','Dead','Nurture')),
    disqualification_reason       TEXT,
    industry_interest_id          VARCHAR(10)     REFERENCES industries(industry_id),
    estimated_budget_inr          NUMERIC(14,2),
    company_size_at_lead_time     TEXT            NOT NULL,
    created_at                    TIMESTAMP       NOT NULL,
    first_contacted_at            TIMESTAMP,
    qualified_at                  TIMESTAMP,
    converted_at                  TIMESTAMP,
    is_duplicate_of_lead_id       VARCHAR(15)     REFERENCES leads(lead_id)
);

CREATE TABLE lead_status_history (
    history_id           VARCHAR(15) PRIMARY KEY,
    lead_id               VARCHAR(15) NOT NULL REFERENCES leads(lead_id),
    status_from           TEXT,
    status_to             TEXT        NOT NULL,
    changed_at            TIMESTAMP   NOT NULL,
    changed_by_rep_id     VARCHAR(10) REFERENCES sales_reps(rep_id)
);

CREATE TABLE campaign_responses (
    response_id           VARCHAR(15) PRIMARY KEY,
    campaign_id            VARCHAR(10) NOT NULL REFERENCES campaigns(campaign_id),
    contact_id              VARCHAR(15) NOT NULL REFERENCES contacts(contact_id),
    response_type           TEXT        NOT NULL,
    response_date           DATE        NOT NULL,
    resulted_in_lead_id     VARCHAR(15) REFERENCES leads(lead_id)
);

CREATE TABLE opportunities (
    opportunity_id       VARCHAR(15)     PRIMARY KEY,
    company_id           VARCHAR(15)     NOT NULL REFERENCES companies(company_id),
    primary_contact_id   VARCHAR(15)     NOT NULL REFERENCES contacts(contact_id),
    source_lead_id       VARCHAR(15)     NOT NULL REFERENCES leads(lead_id),
    owner_rep_id         VARCHAR(10)     NOT NULL REFERENCES sales_reps(rep_id),
    opportunity_name     TEXT            NOT NULL,
    pipeline_stage       TEXT            NOT NULL
        CHECK (pipeline_stage IN ('Qualification','Discovery','Solution Fit','Proposal','Negotiation',
                                   'Closed Won','Closed Lost')),
    forecast_category    TEXT            NOT NULL,
    deal_value_inr       NUMERIC(14,2)   NOT NULL,
    probability_pct      INTEGER         NOT NULL CHECK (probability_pct BETWEEN 0 AND 100),
    expected_close_date  DATE            NOT NULL,
    actual_close_date    DATE,
    close_outcome        TEXT            CHECK (close_outcome IN ('Won','Lost') OR close_outcome IS NULL),
    loss_reason          TEXT,
    competitor_name      TEXT,
    opportunity_type     TEXT            NOT NULL,
    created_at            TIMESTAMP      NOT NULL
);

CREATE TABLE opportunity_products (
    opportunity_product_id   VARCHAR(15)     PRIMARY KEY,
    opportunity_id           VARCHAR(15)     NOT NULL REFERENCES opportunities(opportunity_id),
    product_id               VARCHAR(10)     NOT NULL REFERENCES products(product_id),
    quantity                 INTEGER         NOT NULL CHECK (quantity > 0),
    unit_price_inr           NUMERIC(14,2)   NOT NULL,
    discount_pct             NUMERIC(5,2)    NOT NULL CHECK (discount_pct BETWEEN 0 AND 100),
    line_total_inr           NUMERIC(14,2)   NOT NULL
);

CREATE TABLE opportunity_stage_history (
    history_id                VARCHAR(15) PRIMARY KEY,
    opportunity_id             VARCHAR(15) NOT NULL REFERENCES opportunities(opportunity_id),
    stage_from                 TEXT,
    stage_to                   TEXT        NOT NULL,
    changed_at                 TIMESTAMP   NOT NULL,
    days_in_previous_stage     INTEGER
);

CREATE TABLE customers (
    customer_id                  VARCHAR(15) PRIMARY KEY,
    company_id                   VARCHAR(15) NOT NULL UNIQUE REFERENCES companies(company_id),
    originating_opportunity_id   VARCHAR(15) NOT NULL REFERENCES opportunities(opportunity_id),
    customer_since               DATE        NOT NULL,
    csm_rep_id                   VARCHAR(10) NOT NULL REFERENCES sales_reps(rep_id),
    customer_tier                TEXT        NOT NULL
        CHECK (customer_tier IN ('Bronze','Silver','Gold','Platinum')),
    contract_type                TEXT        NOT NULL
        CHECK (contract_type IN ('Monthly','Annual','Multi-Year')),
    renewal_date                 DATE,
    customer_status               TEXT       NOT NULL
        CHECK (customer_status IN ('Active','At Risk','Paused','Churned'))
);

CREATE TABLE customer_transactions (
    transaction_id     VARCHAR(15)     PRIMARY KEY,
    customer_id        VARCHAR(15)     NOT NULL REFERENCES customers(customer_id),
    opportunity_id     VARCHAR(15)     REFERENCES opportunities(opportunity_id),
    transaction_date   DATE            NOT NULL,
    transaction_type   TEXT            NOT NULL
        CHECK (transaction_type IN ('New Sale','Renewal','Upsell','Downgrade','Refund')),
    amount_inr         NUMERIC(14,2)   NOT NULL,
    payment_status     TEXT            NOT NULL
        CHECK (payment_status IN ('Paid','Pending','Overdue','Partially Paid')),
    invoice_number     TEXT            NOT NULL
);

CREATE TABLE customer_support_cases (
    case_id               VARCHAR(15) PRIMARY KEY,
    customer_id            VARCHAR(15) NOT NULL REFERENCES customers(customer_id),
    contact_id             VARCHAR(15) REFERENCES contacts(contact_id),
    case_type              TEXT        NOT NULL,
    priority               TEXT        NOT NULL CHECK (priority IN ('Low','Medium','High','Critical')),
    status                 TEXT        NOT NULL
        CHECK (status IN ('Open','In Progress','Escalated','Resolved','Closed')),
    opened_at              TIMESTAMP   NOT NULL,
    resolved_at            TIMESTAMP,
    satisfaction_score     INTEGER     CHECK (satisfaction_score BETWEEN 1 AND 5)
);

CREATE TABLE activities (
    activity_id             VARCHAR(15) PRIMARY KEY,
    activity_type            TEXT        NOT NULL
        CHECK (activity_type IN ('Call','Email','Meeting','Demo','Follow-up','Task',
                                  'Site Visit','Proposal Discussion','Negotiation','Support Follow-up')),
    subject                  TEXT        NOT NULL,
    description               TEXT,
    activity_date             TIMESTAMP   NOT NULL,
    due_date                  DATE        NOT NULL,
    status                    TEXT        NOT NULL
        CHECK (status IN ('Completed','Planned','Pending','In Progress','Rescheduled','Cancelled')),
    priority                  TEXT        NOT NULL CHECK (priority IN ('Low','Medium','High','Urgent')),
    lead_id                   VARCHAR(15) REFERENCES leads(lead_id),
    contact_id                VARCHAR(15) REFERENCES contacts(contact_id),
    company_id                VARCHAR(15) REFERENCES companies(company_id),
    opportunity_id             VARCHAR(15) REFERENCES opportunities(opportunity_id),
    customer_id                VARCHAR(15) REFERENCES customers(customer_id),
    sales_rep_id               VARCHAR(15) NOT NULL REFERENCES sales_reps(rep_id),
    outcome                    TEXT,
    next_follow_up_date         DATE,
    created_at                 TIMESTAMP   NOT NULL,
    updated_at                 TIMESTAMP   NOT NULL
);

-- =====================================================================
-- ML-READY TABLES (derived; FKs kept only for traceability)
-- =====================================================================

CREATE TABLE lead_conversion_dataset (
    ml_record_id                          VARCHAR(20) PRIMARY KEY,
    lead_id                               VARCHAR(15) NOT NULL REFERENCES leads(lead_id),
    company_id                            VARCHAR(15) NOT NULL REFERENCES companies(company_id),
    observation_cutoff_at                 TIMESTAMP   NOT NULL,
    industry_id                           VARCHAR(10),
    region                                TEXT,
    company_size_at_lead_time             TEXT,
    lead_source_category                  TEXT,
    campaign_sourced_flag                 BOOLEAN,
    contact_seniority_level               TEXT,
    contact_is_decision_maker             BOOLEAN,
    estimated_budget_known                BOOLEAN,
    estimated_budget_band                 TEXT,
    days_since_created_to_cutoff          INTEGER,
    num_status_transitions_before_cutoff  INTEGER,
    rep_assigned_flag                     BOOLEAN,
    rep_trailing_conversion_rate          NUMERIC(6,4),
    is_duplicate_lead                     BOOLEAN,
    label_converted                       BOOLEAN     NOT NULL,
    dataset_split                         TEXT        NOT NULL CHECK (dataset_split IN ('train','validation','test'))
);

CREATE TABLE lead_scoring_dataset (
    ml_record_id                VARCHAR(20) PRIMARY KEY,
    lead_id                     VARCHAR(15) NOT NULL REFERENCES leads(lead_id),
    company_id                  VARCHAR(15) NOT NULL REFERENCES companies(company_id),
    observation_cutoff_at       TIMESTAMP   NOT NULL,
    industry_id                 VARCHAR(10),
    region                      TEXT,
    company_size_at_lead_time   TEXT,
    lead_source_category        TEXT,
    campaign_sourced_flag       BOOLEAN,
    contact_seniority_level     TEXT,
    contact_is_decision_maker   BOOLEAN,
    contact_department          TEXT,
    label_converted              BOOLEAN    NOT NULL,
    dataset_split                TEXT       NOT NULL CHECK (dataset_split IN ('train','validation','test'))
);

CREATE TABLE sales_forecasting_dataset (
    ml_record_id                                 VARCHAR(20)     PRIMARY KEY,
    department_id                                VARCHAR(10)     NOT NULL REFERENCES departments(department_id),
    department_name                              TEXT,
    period_label                                 TEXT            NOT NULL,
    period_start                                 DATE            NOT NULL,
    pipeline_value_open_at_period_start_inr      NUMERIC(14,2),
    num_open_opportunities_at_period_start       INTEGER,
    historical_win_rate_trailing_3mo             NUMERIC(6,4),
    revenue_trailing_3mo_inr                     NUMERIC(14,2),
    avg_deal_cycle_days_trailing_6mo             NUMERIC(8,2),
    active_rep_count                             INTEGER,
    seasonality_month                            INTEGER CHECK (seasonality_month BETWEEN 1 AND 12),
    label_actual_amount_inr                      NUMERIC(14,2)   NOT NULL,
    dataset_split                                TEXT            NOT NULL CHECK (dataset_split IN ('train','validation','test'))
);

CREATE TABLE customer_segmentation_dataset (
    ml_record_id                           VARCHAR(20)     PRIMARY KEY,
    customer_id                            VARCHAR(15)     NOT NULL REFERENCES customers(customer_id),
    company_id                             VARCHAR(15)     NOT NULL REFERENCES companies(company_id),
    snapshot_date                          DATE            NOT NULL,
    recency_days_since_last_transaction    INTEGER,
    frequency_transactions_last_12mo       INTEGER,
    monetary_total_last_12mo_inr           NUMERIC(14,2),
    tenure_months_at_snapshot              NUMERIC(6,1),
    support_case_count_last_12mo           INTEGER,
    avg_satisfaction_score                 NUMERIC(4,2),
    product_category_diversity             INTEGER,
    industry_id                            VARCHAR(10),
    company_size_band                      TEXT,
    customer_tier                          TEXT,
    contract_type                          TEXT
    -- No cluster/segment-label column by design: this is an unsupervised
    -- feature table with no ground-truth cluster to ship. Run your own
    -- clustering model against these columns to produce assignments -- see
    -- docs/ml_dataset_documentation.md and docs/ml_leakage_prevention.md rule 9.4.
);

CREATE TABLE churn_prediction_dataset (
    ml_record_id                              VARCHAR(20)     PRIMARY KEY,
    customer_id                               VARCHAR(15)     NOT NULL REFERENCES customers(customer_id),
    company_id                                VARCHAR(15)     NOT NULL REFERENCES companies(company_id),
    observation_snapshot_date                 DATE            NOT NULL,
    renewal_due_date                          DATE            NOT NULL,
    tenure_months_at_snapshot                 NUMERIC(6,1),
    days_since_last_transaction_at_snapshot   INTEGER,
    support_case_count_trailing_90d           INTEGER,
    avg_case_priority_trailing_90d            NUMERIC(4,2),
    contract_type                             TEXT,
    customer_tier                             TEXT,
    transaction_amount_trailing_90d_inr       NUMERIC(14,2),
    transaction_amount_trend_90d_inr          NUMERIC(14,2),
    label_churned_within_horizon              BOOLEAN         NOT NULL,
    horizon_days                              INTEGER         NOT NULL,
    dataset_split                             TEXT            NOT NULL CHECK (dataset_split IN ('train','validation','test'))
);

-- =====================================================================
-- Recommended indexes beyond PK/FK (see docs/recommended_schema.md §3)
-- =====================================================================

CREATE INDEX idx_leads_rep_status ON leads(assigned_rep_id, lead_status);
CREATE INDEX idx_opps_rep_stage ON opportunities(owner_rep_id, pipeline_stage);
CREATE INDEX idx_opps_expected_close ON opportunities(expected_close_date);
CREATE INDEX idx_txn_customer_date ON customer_transactions(customer_id, transaction_date);
CREATE INDEX idx_lsh_lead_changed ON lead_status_history(lead_id, changed_at);
CREATE INDEX idx_osh_opp_changed ON opportunity_stage_history(opportunity_id, changed_at);

COMMIT;
