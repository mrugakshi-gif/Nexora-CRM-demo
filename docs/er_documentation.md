# Entity-Relationship Documentation

## Design principles

- **companies is the hub.** Every other transactional table traces back to a `company_id`, directly or via one hop (contact → company, lead → company, opportunity → company, customer → company).
- **Funnel progression is one-directional and gated**, enforced by generation logic and re-checked by validation: a lead must reach *Sales Qualified (SQL)* before it can produce an opportunity; an opportunity must reach *Closed Won* before it can produce a customer; a customer must exist before it can have transactions or support cases.
- **No circular foreign keys.** `leads` does not carry a "converted_to_opportunity_id" — the relationship is recoverable in the other direction via `opportunities.source_lead_id`. This was a deliberate fix made during the v1→v2 schema review (see `generation_methodology.md`).
- **History tables are append-only.** `lead_status_history` and `opportunity_stage_history` are never updated or deleted from; every transition is a new row. The live `lead_status` / `pipeline_stage` columns on the parent table are denormalized copies of "the latest row in the corresponding history table," kept in sync by the generator.
- **ML tables are derived, read-only outputs.** They hold foreign keys back into the source tables (`lead_id`, `customer_id`, `department_id`, etc.) for full traceability but store no independent truth — they must never be treated as a second source of record.

## Relationships (parent → child, cardinality)

| Parent | Child | Cardinality | Notes |
|---|---|---|---|
| industries | companies | 1 : N | every company has exactly one industry |
| industries | campaigns | 1 : N (optional) | `target_industry_id` may be blank |
| industries | leads | 1 : N | `industry_interest_id` |
| territories | sales_reps | 1 : N (optional) | |
| territories | territories→industries | N : 1 (optional) | `primary_industry_focus` |
| departments | sales_reps | 1 : N | |
| departments | campaigns | 1 : N | `owner_department_id` |
| sales_reps | sales_reps | 1 : N (self) | manager hierarchy via `manager_rep_id` |
| sales_reps | companies | 1 : N (optional) | `account_owner_rep_id` |
| sales_reps | leads | 1 : N (optional) | `assigned_rep_id` |
| sales_reps | opportunities | 1 : N | `owner_rep_id` |
| sales_reps | customers | 1 : N | `csm_rep_id` |
| sales_reps | lead_status_history | 1 : N (optional) | `changed_by_rep_id` |
| lead_sources | leads | 1 : N | |
| products | opportunity_products | 1 : N | |
| campaigns | leads | 1 : N (optional) | |
| campaigns | campaign_responses | 1 : N | |
| companies | contacts | 1 : N | |
| companies | leads | 1 : N | |
| companies | opportunities | 1 : N | |
| companies | customers | 1 : 0..1 | a company becomes at most one customer record in this schema |
| contacts | leads | 1 : N | a contact can be tied to multiple leads over time |
| contacts | opportunities | 1 : N | `primary_contact_id` |
| contacts | campaign_responses | 1 : N | |
| contacts | customer_support_cases | 1 : N | |
| leads | lead_status_history | 1 : N | full transition history |
| leads | opportunities | 1 : 0..1 | `source_lead_id`; only Sales-Qualified leads that convert produce one |
| leads | leads | 1 : N (self, optional) | `is_duplicate_of_lead_id` |
| leads | campaign_responses | 1 : N (optional) | `resulted_in_lead_id` |
| opportunities | opportunity_products | 1 : N | line items |
| opportunities | opportunity_stage_history | 1 : N | full transition history |
| opportunities | customers | 1 : 0..1 | `originating_opportunity_id`; only if Closed Won |
| opportunities | customer_transactions | 1 : 0..1 (optional) | only the initial-sale transaction links back to an opportunity |
| customers | customer_transactions | 1 : N | |
| customers | customer_support_cases | 1 : N | |
| leads | activities | 1 : N (optional) | populated only for lead-context activities |
| contacts | activities | 1 : N (optional) | |
| companies | activities | 1 : N (optional) | |
| opportunities | activities | 1 : N (optional) | populated only for opportunity-context activities |
| customers | activities | 1 : N (optional) | populated only for customer-context activities |
| sales_reps | activities | 1 : N | every activity has an owning/performing rep |

## Many-to-many relationships

- **companies ↔ products**, realized through `opportunities` → `opportunity_products` (an opportunity is the join context: which products, at what price/discount, for which deal).
- **contacts ↔ campaigns**, realized through `campaign_responses`.

## Generation / load order (topological)

1. industries, territories, departments, lead_sources, products
2. sales_reps (depends on departments, territories)
3. campaigns (depends on industries, departments)
4. companies (depends on industries; optionally sales_reps for `account_owner_rep_id`)
5. contacts (depends on companies)
6. leads (depends on companies, contacts, lead_sources, campaigns, sales_reps, industries)
7. lead_status_history (depends on leads, sales_reps)
8. campaign_responses (depends on campaigns, contacts, leads)
9. opportunities (depends on leads, companies, contacts, sales_reps)
10. opportunity_products (depends on opportunities, products)
11. opportunity_stage_history (depends on opportunities, sales_reps)
12. customers (depends on opportunities, companies, sales_reps)
13. customer_transactions (depends on customers, opportunities)
14. customer_support_cases (depends on customers, contacts)
15. activities (depends on leads, contacts, companies, opportunities, customers, sales_reps -- generated last among the source tables, read-only against all of them)
16. the 5 ML-ready datasets (depend on all of the above)

This is also the order used by `sql/create_tables_*.sql` and `scripts/load_*.py` — loading out of order will fail on foreign-key constraints.
