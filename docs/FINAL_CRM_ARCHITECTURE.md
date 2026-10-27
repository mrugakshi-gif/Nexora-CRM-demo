# Final CRM Architecture (Phase D1)

This document describes the architectural layout of the Indian B2B CRM application following the D1 backend modularization.

## Overview

The backend is built as a modular FastAPI application using SQLAlchemy for ORM, connecting to a SQLite database (`crm.db`). The architecture follows a strict separation of concerns, routing, and schema validation.

## Directory Structure (Backend)

```
backend/
├── main.py                 # Application entry point, CORS config, and router aggregation
├── models.py               # SQLAlchemy ORM models (Database schema definition)
├── schemas.py              # Pydantic models (API request/response validation)
├── deps.py                 # FastAPI dependencies (Authentication, DB sessions)
├── database.py             # Database connection setup
├── seed_db.py              # Idempotent CSV-to-SQLite data seeding utility
├── ai_agent.py             # Pre-existing AI logic
├── rag.py                  # Pre-existing RAG logic
└── routers/                # Modular API route handlers
    ├── auth.py
    ├── companies.py
    ├── contacts.py
    ├── leads.py
    ├── opportunities.py
    ├── products.py
    ├── customers.py
    ├── transactions.py
    ├── activities.py
    ├── campaigns.py
    ├── campaign_responses.py
    ├── support.py
    ├── sales_reps.py
    ├── users.py
    ├── reference.py        # Combines Industries, Territories, Departments, Lead Sources
    ├── chat.py             # Pre-existing AI chat endpoints
    └── documents.py        # Pre-existing Document/RAG endpoints
```

## Key Architectural Decisions

1.  **Modular Routing**: The original monolithic `main.py` was refactored. `APIRouter` instances are defined in individual files under `routers/` and included in `main.py`. This ensures scalability as the application grows.
2.  **Soft Deletion**: Hard `DELETE` operations are avoided for core entities to preserve referential integrity. Instead, a `deleted_at` column is populated, and `GET` endpoints filter out records where `deleted_at IS NOT NULL`.
3.  **Strict Validation**: Pydantic models in `schemas.py` enforce strict input validation for all `POST` and `PUT` requests, separating Base, Create, Update, and Response concerns.
4.  **Database Seeding**: The `seed_db.py` script ensures that the exact state of the CSV dataset can be reliably and idempotently imported into the SQLite database, validating row counts and preserving primary keys exactly as they appear in the source data.
5.  **AI Integration Safety**: The pre-existing AI dataset, endpoints (`chat.py`, `documents.py`), and associated tables were deliberately excluded from schema alterations to prevent breaking the core value proposition of the system.
6.  **Dependency Injection**: Security (via `get_current_user`) and Database sessions (via `get_db`) are injected into routes, standardizing access control and connection lifecycle management.

## Testing Strategy

The backend includes a foundational automated test suite:
*   `test_d1_database.py`: Validates database row counts against CSV expectations and ensures foreign key constraints are enforced at the DB level.
*   `test_d1_api_contracts.py`: Validates that CRUD endpoints exist, return 200/401 appropriately, and use correct Pydantic response models.
*   `test_d1_frontend_regression.py`: Ensures that legacy AI/RAG and auth endpoints were not broken during the refactoring process.
