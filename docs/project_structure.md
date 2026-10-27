# Project Folder Structure

## This package, as delivered

```
package/
├── README.md
├── requirements.txt
├── docs/
│   ├── data_dictionary.md
│   ├── er_documentation.md
│   ├── er_diagram.txt
│   ├── generation_methodology.md
│   ├── business_rules.md
│   ├── data_quality_report.md
│   ├── validation_report.md
│   ├── ml_dataset_documentation.md
│   ├── ml_leakage_prevention.md
│   ├── database_import_instructions.md
│   ├── project_structure.md            (this file)
│   ├── recommended_schema.md
│   ├── recommended_api_endpoints.md
│   ├── recommended_dashboard_kpis.md
│   └── ml_project_structure.md
├── sql/
│   ├── create_tables_postgres.sql
│   └── create_tables_mysql.sql
├── scripts/
│   ├── load_postgres.py
│   ├── load_mysql.py
│   ├── validate_dataset.py
│   ├── generate_master_tables.py        (Phase 1 generator, for provenance/reproducibility)
│   ├── generate_contacts_leads.py       (Phase 2 generator)
│   ├── generate_opps_customers.py       (Phase 3 generator)
│   └── generate_ml_datasets.py          (Phase 4 generator)
└── data/
    ├── source/
    │   ├── industries.csv
    │   ├── territories.csv
    │   ├── departments.csv
    │   ├── lead_sources.csv
    │   ├── products.csv
    │   ├── sales_reps.csv
    │   ├── campaigns.csv
    │   ├── companies.csv
    │   ├── contacts.csv
    │   ├── leads.csv
    │   ├── lead_status_history.csv
    │   ├── campaign_responses.csv
    │   ├── opportunities.csv
    │   ├── opportunity_products.csv
    │   ├── opportunity_stage_history.csv
    │   ├── customers.csv
    │   ├── customer_transactions.csv
    │   └── customer_support_cases.csv
    └── ml/
        ├── lead_conversion_dataset.csv
        ├── lead_scoring_dataset.csv
        ├── sales_forecasting_dataset.csv
        ├── customer_segmentation_dataset.csv
        └── churn_prediction_dataset.csv
```

## If you build a CRM application on top of this dataset

A reasonable application repository built around this data would separate the immutable synthetic dataset from your own app code:

```
crm-app/
├── dataset/                  # this package, vendored/pinned, read-only
├── db/
│   ├── migrations/           # your app's own migrations, layered on top of
│   │                          #   sql/create_tables_*.sql (e.g. adding audit
│   │                          #   columns, soft-delete flags, app-specific
│   │                          #   tables like `users`/`api_keys`)
│   └── seeds/                # scripts/load_*.py, adapted to your migration tool
├── api/                       # see docs/recommended_api_endpoints.md
│   ├── routes/
│   ├── services/
│   └── models/
├── dashboard/                 # see docs/recommended_dashboard_kpis.md
│   ├── components/
│   └── queries/
├── ml/                        # see docs/ml_project_structure.md
└── tests/
```

Keep `dataset/` read-only and versioned separately from your app code — if you regenerate or rescale the dataset later, you want that to be a deliberate, reviewable update (new CSVs + new validation run), not something your app code accidentally depends on the exact row counts of.
