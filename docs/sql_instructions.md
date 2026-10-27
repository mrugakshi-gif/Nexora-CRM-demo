# SQL Analysis Instructions

The `sql/crm_analysis.sql` file contains 16 professional SQL queries designed to run against the Indian B2B CRM dataset.

Because the data is currently stored in raw CSV format (`data/source/*.csv`), you will need to load them into a SQL engine to execute the queries.

## Option 1: Zero-Setup (DuckDB) Recommended

If you want to run these queries immediately without installing a database server, we highly recommend **DuckDB**. DuckDB can query CSV files directly.

1. Install the DuckDB CLI for your operating system (e.g. `brew install duckdb` on macOS).
2. Open your terminal in the `FINAL_INDIAN_B2B_CRM_DATASET` directory.
3. Start DuckDB:
   ```bash
   duckdb
   ```
4. Create views or tables pointing directly to the CSVs. For example:
   ```sql
   CREATE VIEW opportunities AS SELECT * FROM 'data/source/opportunities.csv';
   CREATE VIEW companies AS SELECT * FROM 'data/source/companies.csv';
   CREATE VIEW industries AS SELECT * FROM 'data/source/industries.csv';
   -- repeat for the other tables
   ```
5. You can now copy and paste any of the 16 queries directly into the DuckDB prompt!

## Option 2: Traditional Relational Database (PostgreSQL / MySQL)

If you are building an application on top of this dataset, you should import the data into a robust RDBMS like PostgreSQL.

1. Create a new database (e.g., `indian_b2b_crm`).
2. Run the table creation scripts (DDL) matching the schema described in `docs/data_dictionary.md`.
3. Use the native bulk-import tool to load the CSVs (e.g., the `COPY` command in Postgres):
   ```sql
   COPY opportunities FROM '/path/to/opportunities.csv' DELIMITER ',' CSV HEADER;
   ```
4. Execute `sql/crm_analysis.sql` using your preferred SQL client (like DBeaver, DataGrip, or `psql`).

## Note on Schema Enforcement

The SQL queries in `sql/crm_analysis.sql` perfectly adhere to the real schema. They do not invent any tables or columns. If a query fails, ensure you have correctly loaded all 24 CSV files with their exact original headers into your SQL engine.
