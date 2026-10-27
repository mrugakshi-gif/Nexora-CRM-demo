# Data Dictionary

All ID columns are strings with a fixed prefix and fixed zero-padded width (e.g. `COMP-000001`); all monetary columns are INR, stored as decimals; all timestamp columns are `YYYY-MM-DD HH:MM:SS`; all date-only columns are `YYYY-MM-DD`; boolean columns are the literal strings `True`/`False` in the CSVs (cast to native booleans on import — see `sql/create_tables_*.sql`). "PK" = primary key, "FK" = foreign key. Nullable means the CSV cell may be blank.

---

## Master / reference tables

### industries
| Column | Type | Nullable | Description |
|---|---|---|---|
| industry_id | PK, `IND-##` | No | Industry code |
| industry_name | text | No | e.g. "Logistics & Transportation" |
| industry_category | text | No | Broader grouping (e.g. "Industrial") |
| is_active | boolean | No | Whether new companies are still assigned to this industry |

### territories
| Column | Type | Nullable | Description |
|---|---|---|---|
| territory_id | PK, `TERR-###` | No | Territory code |
| territory_name | text | No | Sales territory name |
| region | text | No | North / South / East / West |
| primary_industry_focus | FK → industries.industry_id | Yes | Industry this territory is weighted toward, if any |

### departments
| Column | Type | Nullable | Description |
|---|---|---|---|
| department_id | PK, `DEPT-####` | No | Department code |
| department_name | text | No | e.g. "Enterprise Sales", "Customer Success" |
| region_focus | text | Yes | Region this department primarily serves |
| created_at | date | No | Department creation date |

### lead_sources
| Column | Type | Nullable | Description |
|---|---|---|---|
| lead_source_id | PK, `SRC-##` | No | Source code |
| source_name | text | No | e.g. "Organic Search", "Referral", "Trade Show" |
| source_category | text | No | Inbound / Outbound / Partner / Referral |

### products
| Column | Type | Nullable | Description |
|---|---|---|---|
| product_id | PK, `PROD-###` | No | Product/SKU code |
| product_name | text | No | Product name |
| product_category | text | No | Product line grouping |
| pricing_model | text | No | Monthly Subscription / Annual Subscription / One-time / Usage-based |
| list_price_inr | decimal | No | Catalog list price (per the unit implied by pricing_model) |
| is_active | boolean | No | Whether still sellable |

### sales_reps
| Column | Type | Nullable | Description |
|---|---|---|---|
| rep_id | PK, `REP-####` | No | Sales rep code |
| full_name | text | No | Rep's name (synthetic) |
| email | text | No | Synthetic corporate email (`@crmvendor-india.example`) |
| phone | text | No | Synthetic phone, format `+91-XXXXXXXXXX` |
| department_id | FK → departments.department_id | No | Rep's department |
| manager_rep_id | FK → sales_reps.rep_id (self) | Yes | Reporting manager; blank for the Director at the top of the hierarchy |
| role | text | No | Director / Manager / Senior Account Executive / Account Executive / SDR / Customer Success Manager |
| territory_id | FK → territories.territory_id | Yes | Assigned territory |
| hire_date | date | No | Hire date |
| is_active | boolean | No | Currently employed |
| termination_date | date | Yes | Populated only when `is_active = False` |

### campaigns
| Column | Type | Nullable | Description |
|---|---|---|---|
| campaign_id | PK, `CAMP-###` | No | Campaign code |
| campaign_name | text | No | Campaign name incl. fiscal-period tag |
| campaign_type | text | No | Email / Social Media / Paid Search / Webinar / Trade Show / etc. |
| start_date | date | No | Campaign start |
| end_date | date | Yes | Campaign end (blank = ongoing at generation time) |
| budget_inr | decimal | No | Allocated budget |
| target_industry_id | FK → industries.industry_id | Yes | Primary industry targeted |
| owner_department_id | FK → departments.department_id | No | Owning department |

