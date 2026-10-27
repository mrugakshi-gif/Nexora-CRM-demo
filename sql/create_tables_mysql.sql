-- Indian B2B CRM Synthetic Dataset — MySQL 8.x schema
-- Creates all 18 source tables + 5 ML-ready tables, in dependency order.
-- Idempotent: safe to re-run. Requires MySQL 8.0.16+ for CHECK constraint enforcement.

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS churn_prediction_dataset;
DROP TABLE IF EXISTS customer_segmentation_dataset;
DROP TABLE IF EXISTS sales_forecasting_dataset;
DROP TABLE IF EXISTS lead_scoring_dataset;
DROP TABLE IF EXISTS lead_conversion_dataset;
DROP TABLE IF EXISTS customer_support_cases;
DROP TABLE IF EXISTS customer_transactions;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS opportunity_stage_history;
DROP TABLE IF EXISTS opportunity_products;
DROP TABLE IF EXISTS opportunities;
DROP TABLE IF EXISTS campaign_responses;
DROP TABLE IF EXISTS lead_status_history;
DROP TABLE IF EXISTS leads;
DROP TABLE IF EXISTS contacts;
DROP TABLE IF EXISTS companies;
DROP TABLE IF EXISTS campaigns;
DROP TABLE IF EXISTS sales_reps;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS lead_sources;
DROP TABLE IF EXISTS departments;
DROP TABLE IF EXISTS territories;
DROP TABLE IF EXISTS industries;

SET FOREIGN_KEY_CHECKS = 1;

-- =====================================================================
-- MASTER / REFERENCE TABLES
-- =====================================================================

