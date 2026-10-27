# Recommended API Endpoints

A REST-ish endpoint surface for a CRM application built on this schema. Adjust to GraphQL/gRPC as needed — the resource model below carries over either way. Auth/tenant-scoping omitted for brevity; assume every endpoint requires an authenticated `sales_reps`-linked user and (if multi-tenant) is scoped to `tenant_id`.

## Companies / Accounts
```
GET    /companies                       list, filter by industry/size/status/region, paginate
GET    /companies/{id}
POST   /companies
PATCH  /companies/{id}
GET    /companies/{id}/contacts
GET    /companies/{id}/leads
GET    /companies/{id}/opportunities
GET    /companies/{id}/customer                 (0 or 1)
GET    /companies/{id}/timeline                 (merged activity feed: leads, opps, cases)
```

## Contacts
```
GET    /contacts                        filter by company/seniority/decision_maker
GET    /contacts/{id}
POST   /contacts
PATCH  /contacts/{id}
```

## Leads
```
GET    /leads                           filter by status/source/rep/campaign/date range
GET    /leads/{id}
POST   /leads
PATCH  /leads/{id}
POST   /leads/{id}/transition            body: {to_status, reason?}  -> validates against the
                                          allowed state machine (business_rules.md §2.1),
                                          writes a lead_status_history row, never a raw UPDATE
                                          of lead_status
GET    /leads/{id}/history
POST   /leads/{id}/convert-to-opportunity  -> only allowed if lead_status = "Sales Qualified (SQL)"
GET    /leads/duplicates/{id}            candidate duplicates for review
```

## Opportunities / Deals
```
GET    /opportunities                    filter by stage/rep/company/close-date range
GET    /opportunities/{id}
POST   /opportunities
PATCH  /opportunities/{id}
POST   /opportunities/{id}/transition     body: {to_stage, outcome?, loss_reason?, competitor?}
                                          -> validates the state machine, writes
                                          opportunity_stage_history, recomputes probability_pct
GET    /opportunities/{id}/history
GET    /opportunities/{id}/products
POST   /opportunities/{id}/products       add a line item; server recomputes deal_value_inr
DELETE /opportunities/{id}/products/{line_id}
POST   /opportunities/{id}/close-won      -> triggers customer creation (or links to an
                                          existing company's customer) per business_rules.md §1.2
```

## Products
```
GET    /products
GET    /products/{id}
POST   /products                         admin only
PATCH  /products/{id}
```

## Campaigns
```
GET    /campaigns
GET    /campaigns/{id}
GET    /campaigns/{id}/responses
GET    /campaigns/{id}/roi                aggregated: spend vs. attributed opportunity/customer revenue
```

## Customers
```
GET    /customers                        filter by tier/status/contract_type/csm
GET    /customers/{id}
GET    /customers/{id}/transactions
GET    /customers/{id}/support-cases
GET    /customers/{id}/health-score        computed, not stored — see dashboard KPIs doc
```

## Support Cases
```
GET    /support-cases                    filter by status/priority/customer
GET    /support-cases/{id}
POST   /support-cases
PATCH  /support-cases/{id}
POST   /support-cases/{id}/resolve
```

## Sales Reps / Org
```
GET    /sales-reps
GET    /sales-reps/{id}
GET    /sales-reps/{id}/pipeline          their open opportunities
GET    /sales-reps/{id}/leads
GET    /departments
GET    /territories
```

## Analytics / Reporting (backing the dashboards — see recommended_dashboard_kpis.md)
```
GET    /analytics/pipeline-summary        by stage, by rep, by department
GET    /analytics/forecast                 department × month, mirrors sales_forecasting_dataset's grain
GET    /analytics/lead-funnel              conversion rate by stage, by source
GET    /analytics/revenue                  by period, by product, by customer tier
GET    /analytics/churn-risk               customers flagged by the churn model, with score
```

## ML-serving endpoints (if models trained on the ML datasets are deployed)
```
POST   /ml/lead-score                     body: {lead_id} or raw feature payload -> {score}
POST   /ml/conversion-probability         body: {lead_id} -> {probability}
GET    /ml/forecast/{department_id}/{month}
POST   /ml/churn-risk                     body: {customer_id} -> {risk_score, contributing_factors}
```
Keep these behind their own versioned prefix (e.g. `/ml/v1/...`) since model-serving contracts evolve independently of the CRM data API, and log every prediction with its input feature snapshot for later drift analysis — see `docs/ml_project_structure.md`.

## Cross-cutting conventions

- **Never allow a raw `PATCH` to `lead_status` or `pipeline_stage`.** Always go through the `/transition` endpoints so `lead_status_history`/`opportunity_stage_history` stay authoritative and the business rules in `business_rules.md` §2 stay enforced server-side, not just at generation time.
- **Idempotency keys** on all POST endpoints that create financial records (`customer_transactions`, `opportunity_products`) to avoid duplicate-on-retry bugs.
- **Pagination** (cursor-based, not offset) on every list endpoint — this dataset is small, but a real CRM's `lead_status_history`/`opportunity_stage_history` tables grow without bound.
