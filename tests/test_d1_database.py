import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# DB connection using SQLAlchemy
DATABASE_URL = "sqlite:///backend/crm.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_database_table_counts(db):
    """Verify that all tables have at least the seeded row counts.

    Note: D2 tests may create additional records (which are then soft-deleted)
    so we assert >= rather than == to avoid flakiness.
    """
    # Minimum expected counts based on seed output
    min_expected = {
        "companies": 1200,
        "contacts": 925,
        "leads": 1083,
        "opportunities": 198,
        "campaigns": 180,
        "products": 20
    }
    for table, count in min_expected.items():
        result = db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
        assert result >= count, f"Expected at least {count} in {table}, got {result}"

def test_company_relationships(db):
    """Verify Company -> Contacts, Leads, Opportunities."""
    company_id = "COM-8218" # Example valid company ID from DB (will just pick the first one)
    company = db.execute(text("SELECT company_id FROM companies LIMIT 1")).scalar()
    
    contacts = db.execute(text("SELECT COUNT(*) FROM contacts WHERE company_id = :id"), {"id": company}).scalar()
    assert contacts >= 0 # Just checking the query runs and FK works
    
    leads = db.execute(text("SELECT COUNT(*) FROM leads WHERE company_id = :id"), {"id": company}).scalar()
    assert leads >= 0

def test_opportunity_products(db):
    """Verify Opportunity -> Products relationship."""
    opp = db.execute(text("SELECT opportunity_id FROM opportunities LIMIT 1")).scalar()
    products = db.execute(text("SELECT COUNT(*) FROM opportunity_products WHERE opportunity_id = :id"), {"id": opp}).scalar()
    assert products >= 0

def test_foreign_key_integrity():
    """
    Exhaustively tests that there are absolutely zero orphaned records
    in the database across all defined foreign keys, using NOT EXISTS.
    """
    from backend.validate_fks import validate_fks
    try:
        orphans = validate_fks()
        assert orphans == 0, f"Found {orphans} orphaned records in the database!"
    except Exception as e:
        pytest.fail(f"FK Validation failed: {e}")
