# Recommended Database Schema (for a production CRM app built on this dataset)

The delivered `sql/create_tables_*.sql` scripts implement the dataset's schema exactly as generated. This document recommends what to add on top if you're building an actual CRM application against it — none of this is present in the delivered CSVs/SQL, it's forward guidance.

## 1. Keep the dataset schema as your "core CRM" tables, largely as-is

The 19 source tables map cleanly onto what a real CRM's core schema looks like (companies/accounts, contacts, leads, opportunities/deals, products, customers, transactions, support cases). Resist the urge to redesign them before you have real usage data telling you they're wrong — the schema already went through a design-review pass (v1 → v2, documented in `generation_methodology.md`) that removed a circular FK and a polymorphic-FK anti-pattern.

## 2. Additions a real application will need immediately

- **`users` / `auth`**: `sales_reps` models the org chart but has no login credentials, password hash, session, or role/permission model. Add a `users` table (1:1 or 1:N with `sales_reps`, since not every rep needs app access, and you may have admin users who aren't reps) plus a `roles`/`permissions` table.
- **Audit columns**: add `created_by`, `updated_by`, `updated_at` to every mutable table (the dataset only has `created_at`) so the app can show "last edited by" and support undo/audit views.
- **Soft deletes**: add a `deleted_at` (nullable) to `contacts`, `leads`, `opportunities`, `companies` rather than hard-deleting — CRM users expect to recover an accidentally-deleted record.
- **Notes / activity feed**: a generic `notes` or `activities` table (polymorphic-safe version: separate nullable FKs `lead_id`, `opportunity_id`, `contact_id`, `customer_id` — following the same pattern the dataset already uses for `opportunity_products`/`customer_transactions` rather than a single polymorphic `entity_type`/`entity_id` pair, which this dataset's own design review explicitly rejected for `activities` in v1).
- **Tasks / reminders**: `tasks(task_id, owner_rep_id, related_lead_id NULL, related_opportunity_id NULL, due_at, status, title)` — every real CRM needs "follow up with X by Y."
- **Attachments/documents**: `documents(document_id, related_entity FKs, file_url, uploaded_by, uploaded_at)`, backed by object storage (S3-compatible), not a `bytea`/`blob` column.
- **Email/calendar integration tables**: if you sync with a real mailbox/calendar, you'll want `email_threads`, `email_messages`, `calendar_events` linked to contacts/leads/opportunities.
- **API keys / webhooks / integration config**: if other systems will push/pull data.

## 3. Indexing recommendations beyond the PK/FK indexes in the delivered SQL

- `leads(assigned_rep_id, lead_status)` — composite, for "my open leads" queries.
- `opportunities(owner_rep_id, pipeline_stage)` — composite, for pipeline/forecast views.
- `opportunities(expected_close_date)` and `(actual_close_date)` — for forecast and reporting date-range queries.
- `customer_transactions(customer_id, transaction_date)` — composite, for account-history and RFM-style queries.
- `lead_status_history(lead_id, changed_at)` and `opportunity_stage_history(opportunity_id, changed_at)` — already effectively required for correct ordering; index explicitly for timeline views.
- Full-text search index (Postgres `tsvector` / MySQL `FULLTEXT`) on `companies.company_name` and `contacts.full_name` once you have autocomplete/search UI.

## 4. Partitioning / scale considerations

At production scale, `lead_status_history` and `opportunity_stage_history` are the fastest-growing tables (every stage change adds a row, forever) — consider partitioning by `changed_at` (monthly/quarterly) if you expect years of history, and an archival policy for closed opportunities' history older than N years.

## 5. Multi-tenancy

This dataset models a single CRM vendor's own book of business. If your application will serve multiple tenants (e.g. a multi-org SaaS CRM product), every table needs a `tenant_id`/`org_id` column and every query needs tenant-scoping — that's a schema-wide change, not an incremental one, so decide this before loading real customer data even if you defer implementing it.

## 6. What NOT to add without a real need

Avoid adding "just in case" columns (e.g. 10 unused custom fields, a generic `metadata JSONB` on every table used for nothing specific) — this dataset's clean, validated shape is a feature; a real app's schema tends to accrete cruft fast enough on its own.
