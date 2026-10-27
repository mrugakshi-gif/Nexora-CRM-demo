# Referential-Integrity Report

Generated from the final validation run (`scripts/validation/validate_dataset.py`) against the CSVs shipped in this package. Source: `data/full_audit_report.json`, section `6_7_invalid_fk_and_orphans`.

## Result: 0 orphaned foreign keys across every declared relationship

All 34 declared foreign-key relationships plus 4 semantic cross-checks were tested. Every non-blank foreign-key value resolves to an existing primary key in its parent table; every cross-entity consistency rule holds.

| # | Relationship | Orphans found |
|---|---|---|
| 1 | companies.industry_id → industries.industry_id | 0 |
| 2 | companies.account_owner_rep_id → sales_reps.rep_id | 0 |
| 3 | contacts.company_id → companies.company_id | 0 |
| 4 | sales_reps.department_id → departments.department_id | 0 |
| 5 | sales_reps.manager_rep_id → sales_reps.rep_id (self) | 0 |
| 6 | sales_reps.territory_id → territories.territory_id | 0 |
| 7 | campaigns.target_industry_id → industries.industry_id | 0 |
| 8 | campaigns.owner_department_id → departments.department_id | 0 |
| 9 | leads.company_id → companies.company_id | 0 |
| 10 | leads.contact_id → contacts.contact_id | 0 |
| 11 | leads.lead_source_id → lead_sources.lead_source_id | 0 |
| 12 | leads.assigned_rep_id → sales_reps.rep_id | 0 |
| 13 | leads.campaign_id → campaigns.campaign_id | 0 |
| 14 | leads.industry_interest_id → industries.industry_id | 0 |
| 15 | leads.is_duplicate_of_lead_id → leads.lead_id (self) | 0 |
| 16 | lead_status_history.lead_id → leads.lead_id | 0 |
| 17 | lead_status_history.changed_by_rep_id → sales_reps.rep_id | 0 |
| 18 | campaign_responses.campaign_id → campaigns.campaign_id | 0 |
| 19 | campaign_responses.contact_id → contacts.contact_id | 0 |
| 20 | campaign_responses.resulted_in_lead_id → leads.lead_id | 0 |
| 21 | opportunities.company_id → companies.company_id | 0 |
| 22 | opportunities.owner_rep_id → sales_reps.rep_id | 0 |
| 23 | opportunities.source_lead_id → leads.lead_id | 0 |
| 24 | opportunities.primary_contact_id → contacts.contact_id | 0 |
| 25 | opportunity_products.opportunity_id → opportunities.opportunity_id | 0 |
| 26 | opportunity_products.product_id → products.product_id | 0 |
| 27 | opportunity_stage_history.opportunity_id → opportunities.opportunity_id | 0 |
| 28 | customers.company_id → companies.company_id | 0 |
| 29 | customers.originating_opportunity_id → opportunities.opportunity_id | 0 |
| 30 | customers.csm_rep_id → sales_reps.rep_id | 0 |
| 31 | customer_transactions.customer_id → customers.customer_id | 0 |
| 32 | customer_transactions.opportunity_id → opportunities.opportunity_id | 0 |
| 33 | customer_support_cases.customer_id → customers.customer_id | 0 |
| 34 | customer_support_cases.contact_id → contacts.contact_id | 0 |

## Semantic cross-entity checks (beyond simple FK resolution)

| Check | Violations found |
|---|---|
| A lead's `contact_id` belongs to the same `company_id` as the lead | 0 |
| An opportunity's `primary_contact_id` belongs to the same company as the opportunity | 0 |
| A customer's `company_id` matches its `originating_opportunity_id`'s company | 0 |
| A support case's `contact_id` belongs to the same company as the case's customer | 0 |

## ML-dataset traceability (foreign keys back into the source tables)

| Dataset | Traceability check | Result |
|---|---|---|
| lead_conversion_dataset | every `lead_id` / `company_id` resolves | 0 orphans |
| lead_scoring_dataset | every `lead_id` resolves | 0 orphans |
| customer_segmentation_dataset | every `customer_id` resolves | 0 orphans |
| churn_prediction_dataset | every `customer_id` resolves | 0 orphans |
| sales_forecasting_dataset | every `department_id` resolves | 0 orphans |

## Uniqueness checks (primary keys and business-key duplicates)

| Check | Violations found |
|---|---|
| Duplicate primary key, any of the 24 tables | 0 |
| Duplicate `(company_name, city)` in companies | 0 |
| Duplicate `website_domain` in companies (non-blank) | 0 |
| Duplicate `gstin` in companies (non-blank) | 0 |
| Duplicate `email` in contacts (non-blank) | 0 |
| Duplicate `email` in sales_reps (non-blank) | 0 |
| Duplicate `product_name` in products | 0 |
| A company producing more than one `customers` row | 0 |

**Conclusion:** the dataset's relational graph is fully consistent. Every child row has a valid parent, every self-referencing FK (manager hierarchy, duplicate-lead flag) resolves within its own table, and no table contains a duplicate primary key or an unintended duplicate business entity.
