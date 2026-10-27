# Final CRM Data Dictionary (Phase D1)

This document describes the final state of the Indian B2B CRM database following the D1 migration.

## Reference Entities (Read-Only)

These tables contain static reference data used for categorization and lookups.

*   **`industries`**: Standardized industry verticals (e.g., "Technology", "Manufacturing").
*   **`territories`**: Geographic sales regions in India (e.g., "North India", "South India").
*   **`departments`**: Internal organization departments (e.g., "Sales", "Support").
*   **`lead_sources`**: Origins of leads (e.g., "Website", "Referral", "Cold Call").

## Core CRM Entities (CRUD)

These tables represent the operational data of the CRM and support full CRUD functionality (with soft-deletes via `deleted_at`).

*   **`companies`**: B2B client organizations. The central entity of the CRM.
*   **`contacts`**: Individual people working at `companies`.
*   **`leads`**: Prospective business opportunities that have not yet converted.
*   **`opportunities`**: Qualified sales deals in progress.
*   **`products`**: Services and software products offered by the CRM owner. (Migrated to CRUD in D1).
*   **`customers`**: Companies that have successfully purchased products (converted from leads/opportunities).
*   **`transactions`**: Financial records of purchases made by `customers`.
*   **`activities`**: Log of interactions (calls, emails, meetings) with contacts/leads.
*   **`campaigns`**: Marketing initiatives.
*   **`support_cases`**: Post-sale issues and support tickets raised by `customers`.

## Internal / System Entities

*   **`users`**: System users (Sales reps, managers, admins) authenticated to use the CRM.
*   **`sales_reps`**: Detailed profiles for sales representatives, mapping to territories and departments.

## History & Linking Tables

*   **`lead_status_history`**: Audit trail of status changes for leads.
*   **`opportunity_stage_history`**: Audit trail of stage progression for opportunities.
*   **`opportunity_products`**: Junction table linking `opportunities` to the specific `products` being pitched.
*   **`campaign_responses`**: Junction table linking `campaigns` to `leads` that responded.

## AI & RAG Entities (Pre-existing)

These tables support the AI assistant and RAG capabilities. They were preserved as-is during D1.

*   **`chat_sessions`**: Logical sessions for the AI chat.
*   **`chat_messages`**: Individual messages within a chat session.
*   **`company_documents`**: Uploaded context documents (PDFs, etc.) linked to a company for RAG.

## Schema Conventions

*   **Primary Keys**: String UUIDs or prefixed IDs (e.g., `COM-1234`).
*   **Soft Deletion**: Implemented via a `deleted_at` (FLOAT/timestamp) column. Non-null indicates the record is archived.
*   **Audit Fields**: Most core entities include `created_at`, `updated_at`, `created_by`, and `updated_by`.