### companies
| Column | Type | Nullable | Description |
|---|---|---|---|
| company_id | PK, `COMP-######` | No | Company code |
| company_name | text | No | Company name (real-anchor or synthetic — see `name_is_real_entity`) |
| name_is_real_entity | boolean | No | **True only for the curated real-company subset (~8% of rows).** See README §"Which data is real". |
| industry_id | FK → industries.industry_id | No | Company's industry |
| sub_industry | text | Yes | One of a fixed vocabulary of 3–5 sub-industries per `industry_id` (e.g. IT & Software Services → "IT Services & Consulting" / "Software Products/SaaS" / "IT Infrastructure & Cloud" / "Cybersecurity" / "BPO/ITES") — populated for ~95% of companies; blank for ~5%, matching the sparsity real CRM sub-classification data shows (see `business_rules.md` rule 4.9 and `data_quality_report.md` §1.8) |
| company_size_band | text | No | Micro / Small / Mid / Large / Enterprise |
| annual_revenue_band_inr | text | No | Banded (not exact) revenue range, e.g. "₹1–5 Cr" — synthetic even for real-named rows |
| gstin | text | No | Synthetic, format-valid 15-character GSTIN (not a real registration) |
| city | text | No | HQ city |
| state | text | No | HQ state |
| region | text | No | North / South / East / West |
| pincode | text | No | 6-digit synthetic pincode |
| website_domain | text | Yes | Synthetic `.example` domain; may be blank |
| company_type | text | No | Private Limited / Public Limited / LLP / Partnership / Proprietorship / PSU |
| founded_year | integer | No | Synthetic founding year |
| account_owner_rep_id | FK → sales_reps.rep_id | Yes | Assigned account owner |
| account_status | text | No | Prospect / Active Customer (backfilled to Active Customer once the company produces a `customers` row) |
| created_at | timestamp | No | Record creation timestamp |

---

## Transactional tables

### contacts
| Column | Type | Nullable | Description |
|---|---|---|---|
| contact_id | PK, `CONT-######` | No | Contact code |
| company_id | FK → companies.company_id | No | Employer company |
| full_name | text | No | Synthetic name |
| job_title | text | No | Job title, derived from department + seniority |
| seniority_level | text | No | Junior / Mid / Senior / Manager / Director / VP / C-Level |
| department | text | No | Functional department, or "Founder/Owner" for small-company contacts |
| email | text | No | Synthetic email at a domain derived from the employer's `website_domain` |
| phone | text | Yes | Synthetic phone, ~14% blank (not captured) |
| is_primary_contact | boolean | No | True for exactly one contact per company (the first generated) |
| linkedin_handle | text | Yes | Synthetic LinkedIn slug; ~45% blank |
| is_decision_maker | boolean | No | True for senior/founder contacts and a probabilistic subset of Managers |
| created_at | timestamp | No | Record creation timestamp |

### leads
| Column | Type | Nullable | Description |
|---|---|---|---|
| lead_id | PK, `LEAD-######` | No | Lead code |
| company_id | FK → companies.company_id | No | Company the lead belongs to |
| contact_id | FK → contacts.contact_id | No | Associated contact (must belong to the same company) |
| lead_source_id | FK → lead_sources.lead_source_id | No | How the lead originated |
| campaign_id | FK → campaigns.campaign_id | Yes | Originating campaign, if any |
| assigned_rep_id | FK → sales_reps.rep_id | Yes | Blank for ~35% of stalled "New" leads (unassigned backlog) |
| lead_status | text | No | New / Contacted / Qualifying / Qualified (MQL) / Sales Qualified (SQL) / Converted / Disqualified / Dead / Nurture |
| disqualification_reason | text | Yes | Populated only when `lead_status = Disqualified` |
| industry_interest_id | FK → industries.industry_id | No | Product-interest industry tag (usually equals the company's own industry) |
| estimated_budget_inr | decimal | Yes | Self-reported/estimated budget; not always captured |
| company_size_at_lead_time | text | No | Snapshot of the company's size band when the lead was created (may differ from the company's current band) |
| created_at | timestamp | No | Lead creation |
| first_contacted_at | timestamp | Yes | First outreach; blank if never contacted |
| qualified_at | timestamp | Yes | Reached Qualified (MQL); blank if not yet reached |
| converted_at | timestamp | Yes | Reached Converted; blank unless `lead_status = Converted` |
| is_duplicate_of_lead_id | FK → leads.lead_id (self) | Yes | Populated for leads flagged as duplicates of an earlier lead |

### lead_status_history
Append-only audit trail; one row per status transition. Never updated in place.

| Column | Type | Nullable | Description |
|---|---|---|---|
| history_id | PK, `LSH-#######` | No | History row code |
| lead_id | FK → leads.lead_id | No | Lead this transition belongs to |
| status_from | text | Yes | Prior status; blank for a lead's first ("New") row |
| status_to | text | No | New status |
| changed_at | timestamp | No | When the transition occurred |
| changed_by_rep_id | FK → sales_reps.rep_id | Yes | Rep who made the change; blank for system-generated first rows |

