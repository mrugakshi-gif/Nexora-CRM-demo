"""
Main FastAPI application entry point.
Refactored for Phase D1 to use modular routers instead of monolithic file.
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=env_path)

from .firebase_client import init_firebase
init_firebase()

from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
from .database import SessionLocal
from .services.automation_service import run_automation

scheduler = BackgroundScheduler()

def scheduled_automation_job():
    if os.getenv("AUTOMATION_ENABLED", "false").lower() == "true":
        db = SessionLocal()
        try:
            run_automation(db)
        except Exception as e:
            print(f"Scheduled automation job failed: {e}")
        finally:
            db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.getenv("AUTOMATION_ENABLED", "false").lower() == "true":
        interval_minutes = int(os.getenv("AUTOMATION_INTERVAL_MINUTES", "60"))
        scheduler.add_job(scheduled_automation_job, "interval", minutes=interval_minutes)
        scheduler.start()
        print(f"Automation scheduler started, running every {interval_minutes} minutes.")
    yield
    if scheduler.running:
        scheduler.shutdown()

# Initialize FastAPI app
app = FastAPI(
    title="Indian B2B CRM API",
    description="Complete CRM API with business logic, analytics, and AI — Phase D2",
    version="2.0.0",
    lifespan=lifespan
)
# Configure CORS
default_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
]
env_origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()]
origins = list(dict.fromkeys(default_origins + env_origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoint
@app.get("/")
def read_root():
    return {"message": "Welcome to the Indian B2B CRM Backend API"}


# Import and include all routers
from .routers import (
    compare_endpoints,
    auth, companies, contacts, leads, opportunities,
    activities, customers, transactions, support, products,
    campaigns, campaign_responses, sales_reps, users,
    reference, chat, documents, analytics, ml, lookups, search, notifications, health, intelligence, email
)

# Core CRUD routers
app.include_router(auth.router)
app.include_router(lookups.router)
app.include_router(intelligence.router)
app.include_router(search.router)
app.include_router(notifications.router)
app.include_router(companies.router)
app.include_router(contacts.router)
app.include_router(leads.router)
app.include_router(opportunities.router)
app.include_router(activities.router)
app.include_router(customers.router)
app.include_router(transactions.router)
app.include_router(support.router)
app.include_router(products.router)
from backend.routers import automation
app.include_router(compare_endpoints.router)
app.include_router(email.router)
app.include_router(automation.router)

# Read-only entity routers
app.include_router(campaigns.router)
app.include_router(campaign_responses.router)
app.include_router(sales_reps.router)
app.include_router(users.router)

# Reference data routers
app.include_router(reference.router_industries)
app.include_router(reference.router_territories)
app.include_router(reference.router_departments)
app.include_router(reference.router_lead_sources)

# AI & Documents
app.include_router(chat.router)
app.include_router(documents.router)

# Analytics
app.include_router(analytics.router)
app.include_router(health.router)

# ML Predictions
app.include_router(ml.router)