CREATE TABLE industries (
    industry_id         VARCHAR(10)  PRIMARY KEY,
    industry_name        VARCHAR(120) NOT NULL,
    industry_category    VARCHAR(60)  NOT NULL,
    is_active            BOOLEAN      NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE territories (
    territory_id            VARCHAR(10) PRIMARY KEY,
    territory_name           VARCHAR(120) NOT NULL,
    region                   VARCHAR(30) NOT NULL,
    primary_industry_focus   VARCHAR(10),
    FOREIGN KEY (primary_industry_focus) REFERENCES industries(industry_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE departments (
    department_id    VARCHAR(10) PRIMARY KEY,
    department_name  VARCHAR(120) NOT NULL,
    region_focus     VARCHAR(30),
    created_at       DATE        NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE lead_sources (
    lead_source_id   VARCHAR(10) PRIMARY KEY,
    source_name      VARCHAR(120) NOT NULL,
    source_category  VARCHAR(60) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE products (
    product_id        VARCHAR(10)     PRIMARY KEY,
    product_name      VARCHAR(150)    NOT NULL,
    product_category  VARCHAR(80)     NOT NULL,
    pricing_model     VARCHAR(30)     NOT NULL,
    list_price_inr    DECIMAL(14,2)   NOT NULL,
    is_active         BOOLEAN         NOT NULL,
    CHECK (pricing_model IN ('Monthly Subscription','Annual Subscription','One-time','Usage-based'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE sales_reps (
    rep_id            VARCHAR(10) PRIMARY KEY,
    full_name         VARCHAR(120) NOT NULL,
    email             VARCHAR(150) NOT NULL UNIQUE,
    phone             VARCHAR(20) NOT NULL,
    department_id     VARCHAR(10) NOT NULL,
    manager_rep_id    VARCHAR(10),
    role              VARCHAR(60) NOT NULL,
    territory_id      VARCHAR(10),
    hire_date         DATE        NOT NULL,
    is_active         BOOLEAN     NOT NULL,
    termination_date  DATE,
    FOREIGN KEY (department_id) REFERENCES departments(department_id),
    FOREIGN KEY (manager_rep_id) REFERENCES sales_reps(rep_id),
    FOREIGN KEY (territory_id) REFERENCES territories(territory_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE campaigns (
    campaign_id           VARCHAR(10)     PRIMARY KEY,
    campaign_name         VARCHAR(200)    NOT NULL,
    campaign_type         VARCHAR(60)     NOT NULL,
    start_date            DATE            NOT NULL,
    end_date              DATE,
    budget_inr            DECIMAL(14,2),
    target_industry_id    VARCHAR(10),
    owner_department_id   VARCHAR(10)     NOT NULL,
    FOREIGN KEY (target_industry_id) REFERENCES industries(industry_id),
    FOREIGN KEY (owner_department_id) REFERENCES departments(department_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE companies (
    company_id                VARCHAR(15)     PRIMARY KEY,
    company_name              VARCHAR(200)    NOT NULL,
    name_is_real_entity       BOOLEAN         NOT NULL,
    industry_id               VARCHAR(10)     NOT NULL,
    sub_industry              VARCHAR(120),
    company_size_band         VARCHAR(20)     NOT NULL,
    annual_revenue_band_inr   VARCHAR(30),
    gstin                     VARCHAR(15),
    city                      VARCHAR(80)     NOT NULL,
    state                     VARCHAR(80)     NOT NULL,
    region                    VARCHAR(20)     NOT NULL,
    pincode                   VARCHAR(6),
    website_domain            VARCHAR(150),
    company_type              VARCHAR(30)     NOT NULL,
    founded_year              INT,
    account_owner_rep_id      VARCHAR(10),
    account_status            VARCHAR(30)     NOT NULL,
    created_at                DATETIME        NOT NULL,
    UNIQUE KEY uq_company_name_city (company_name, city),
    FOREIGN KEY (industry_id) REFERENCES industries(industry_id),
    FOREIGN KEY (account_owner_rep_id) REFERENCES sales_reps(rep_id),
    CHECK (company_size_band IN ('Micro','Small','Mid','Large','Enterprise')),
    CHECK (company_type IN ('Private Limited','Public Limited','LLP','Partnership','Proprietorship','PSU')),
    CHECK (account_status IN ('Prospect','Active Customer','Inactive Customer','Lost'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================================
-- TRANSACTIONAL TABLES
-- =====================================================================

CREATE TABLE contacts (
    contact_id          VARCHAR(15) PRIMARY KEY,
    company_id          VARCHAR(15) NOT NULL,
    full_name           VARCHAR(120) NOT NULL,
    job_title           VARCHAR(120) NOT NULL,
    seniority_level     VARCHAR(20) NOT NULL,
    department          VARCHAR(60) NOT NULL,
    email               VARCHAR(150) NOT NULL UNIQUE,
    phone               VARCHAR(20),
    is_primary_contact  BOOLEAN     NOT NULL,
    linkedin_handle     VARCHAR(150),
    is_decision_maker   BOOLEAN     NOT NULL,
    created_at          DATETIME    NOT NULL,
    FOREIGN KEY (company_id) REFERENCES companies(company_id),
    CHECK (seniority_level IN ('Junior','Mid','Senior','Manager','Director','VP','C-Level'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE leads (
    lead_id                       VARCHAR(15)     PRIMARY KEY,
    company_id                    VARCHAR(15)     NOT NULL,
    contact_id                    VARCHAR(15)     NOT NULL,
    lead_source_id                VARCHAR(10)     NOT NULL,
    campaign_id                   VARCHAR(10),
    assigned_rep_id               VARCHAR(10),
    lead_status                   VARCHAR(30)     NOT NULL,
    disqualification_reason       VARCHAR(150),
    industry_interest_id          VARCHAR(10),
    estimated_budget_inr          DECIMAL(14,2),
    company_size_at_lead_time     VARCHAR(20)     NOT NULL,
    created_at                    DATETIME        NOT NULL,
    first_contacted_at            DATETIME,
    qualified_at                  DATETIME,
    converted_at                  DATETIME,
    is_duplicate_of_lead_id       VARCHAR(15),
    FOREIGN KEY (company_id) REFERENCES companies(company_id),
    FOREIGN KEY (contact_id) REFERENCES contacts(contact_id),
    FOREIGN KEY (lead_source_id) REFERENCES lead_sources(lead_source_id),
    FOREIGN KEY (campaign_id) REFERENCES campaigns(campaign_id),
    FOREIGN KEY (assigned_rep_id) REFERENCES sales_reps(rep_id),
    FOREIGN KEY (industry_interest_id) REFERENCES industries(industry_id),
    FOREIGN KEY (is_duplicate_of_lead_id) REFERENCES leads(lead_id),
    CHECK (lead_status IN ('New','Contacted','Qualifying','Qualified (MQL)','Sales Qualified (SQL)',
                            'Converted','Disqualified','Dead','Nurture'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE lead_status_history (
    history_id           VARCHAR(15) PRIMARY KEY,
    lead_id               VARCHAR(15) NOT NULL,
    status_from           VARCHAR(30),
    status_to             VARCHAR(30) NOT NULL,
    changed_at            DATETIME    NOT NULL,
    changed_by_rep_id     VARCHAR(10),
    FOREIGN KEY (lead_id) REFERENCES leads(lead_id),
    FOREIGN KEY (changed_by_rep_id) REFERENCES sales_reps(rep_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE campaign_responses (
    response_id           VARCHAR(15) PRIMARY KEY,
    campaign_id            VARCHAR(10) NOT NULL,
    contact_id              VARCHAR(15) NOT NULL,
    response_type           VARCHAR(40) NOT NULL,
    response_date           DATE        NOT NULL,
    resulted_in_lead_id     VARCHAR(15),
    FOREIGN KEY (campaign_id) REFERENCES campaigns(campaign_id),
    FOREIGN KEY (contact_id) REFERENCES contacts(contact_id),
    FOREIGN KEY (resulted_in_lead_id) REFERENCES leads(lead_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE opportunities (
    opportunity_id       VARCHAR(15)     PRIMARY KEY,
    company_id           VARCHAR(15)     NOT NULL,
    primary_contact_id   VARCHAR(15)     NOT NULL,
    source_lead_id       VARCHAR(15)     NOT NULL,
    owner_rep_id         VARCHAR(10)     NOT NULL,
    opportunity_name     VARCHAR(250)    NOT NULL,
    pipeline_stage       VARCHAR(30)     NOT NULL,
    forecast_category    VARCHAR(30)     NOT NULL,
    deal_value_inr       DECIMAL(14,2)   NOT NULL,
    probability_pct      INT             NOT NULL,
    expected_close_date  DATE            NOT NULL,
    actual_close_date    DATE,
    close_outcome        VARCHAR(10),
    loss_reason          VARCHAR(150),
    competitor_name      VARCHAR(100),
    opportunity_type     VARCHAR(40)     NOT NULL,
    created_at            DATETIME       NOT NULL,
    FOREIGN KEY (company_id) REFERENCES companies(company_id),
    FOREIGN KEY (primary_contact_id) REFERENCES contacts(contact_id),
    FOREIGN KEY (source_lead_id) REFERENCES leads(lead_id),
    FOREIGN KEY (owner_rep_id) REFERENCES sales_reps(rep_id),
    CHECK (pipeline_stage IN ('Qualification','Discovery','Solution Fit','Proposal','Negotiation',
                               'Closed Won','Closed Lost')),
    CHECK (probability_pct BETWEEN 0 AND 100),
    CHECK (close_outcome IN ('Won','Lost') OR close_outcome IS NULL)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE opportunity_products (
    opportunity_product_id   VARCHAR(15)     PRIMARY KEY,
    opportunity_id           VARCHAR(15)     NOT NULL,
    product_id               VARCHAR(10)     NOT NULL,
    quantity                 INT             NOT NULL,
    unit_price_inr           DECIMAL(14,2)   NOT NULL,
    discount_pct             DECIMAL(5,2)    NOT NULL,
    line_total_inr           DECIMAL(14,2)   NOT NULL,
    FOREIGN KEY (opportunity_id) REFERENCES opportunities(opportunity_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id),
    CHECK (quantity > 0),
    CHECK (discount_pct BETWEEN 0 AND 100)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE opportunity_stage_history (
    history_id                VARCHAR(15) PRIMARY KEY,
    opportunity_id             VARCHAR(15) NOT NULL,
    stage_from                 VARCHAR(30),
    stage_to                   VARCHAR(30) NOT NULL,
    changed_at                 DATETIME    NOT NULL,
    days_in_previous_stage     INT,
    FOREIGN KEY (opportunity_id) REFERENCES opportunities(opportunity_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE customers (
    customer_id                  VARCHAR(15) PRIMARY KEY,
    company_id                   VARCHAR(15) NOT NULL UNIQUE,
    originating_opportunity_id   VARCHAR(15) NOT NULL,
    customer_since               DATE        NOT NULL,
    csm_rep_id                   VARCHAR(10) NOT NULL,
    customer_tier                VARCHAR(20) NOT NULL,
    contract_type                VARCHAR(20) NOT NULL,
    renewal_date                 DATE,
    customer_status                VARCHAR(20) NOT NULL,
    FOREIGN KEY (company_id) REFERENCES companies(company_id),
    FOREIGN KEY (originating_opportunity_id) REFERENCES opportunities(opportunity_id),
    FOREIGN KEY (csm_rep_id) REFERENCES sales_reps(rep_id),
    CHECK (customer_tier IN ('Bronze','Silver','Gold','Platinum')),
    CHECK (contract_type IN ('Monthly','Annual','Multi-Year')),
    CHECK (customer_status IN ('Active','At Risk','Paused','Churned'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE customer_transactions (
    transaction_id     VARCHAR(15)     PRIMARY KEY,
    customer_id        VARCHAR(15)     NOT NULL,
    opportunity_id     VARCHAR(15),
    transaction_date   DATE            NOT NULL,
    transaction_type   VARCHAR(20)     NOT NULL,
    amount_inr         DECIMAL(14,2)   NOT NULL,
    payment_status     VARCHAR(20)     NOT NULL,
    invoice_number     VARCHAR(40)     NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (opportunity_id) REFERENCES opportunities(opportunity_id),
    CHECK (transaction_type IN ('New Sale','Renewal','Upsell','Downgrade','Refund')),
    CHECK (payment_status IN ('Paid','Pending','Overdue','Partially Paid'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE customer_support_cases (
    case_id               VARCHAR(15) PRIMARY KEY,
    customer_id            VARCHAR(15) NOT NULL,
    contact_id             VARCHAR(15),
    case_type              VARCHAR(40) NOT NULL,
    priority               VARCHAR(20) NOT NULL,
    status                 VARCHAR(20) NOT NULL,
    opened_at              DATETIME    NOT NULL,
    resolved_at            DATETIME,
    satisfaction_score     INT,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (contact_id) REFERENCES contacts(contact_id),
    CHECK (priority IN ('Low','Medium','High','Critical')),
    CHECK (status IN ('Open','In Progress','Escalated','Resolved','Closed')),
    CHECK (satisfaction_score BETWEEN 1 AND 5 OR satisfaction_score IS NULL)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE activities (
    activity_id             VARCHAR(15) PRIMARY KEY,
    activity_type            VARCHAR(30) NOT NULL,
    subject                  VARCHAR(255) NOT NULL,
    description               TEXT,
    activity_date             DATETIME    NOT NULL,
    due_date                  DATE        NOT NULL,
    status                    VARCHAR(20) NOT NULL,
    priority                  VARCHAR(20) NOT NULL,
    lead_id                   VARCHAR(15),
    contact_id                VARCHAR(15),
    company_id                VARCHAR(15),
    opportunity_id             VARCHAR(15),
    customer_id                VARCHAR(15),
    sales_rep_id               VARCHAR(15) NOT NULL,
    outcome                    TEXT,
    next_follow_up_date         DATE,
    created_at                 DATETIME    NOT NULL,
    updated_at                 DATETIME    NOT NULL,
    FOREIGN KEY (lead_id) REFERENCES leads(lead_id),
    FOREIGN KEY (contact_id) REFERENCES contacts(contact_id),
    FOREIGN KEY (company_id) REFERENCES companies(company_id),
    FOREIGN KEY (opportunity_id) REFERENCES opportunities(opportunity_id),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (sales_rep_id) REFERENCES sales_reps(rep_id),
    CHECK (activity_type IN ('Call','Email','Meeting','Demo','Follow-up','Task',
                              'Site Visit','Proposal Discussion','Negotiation','Support Follow-up')),
    CHECK (status IN ('Completed','Planned','Pending','In Progress','Rescheduled','Cancelled')),
    CHECK (priority IN ('Low','Medium','High','Urgent'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================================
-- ML-READY TABLES (derived; FKs kept only for traceability)
-- =====================================================================

CREATE TABLE lead_conversion_dataset (
    ml_record_id                          VARCHAR(20) PRIMARY KEY,
    lead_id                               VARCHAR(15) NOT NULL,
    company_id                            VARCHAR(15) NOT NULL,
    observation_cutoff_at                 DATETIME    NOT NULL,
    industry_id                           VARCHAR(10),
    region                                VARCHAR(20),
    company_size_at_lead_time             VARCHAR(20),
    lead_source_category                  VARCHAR(40),
    campaign_sourced_flag                 BOOLEAN,
    contact_seniority_level               VARCHAR(20),
    contact_is_decision_maker             BOOLEAN,
    estimated_budget_known                BOOLEAN,
    estimated_budget_band                 VARCHAR(30),
    days_since_created_to_cutoff          INT,
    num_status_transitions_before_cutoff  INT,
    rep_assigned_flag                     BOOLEAN,
    rep_trailing_conversion_rate          DECIMAL(6,4),
    is_duplicate_lead                     BOOLEAN,
    label_converted                       BOOLEAN     NOT NULL,
    dataset_split                         VARCHAR(12) NOT NULL,
    FOREIGN KEY (lead_id) REFERENCES leads(lead_id),
    FOREIGN KEY (company_id) REFERENCES companies(company_id),
    CHECK (dataset_split IN ('train','validation','test'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE lead_scoring_dataset (
    ml_record_id                VARCHAR(20) PRIMARY KEY,
    lead_id                     VARCHAR(15) NOT NULL,
    company_id                  VARCHAR(15) NOT NULL,
    observation_cutoff_at       DATETIME    NOT NULL,
    industry_id                 VARCHAR(10),
    region                      VARCHAR(20),
    company_size_at_lead_time   VARCHAR(20),
    lead_source_category        VARCHAR(40),
    campaign_sourced_flag       BOOLEAN,
    contact_seniority_level     VARCHAR(20),
    contact_is_decision_maker   BOOLEAN,
    contact_department          VARCHAR(60),
    label_converted              BOOLEAN    NOT NULL,
    dataset_split                VARCHAR(12) NOT NULL,
    FOREIGN KEY (lead_id) REFERENCES leads(lead_id),
    FOREIGN KEY (company_id) REFERENCES companies(company_id),
    CHECK (dataset_split IN ('train','validation','test'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE sales_forecasting_dataset (
    ml_record_id                                 VARCHAR(20)     PRIMARY KEY,
    department_id                                VARCHAR(10)     NOT NULL,
    department_name                              VARCHAR(120),
    period_label                                 VARCHAR(20)     NOT NULL,
    period_start                                 DATE            NOT NULL,
    pipeline_value_open_at_period_start_inr      DECIMAL(14,2),
    num_open_opportunities_at_period_start       INT,
    historical_win_rate_trailing_3mo             DECIMAL(6,4),
    revenue_trailing_3mo_inr                     DECIMAL(14,2),
    avg_deal_cycle_days_trailing_6mo             DECIMAL(8,2),
    active_rep_count                             INT,
    seasonality_month                            INT,
    label_actual_amount_inr                      DECIMAL(14,2)   NOT NULL,
    dataset_split                                VARCHAR(12)     NOT NULL,
    FOREIGN KEY (department_id) REFERENCES departments(department_id),
    CHECK (seasonality_month BETWEEN 1 AND 12),
    CHECK (dataset_split IN ('train','validation','test'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE customer_segmentation_dataset (
    ml_record_id                           VARCHAR(20)     PRIMARY KEY,
    customer_id                            VARCHAR(15)     NOT NULL,
    company_id                             VARCHAR(15)     NOT NULL,
    snapshot_date                          DATE            NOT NULL,
    recency_days_since_last_transaction    INT,
    frequency_transactions_last_12mo       INT,
    monetary_total_last_12mo_inr           DECIMAL(14,2),
    tenure_months_at_snapshot              DECIMAL(6,1),
    support_case_count_last_12mo           INT,
    avg_satisfaction_score                 DECIMAL(4,2),
    product_category_diversity             INT,
    industry_id                            VARCHAR(10),
    company_size_band                      VARCHAR(20),
    customer_tier                          VARCHAR(20),
    contract_type                          VARCHAR(20),
    -- No cluster/segment-label column by design: this is an unsupervised
    -- feature table with no ground-truth cluster to ship -- see
    -- docs/ml_dataset_documentation.md and docs/ml_leakage_prevention.md rule 9.4.
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE churn_prediction_dataset (
    ml_record_id                              VARCHAR(20)     PRIMARY KEY,
    customer_id                               VARCHAR(15)     NOT NULL,
    company_id                                VARCHAR(15)     NOT NULL,
    observation_snapshot_date                 DATE            NOT NULL,
    renewal_due_date                          DATE            NOT NULL,
    tenure_months_at_snapshot                 DECIMAL(6,1),
    days_since_last_transaction_at_snapshot   INT,
    support_case_count_trailing_90d           INT,
    avg_case_priority_trailing_90d            DECIMAL(4,2),
    contract_type                             VARCHAR(20),
    customer_tier                             VARCHAR(20),
    transaction_amount_trailing_90d_inr       DECIMAL(14,2),
    transaction_amount_trend_90d_inr          DECIMAL(14,2),
    label_churned_within_horizon              BOOLEAN         NOT NULL,
    horizon_days                              INT             NOT NULL,
    dataset_split                             VARCHAR(12)     NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (company_id) REFERENCES companies(company_id),
    CHECK (dataset_split IN ('train','validation','test'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================================
-- Recommended indexes beyond PK/FK (see docs/recommended_schema.md §3)
-- =====================================================================

CREATE INDEX idx_leads_rep_status ON leads(assigned_rep_id, lead_status);
CREATE INDEX idx_opps_rep_stage ON opportunities(owner_rep_id, pipeline_stage);
CREATE INDEX idx_opps_expected_close ON opportunities(expected_close_date);
CREATE INDEX idx_txn_customer_date ON customer_transactions(customer_id, transaction_date);
CREATE INDEX idx_lsh_lead_changed ON lead_status_history(lead_id, changed_at);
CREATE INDEX idx_osh_opp_changed ON opportunity_stage_history(opportunity_id, changed_at);