### campaign_responses
| Column | Type | Nullable | Description |
|---|---|---|---|
| response_id | PK, `CRSP-########` | No | Response code |
| campaign_id | FK → campaigns.campaign_id | No | Campaign responded to |
| contact_id | FK → contacts.contact_id | No | Responding contact |
| response_type | text | No | Opened / Clicked / Registered / Attended / Downloaded, etc. |
| response_date | date | No | Response date |
| resulted_in_lead_id | FK → leads.lead_id | Yes | Populated if this response directly produced a lead |

### opportunities
| Column | Type | Nullable | Description |
|---|---|---|---|
| opportunity_id | PK, `OPP-######` | No | Opportunity code |
| company_id | FK → companies.company_id | No | Account |
| primary_contact_id | FK → contacts.contact_id | No | Deal's primary contact (same company as `company_id`) |
| source_lead_id | FK → leads.lead_id | No | The Sales-Qualified lead this opportunity was created from |
| owner_rep_id | FK → sales_reps.rep_id | No | Owning rep |
| opportunity_name | text | No | Auto-generated deal name |
| pipeline_stage | text | No | Qualification / Discovery / Solution Fit / Proposal / Negotiation / Closed Won / Closed Lost |
| forecast_category | text | No | Pipeline / Best Case / Commit / Closed Won / Closed Lost |
| deal_value_inr | decimal | No | Sum of `opportunity_products.line_total_inr` for this opportunity |
| probability_pct | integer | No | 0–100; tied to `pipeline_stage` (100 for Closed Won, 0 for Closed Lost, banded otherwise) |
| expected_close_date | date | No | Forecasted close date |
| actual_close_date | date | Yes | Populated only once Closed Won/Lost |
| close_outcome | text | Yes | "Won" / "Lost"; blank while open |
| loss_reason | text | Yes | Populated only when `close_outcome = Lost` |
| competitor_name | text | Yes | Populated only for a subset of competitive losses |
| opportunity_type | text | No | Currently always "New Business" in this batch |
| created_at | timestamp | No | Opportunity creation |

### opportunity_products
Line items of an opportunity (many-to-many companies↔products, realized as one row per product per opportunity).

| Column | Type | Nullable | Description |
|---|---|---|---|
| opportunity_product_id | PK, `OPPR-#######` | No | Line-item code |
| opportunity_id | FK → opportunities.opportunity_id | No | Parent opportunity |
| product_id | FK → products.product_id | No | Product sold |
| quantity | integer | No | Quantity (>1 typically only for usage-based products) |
| unit_price_inr | decimal | No | Unit price at time of quote (snapshot of `products.list_price_inr`) |
| discount_pct | decimal | No | 0 / 5 / 10 / 15 / 20 |
| line_total_inr | decimal | No | `quantity × unit_price_inr × (1 − discount_pct/100)` |

### customers
Created **only** from a Closed-Won opportunity.

| Column | Type | Nullable | Description |
|---|---|---|---|
| customer_id | PK, `CUST-######` | No | Customer code |
| company_id | FK → companies.company_id | No | The company that became a customer (must match `originating_opportunity_id`'s company) |
| originating_opportunity_id | FK → opportunities.opportunity_id | No | The Closed-Won opportunity that created this customer |
| customer_since | date | No | Onboarding date (shortly after the opportunity's close date) |
| csm_rep_id | FK → sales_reps.rep_id | No | Assigned Customer Success Manager |
| customer_tier | text | No | Bronze / Silver / Gold / Platinum, by deal-value band (only Bronze/Silver observed in this batch — see README limitations) |
| contract_type | text | No | Monthly / Annual / Multi-Year |
| renewal_date | date | No | Next renewal checkpoint, per `contract_type` cadence |
| customer_status | text | No | Active / At Risk / Paused (no explicit "Churned" value — see README) |

### customer_transactions
| Column | Type | Nullable | Description |
|---|---|---|---|
| transaction_id | PK, `TXN-#######` | No | Transaction code |
| customer_id | FK → customers.customer_id | No | Customer |
| opportunity_id | FK → opportunities.opportunity_id | Yes | Populated only for the initial-sale transaction |
| transaction_date | date | No | Transaction date |
| transaction_type | text | No | New Sale / Renewal / Upsell / Downgrade / Refund |
| amount_inr | decimal | No | Transaction amount. **Negative iff `transaction_type = "Refund"`** (a refund/reversal of a prior sale) — every other `transaction_type` is always non-negative. This dataset ships 2 `Refund` rows (both negative); see `business_rules.md` rule 4.8 and `data_quality_report.md` §1.8 |
| payment_status | text | No | Paid / Pending / Overdue / Partially Paid |
| invoice_number | text | No | Synthetic invoice reference |

### customer_support_cases
| Column | Type | Nullable | Description |
|---|---|---|---|
| case_id | PK, `CASE-#######` | No | Case code |
| customer_id | FK → customers.customer_id | No | Customer |
| contact_id | FK → contacts.contact_id | No | Reporting contact (same company as the customer) |
| case_type | text | No | Technical Issue / Billing Query / Feature Request / Onboarding Help / Complaint / General Query |
| priority | text | No | Low / Medium / High / Critical |
| status | text | No | Open / In Progress / Escalated / Resolved / Closed |
| opened_at | timestamp | No | Case opened |
| resolved_at | timestamp | Yes | Blank while unresolved |
| satisfaction_score | integer | Yes | 1–5; populated only for resolved/closed cases with a survey response |

### activities
| Column | Type | Nullable | Description |
|---|---|---|---|
| activity_id | PK, `ACT-#######` | No | Activity code |
| activity_type | text | No | Call / Email / Meeting / Demo / Follow-up / Task / Site Visit / Proposal Discussion / Negotiation / Support Follow-up |
| subject | text | No | Short one-line summary of the activity |
| description | text | No | Longer free-text description of what the activity covered |
| activity_date | timestamp | No | When the activity occurred / was logged; never after `created_at` or `updated_at`, never after the generation cutoff |
| due_date | date | No | Deadline associated with the activity; always on/after `activity_date`'s calendar date. May legitimately be ahead of the generation cutoff for an open (Planned/Pending/In Progress/Rescheduled) activity |
| status | text | No | Completed / Planned / Pending / In Progress / Rescheduled / Cancelled |
| priority | text | No | Low / Medium / High / Urgent |
| lead_id | FK → leads.lead_id | Yes | Populated only when the activity is tied to a lead |
| contact_id | FK → contacts.contact_id | Yes | Populated only when the activity involved a specific contact |
| company_id | FK → companies.company_id | Yes | Populated when the activity is tied to a company (lead, opportunity, or customer context) |
| opportunity_id | FK → opportunities.opportunity_id | Yes | Populated only when the activity is tied to an opportunity |
| customer_id | FK → customers.customer_id | Yes | Populated only when the activity is tied to a post-sale customer |
| sales_rep_id | FK → sales_reps.rep_id | No | Rep who performed/owns the activity |
| outcome | text | Conditional | Required (non-blank) if and only if `status = "Completed"` |
| next_follow_up_date | date | Yes | When present, always strictly after `activity_date`'s calendar date |
| created_at | timestamp | No | When the activity record was created; always on/after `activity_date` |
| updated_at | timestamp | No | When the activity record was last updated; always on/after `created_at` |

At least one of `lead_id` / `contact_id` / `company_id` / `opportunity_id` / `customer_id` is populated for the large majority of rows (each activity is generated from a lead, opportunity, or customer context); a small share are general internal tasks with none of these set, which is valid by design (see `business_rules.md` rule 3.7).

---

## Historical / audit-trail tables

See `lead_status_history` and `opportunity_stage_history` above (`opportunity_stage_history` mirrors `lead_status_history`'s structure with `stage_from`/`stage_to`/`days_in_previous_stage` in place of `status_from`/`status_to`).

### opportunity_stage_history
| Column | Type | Nullable | Description |
|---|---|---|---|
| history_id | PK, `OSH-#######` | No | History row code |
| opportunity_id | FK → opportunities.opportunity_id | No | Opportunity this transition belongs to |
| stage_from | text | Yes | Prior stage; blank for the opportunity's first row |
| stage_to | text | No | New stage |
| changed_at | timestamp | No | When the transition occurred |
| days_in_previous_stage | integer | Yes | Days spent in the prior stage; blank on the first row |

---

## ML-ready datasets

All five share `ml_record_id` (PK) and `dataset_split` (`train` / `validation` / `test`, assigned by **chronological** order on the dataset's own time column — never randomly). Full business meaning, generation logic, and leakage controls: `ml_dataset_documentation.md` and `ml_leakage_prevention.md`.

### lead_conversion_dataset (grain: one row per lead)
| Column | Description |
|---|---|
| ml_record_id | PK |
| lead_id | FK → leads.lead_id |
| company_id | FK → companies.company_id |
| observation_cutoff_at | The timestamp features are computed "as of" (qualified_at → first_contacted_at → created_at fallback chain) |
| industry_id, region, company_size_at_lead_time | Firmographic features, snapshotted at/ before cutoff |
| lead_source_category, campaign_sourced_flag | Acquisition-channel features |
| contact_seniority_level, contact_is_decision_maker | Contact-quality features |
| estimated_budget_known, estimated_budget_band | Budget features (banded, not exact, to limit granularity-based leakage) |
| days_since_created_to_cutoff | Elapsed lead age at cutoff |
| num_status_transitions_before_cutoff | Count of `lead_status_history` rows strictly before cutoff |
| rep_assigned_flag | Whether a rep was assigned as of cutoff |
| rep_trailing_conversion_rate | Assigned rep's conversion rate computed only from leads that resolved strictly before this lead's cutoff (leakage-safe rolling feature) |
| is_duplicate_lead | From `leads.is_duplicate_of_lead_id` |
| label_converted | True/False — did the lead reach `Converted` (ever, not just by cutoff) |
| dataset_split | train/validation/test, chronological on `observation_cutoff_at` |

### lead_scoring_dataset (grain: one row per lead, strict day-0)
Same population as above, but `observation_cutoff_at` is forced to equal `leads.created_at` exactly — a pure "score this lead the instant it lands" view. Deliberately excludes budget, engagement, and trailing-rate features (nothing exists yet at day 0). Columns: `ml_record_id, lead_id, company_id, observation_cutoff_at, industry_id, region, company_size_at_lead_time, lead_source_category, campaign_sourced_flag, contact_seniority_level, contact_is_decision_maker, contact_department, label_converted, dataset_split`.

### sales_forecasting_dataset (grain: one row per department × month)
| Column | Description |
|---|---|
| department_id, department_name | Revenue-owning department |
| period_label, period_start | The forecast month |
| pipeline_value_open_at_period_start_inr | Sum of open-opportunity deal value, as of `period_start` |
| num_open_opportunities_at_period_start | Count, as of `period_start` |
| historical_win_rate_trailing_3mo | Win rate over the 3 months before `period_start` |
| revenue_trailing_3mo_inr | Realized Closed-Won revenue over the 3 months before `period_start` |
| avg_deal_cycle_days_trailing_6mo | Average created→closed cycle length, trailing 6 months |
| active_rep_count | Active reps in the department as of `period_start` |
| seasonality_month | Calendar month number, 1–12 |
| label_actual_amount_inr | Realized Closed-Won revenue **within** the period (the forecast target) |
| dataset_split | train/validation/test, chronological on `period_start` |

### customer_segmentation_dataset (grain: one row per customer per quarter-end snapshot)
| Column | Description |
|---|---|
| customer_id, company_id | Customer |
| snapshot_date | Quarter-end snapshot date |
| recency_days_since_last_transaction | RFM: recency |
| frequency_transactions_last_12mo | RFM: frequency |
| monetary_total_last_12mo_inr | RFM: monetary |
| tenure_months_at_snapshot | Months since `customer_since` |
| support_case_count_last_12mo, avg_satisfaction_score | Support-engagement features |
| product_category_diversity | Distinct product categories purchased |
| industry_id, company_size_band, customer_tier, contract_type | Firmographic/contract features |

**No cluster-label column.** This table intentionally does **not** ship a `segment_label_cluster_id` (or similarly named) column. An earlier revision included one that was always 100% blank — a misleading placeholder that looked like a failed-to-populate label rather than what it actually was (a slot reserved for a downstream clustering model's *output*). Since this is an unsupervised segmentation/RFM feature table with no ground-truth cluster assignment to ship, the column has been removed entirely rather than left blank; run your own clustering model (k-means, hierarchical, etc.) against these features to produce cluster assignments. See `ml_leakage_prevention.md` rule 9.4 and `data_quality_report.md` §1.9.

### churn_prediction_dataset (grain: one row per customer per renewal-cycle checkpoint)
| Column | Description |
|---|---|
| customer_id, company_id | Customer |
| observation_snapshot_date | 30 days before the renewal due date being evaluated |
| renewal_due_date | The renewal checkpoint this row evaluates |
| tenure_months_at_snapshot | Months since `customer_since` |
| days_since_last_transaction_at_snapshot | Recency at snapshot |
| support_case_count_trailing_90d, avg_case_priority_trailing_90d | Support-engagement features, trailing 90 days |
| contract_type, customer_tier | Firmographic features |
| transaction_amount_trailing_90d_inr, transaction_amount_trend_90d_inr | Recent revenue trend features |
| label_churned_within_horizon | True if no Renewal-type transaction appears in `[due−15, due+45]` days |
| horizon_days | The label window length used |
| dataset_split | train/validation/test, chronological on `observation_snapshot_date` |

Deliberately **excluded** as a feature: `customer_status` (would leak the outcome — see `ml_leakage_prevention.md`).
