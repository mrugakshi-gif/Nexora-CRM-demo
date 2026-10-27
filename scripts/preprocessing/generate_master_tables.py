#!/usr/bin/env python3
"""
Indian B2B CRM synthetic dataset — Phase 1: Master & Reference tables.
Generates: industries, territories, departments, lead_sources, products,
           sales_reps, campaigns, companies

All interaction/financial/behavioral data is synthetic. A small subset of
`companies` rows use real, publicly known Indian company names + broad public
industry/HQ-city facts as an identity skin only (see name_is_real_entity flag).
No revenue, GSTIN, pincode, website, or contact details for these rows are
claimed to be real — those fields are synthetic for every row, real or not.
"""
import csv
import random
import string
from datetime import date, datetime, timedelta

random.seed(20260915)  # fixed seed -> reproducible, auditable output

# Sub-industry vocabulary, one list per industry_id. Populated via a
# SEPARATE, independently-seeded random.Random instance (see
# _sub_industry_rng below) rather than the module-level `random` stream, so
# that filling in this previously-always-blank column does not consume an
# extra draw from the shared PRNG and shift every downstream field (GSTIN,
# pincode, dates, rep assignment, etc.) for this and every later company.
SUB_INDUSTRIES = {
    "IND-01": ["IT Services & Consulting", "Software Products/SaaS", "IT Infrastructure & Cloud",
               "Cybersecurity", "BPO/ITES"],
    "IND-02": ["Industrial Machinery", "Metals & Metal Fabrication", "Capital Goods",
               "Electrical Equipment", "Precision Engineering"],
    "IND-03": ["Textile Manufacturing", "Garment & Apparel", "Home Textiles", "Technical Textiles"],
    "IND-04": ["Pharmaceutical Manufacturing", "Hospitals & Clinics", "Diagnostics & Labs",
               "Medical Devices", "Health-Tech"],
    "IND-05": ["Packaged Foods & Beverages", "Personal Care & Household", "Retail Chains",
               "Consumer Durables"],
    "IND-06": ["Banking", "NBFC", "Insurance", "Asset Management", "Fintech"],
    "IND-07": ["Freight & Cargo", "Warehousing & 3PL", "Courier & Last-Mile Delivery",
               "Shipping & Freight Forwarding"],
    "IND-08": ["Residential Real Estate", "Commercial Real Estate", "Construction & Contracting",
               "Real Estate Services"],
    "IND-09": ["K-12 Education", "Higher Education", "EdTech Platforms", "Test Prep & Coaching",
               "Skill Development & Vocational Training"],
    "IND-10": ["Automotive OEM", "Auto Components & Ancillaries", "Two-Wheeler Manufacturing",
               "EV & Auto-Electronics"],
    "IND-11": ["Agri-Inputs (Seeds/Fertilizers)", "Agri-Processing", "Dairy & Allied",
               "Farm Equipment"],
    "IND-12": ["Broadcasting & TV", "Digital Media & OTT", "Advertising & Marketing Agencies",
               "Gaming & Animation"],
    "IND-13": ["Power Generation", "Renewable Energy", "Power Transmission & Distribution",
               "Oil & Gas"],
    "IND-14": ["Online Marketplace", "D2C E-commerce", "Quick Commerce", "E-commerce Enablement"],
    "IND-15": ["Hotels & Resorts", "Travel Agencies & Tour Operators", "Online Travel/Booking",
               "Restaurants & QSR"],
    "IND-16": ["Telecom Operators", "Telecom Infrastructure", "Network Equipment & VAS"],
    "IND-17": ["Specialty Chemicals", "Agrochemicals", "Petrochemicals", "Industrial Gases"],
    "IND-18": ["Roads & Highways EPC", "Power Sector EPC", "Industrial EPC", "Urban Infrastructure"],
    "IND-19": ["Management Consulting", "Legal Services", "Accounting & Audit",
               "HR & Staffing Services", "Market Research"],
    "IND-20": ["Central Government", "State Government", "Public Sector Undertaking (PSU)",
               "Municipal/Local Body"],
}

def pick_sub_industry(company_id, industry_id):
    """Deterministic pick from an independent local RNG (seeded from the
    company_id + industry_id, not from the shared module-level `random`
    stream), so backfilling this column can never perturb any other
    generated field's value. ~6% of companies still get a blank
    sub_industry (a real company sometimes just isn't sub-classified in a
    CRM), matching the sparsity that other optional company fields show."""
    options = SUB_INDUSTRIES.get(industry_id)
    if not options:
        return ""
    local_rng = random.Random(f"subind::{company_id}::{industry_id}")
    if local_rng.random() < 0.06:
        return ""
    return local_rng.choice(options)

OUT = "/home/claude/crm_gen/output"
import os
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------------------
# 1. industries
# ---------------------------------------------------------------------------
INDUSTRIES = [
    ("IND-01", "IT & Software Services", "Technology"),
    ("IND-02", "Manufacturing (Industrial/Engineering)", "Manufacturing"),
    ("IND-03", "Manufacturing (Textiles & Apparel)", "Manufacturing"),
    ("IND-04", "Pharmaceuticals & Healthcare", "Services"),
    ("IND-05", "FMCG & Retail", "Trade & Retail"),
    ("IND-06", "BFSI", "Services"),
    ("IND-07", "Logistics & Supply Chain", "Services"),
    ("IND-08", "Real Estate & Construction", "Manufacturing"),
    ("IND-09", "Education & EdTech", "Services"),
    ("IND-10", "Automotive & Auto Components", "Manufacturing"),
    ("IND-11", "Agriculture & Agri-Business", "Primary Sector"),
    ("IND-12", "Media & Entertainment", "Services"),
    ("IND-13", "Energy & Power", "Primary Sector"),
    ("IND-14", "E-commerce", "Trade & Retail"),
    ("IND-15", "Hospitality & Travel", "Services"),
    ("IND-16", "Telecom", "Technology"),
    ("IND-17", "Chemicals", "Manufacturing"),
    ("IND-18", "Infrastructure/EPC", "Manufacturing"),
    ("IND-19", "Professional Services", "Services"),
    ("IND-20", "Public Sector/Government", "Public Sector"),
]
industries_rows = [
    {"industry_id": i, "industry_name": n, "industry_category": c, "is_active": True}
    for i, n, c in INDUSTRIES
]
IND_BY_NAME = {n: i for i, n, c in INDUSTRIES}

# ---------------------------------------------------------------------------
# 2. territories
# ---------------------------------------------------------------------------
TERRITORIES = [
    ("TERR-001", "Delhi-NCR Core", "North", "IND-01"),
    ("TERR-002", "Punjab & Chandigarh", "North", None),
    ("TERR-003", "Rajasthan", "North", None),
    ("TERR-004", "UP (Lucknow & Central UP)", "North", None),
    ("TERR-005", "Mumbai Metro", "West", "IND-06"),
    ("TERR-006", "Pune", "West", "IND-01"),
    ("TERR-007", "Gujarat (Ahmedabad-Surat)", "West", "IND-03"),
    ("TERR-008", "Maharashtra (Nagpur-Nashik)", "West", None),
    ("TERR-009", "Bengaluru", "South", "IND-01"),
    ("TERR-010", "Chennai", "South", "IND-10"),
    ("TERR-011", "Hyderabad", "South", "IND-01"),
    ("TERR-012", "Kerala (Kochi)", "South", None),
    ("TERR-013", "Tamil Nadu (Coimbatore)", "South", "IND-02"),
    ("TERR-014", "Andhra Pradesh (Vizag)", "South", None),
    ("TERR-015", "Kolkata & West Bengal", "East", None),
    ("TERR-016", "Odisha & East Coast", "East", None),
    ("TERR-017", "Bihar & Jharkhand", "East", None),
    ("TERR-018", "MP & Chhattisgarh (Indore-Raipur)", "Central", None),
]
territories_rows = [
    {"territory_id": t, "territory_name": n, "region": r, "primary_industry_focus": f}
    for t, n, r, f in TERRITORIES
]

# ---------------------------------------------------------------------------
# 3. departments
# ---------------------------------------------------------------------------
DEPARTMENTS = [
    ("DEPT-0001", "Enterprise Sales", "Pan-India"),
    ("DEPT-0002", "SMB Sales", "Pan-India"),
    ("DEPT-0003", "Inside Sales", "Pan-India"),
    ("DEPT-0004", "Customer Success", "Pan-India"),
    ("DEPT-0005", "Marketing", "Pan-India"),
    ("DEPT-0006", "Sales Operations", "Pan-India"),
    ("DEPT-0007", "Channel Partnerships", "Pan-India"),
]
departments_rows = [
    {"department_id": d, "department_name": n, "region_focus": r,
     "created_at": "2022-04-01"}
    for d, n, r in DEPARTMENTS
]

# ---------------------------------------------------------------------------
# 4. lead_sources
# ---------------------------------------------------------------------------
LEAD_SOURCES = [
    ("SRC-01", "Website Form", "Inbound"),
    ("SRC-02", "Inbound Call", "Inbound"),
    ("SRC-03", "Referral", "Referral"),
    ("SRC-04", "Trade Show/Exhibition", "Outbound"),
    ("SRC-05", "LinkedIn Outbound", "Outbound"),
    ("SRC-06", "Cold Email", "Outbound"),
    ("SRC-07", "Partner Channel", "Partner"),
    ("SRC-08", "IndiaMART/TradeIndia Listing", "Inbound"),
    ("SRC-09", "Google Ads", "Inbound"),
    ("SRC-10", "Organic Search", "Inbound"),
    ("SRC-11", "Webinar", "Inbound"),
    ("SRC-12", "Existing Customer Upsell", "Referral"),
]
lead_sources_rows = [
    {"lead_source_id": s, "source_name": n, "source_category": c}
    for s, n, c in LEAD_SOURCES
]

# ---------------------------------------------------------------------------
# 5. products
# ---------------------------------------------------------------------------
PRODUCTS = [
    ("PROD-001", "CRM Suite — Starter", "SaaS Subscription", "Monthly Subscription", 2999),
    ("PROD-002", "CRM Suite — Professional", "SaaS Subscription", "Annual Subscription", 89999),
    ("PROD-003", "CRM Suite — Enterprise", "SaaS Subscription", "Annual Subscription", 249999),
    ("PROD-004", "Sales Analytics Add-on", "SaaS Subscription", "Annual Subscription", 34999),
    ("PROD-005", "Marketing Automation Add-on", "SaaS Subscription", "Annual Subscription", 44999),
    ("PROD-006", "WhatsApp Business Integration", "SaaS Subscription", "Monthly Subscription", 1999),
    ("PROD-007", "Mobile Sales App Module", "SaaS Subscription", "Annual Subscription", 19999),
    ("PROD-008", "Lead Scoring AI Module", "SaaS Subscription", "Annual Subscription", 59999),
    ("PROD-009", "Customer Support Desk Module", "SaaS Subscription", "Annual Subscription", 39999),
    ("PROD-010", "Data Migration Service", "Implementation Services", "One-time", 74999),
    ("PROD-011", "Onboarding & Setup Package", "Implementation Services", "One-time", 49999),
    ("PROD-012", "Custom Integration Development", "Implementation Services", "One-time", 149999),
    ("PROD-013", "Standard Support/AMC", "Support/AMC", "Annual Subscription", 24999),
    ("PROD-014", "Premium Support/AMC 24x7", "Support/AMC", "Annual Subscription", 79999),
    ("PROD-015", "On-site Training Package", "Training", "One-time", 34999),
    ("PROD-016", "Virtual Training Package", "Training", "One-time", 12999),
    ("PROD-017", "API Access Add-on (per 1,000 calls)", "SaaS Subscription", "Usage-based", 499),
    ("PROD-018", "Advanced Reporting & BI Module", "SaaS Subscription", "Annual Subscription", 54999),
    ("PROD-019", "Data Storage Expansion (per 100GB)", "SaaS Subscription", "Usage-based", 4999),
    ("PROD-020", "On-Premise Server License", "Software License", "One-time", 399999),
]
products_rows = [
    {"product_id": p, "product_name": n, "product_category": c,
     "pricing_model": pm, "list_price_inr": price, "is_active": True}
    for p, n, c, pm, price in PRODUCTS
]

# ---------------------------------------------------------------------------
# Name pools (synthetic, Indian, diverse across regions/communities)
# ---------------------------------------------------------------------------
FIRST_NAMES = [
    "Aarav","Vivaan","Aditya","Vihaan","Arjun","Reyansh","Krishna","Ishaan","Kabir","Rohan",
    "Rahul","Amit","Suresh","Rajesh","Sanjay","Vikram","Anil","Manoj","Deepak","Naveen",
    "Priya","Ananya","Diya","Isha","Saanvi","Aarohi","Kavya","Neha","Pooja","Riya",
    "Sunita","Anita","Meera","Kavita","Shalini","Divya","Swati","Nisha","Radha","Lakshmi",
    "Arun","Karthik","Venkatesh","Ramesh","Srinivas","Balaji","Prasad","Ganesh","Murali","Raghavan",
    "Farhan","Imran","Zaid","Sameer","Ayesha","Zoya","Fatima","Nusrat","Salman","Arif",
    "Gurpreet","Harpreet","Jasbir","Simran","Manpreet","Navjot","Karan","Rajinder","Amrit","Baljeet",
    "Sneha","Pallavi","Preeti","Ritu","Shweta","Vandana","Alok","Ashok","Bharat","Chetan",
    "Devendra","Girish","Hemant","Jayesh","Kiran","Mahesh","Nikhil","Omkar","Pankaj","Qamar",
]
LAST_NAMES = [
    "Sharma","Verma","Gupta","Mehta","Shah","Patel","Desai","Joshi","Iyer","Nair",
    "Menon","Pillai","Reddy","Rao","Naidu","Chatterjee","Banerjee","Mukherjee","Das","Ghosh",
    "Singh","Kaur","Khan","Ahmed","Ansari","Sheikh","Kapoor","Malhotra","Khanna","Chopra",
    "Agarwal","Bansal","Jain","Bhatia","Saxena","Mishra","Pandey","Tiwari","Dubey","Trivedi",
    "Kulkarni","Deshmukh","Deshpande","Kelkar","Patil","Bhosale","Gaikwad","Naik","Shetty","Hegde",
    "Raut","Chauhan","Rathore","Yadav","Prasad","Sinha","Thakur","Bhatt","Vyas","Solanki",
]

def unique_full_names(n):
    seen = set()
    out = []
    while len(out) < n:
        fn = random.choice(FIRST_NAMES)
        ln = random.choice(LAST_NAMES)
        full = f"{fn} {ln}"
        if full in seen:
            continue
        seen.add(full)
        out.append((fn, ln, full))
    return out

CITY_TIER = {
    "Mumbai": ("Maharashtra", "West", 1), "Delhi-NCR": ("Delhi", "North", 1),
    "Bengaluru": ("Karnataka", "South", 1), "Chennai": ("Tamil Nadu", "South", 1),
    "Hyderabad": ("Telangana", "South", 1), "Pune": ("Maharashtra", "West", 1),
    "Kolkata": ("West Bengal", "East", 1), "Ahmedabad": ("Gujarat", "West", 1),
    "Chandigarh": ("Punjab", "North", 2), "Lucknow": ("Uttar Pradesh", "North", 2),
    "Jaipur": ("Rajasthan", "North", 2), "Surat": ("Gujarat", "West", 2),
    "Nagpur": ("Maharashtra", "West", 2), "Nashik": ("Maharashtra", "West", 2),
    "Kochi": ("Kerala", "South", 2), "Coimbatore": ("Tamil Nadu", "South", 2),
    "Visakhapatnam": ("Andhra Pradesh", "South", 2), "Bhubaneswar": ("Odisha", "East", 2),
    "Patna": ("Bihar", "East", 2), "Guwahati": ("Assam", "East", 3),
    "Indore": ("Madhya Pradesh", "Central", 2), "Bhopal": ("Madhya Pradesh", "Central", 3),
    "Raipur": ("Chhattisgarh", "Central", 3),
}
TIER1_CITIES = [c for c, v in CITY_TIER.items() if v[2] == 1]
TIER23_CITIES = [c for c, v in CITY_TIER.items() if v[2] != 1]
STATE_CODE = {  # for synthetic GSTIN state prefix
    "Maharashtra": "27", "Delhi": "07", "Karnataka": "29", "Tamil Nadu": "33",
    "Telangana": "36", "West Bengal": "19", "Gujarat": "24", "Punjab": "03",
    "Uttar Pradesh": "09", "Rajasthan": "08", "Kerala": "32", "Andhra Pradesh": "37",
    "Odisha": "21", "Bihar": "10", "Assam": "18", "Madhya Pradesh": "23",
    "Chhattisgarh": "22",
}

def pick_city():
    return random.choice(TIER1_CITIES) if random.random() < 0.67 else random.choice(TIER23_CITIES)

# ---------------------------------------------------------------------------
# 6. sales_reps
# ---------------------------------------------------------------------------
N_REPS = 80
rep_names = unique_full_names(N_REPS)
TERR_IDS = [t[0] for t in TERRITORIES]

# Build hierarchy: 1 Sales Director, 6 Sales Managers, rest AE/Sr AE/SDR/CSM
role_plan = (
    ["Sales Director"] * 1 +
    ["Sales Manager"] * 6 +
    ["Senior Account Executive"] * 14 +
    ["Account Executive"] * 24 +
    ["SDR"] * 18 +
    ["Customer Success Manager"] * 17
)
random.shuffle(role_plan)
assert len(role_plan) == N_REPS

def role_to_dept(role):
    if role == "Customer Success Manager":
        return "DEPT-0004"
    if role == "Sales Director":
        return random.choice(["DEPT-0001", "DEPT-0002", "DEPT-0006"])
    if role == "SDR":
        return "DEPT-0003"
    return random.choice(["DEPT-0001", "DEPT-0002", "DEPT-0007"])

base_hire = date(2021, 4, 1)
today = date(2026, 9, 15)

sales_reps_rows = []
director_id = None
manager_ids = []
for idx, ((fn, ln, full), role) in enumerate(zip(rep_names, role_plan), start=1):
    rep_id = f"REP-{idx:04d}"
    dept = role_to_dept(role)
    terr = random.choice(TERR_IDS)
    hire_days = random.randint(0, (today - base_hire).days - 60)
    hire_date = base_hire + timedelta(days=hire_days)
    is_active = random.random() > 0.08
    term_date = ""
    if not is_active:
        term_days = random.randint(60, (today - hire_date).days)
        term_date = (hire_date + timedelta(days=term_days)).isoformat()
    fn_e = "".join(ch for ch in fn.lower() if ch.isalnum())
    ln_e = "".join(ch for ch in ln.lower() if ch.isalnum())
    email_local = f"{fn_e}.{ln_e}{idx}"
    email = f"{email_local}@crmvendor-india.example"
    phone = f"+91-9{random.randint(100000000,999999999)}"
    row = {
        "rep_id": rep_id, "full_name": full, "email": email, "phone": phone,
        "department_id": dept, "manager_rep_id": "", "role": role,
        "territory_id": terr, "hire_date": hire_date.isoformat(),
        "is_active": is_active, "termination_date": term_date,
    }
    sales_reps_rows.append(row)
    if role == "Sales Director":
        director_id = rep_id
    elif role == "Sales Manager":
        manager_ids.append(rep_id)

# assign managers: Sales Managers report to Director; AE/SrAE/SDR report to a Sales Manager; CSMs report to no one (null, CS dept separate) or to director
for row in sales_reps_rows:
    if row["role"] == "Sales Manager":
        row["manager_rep_id"] = director_id
    elif row["role"] in ("Senior Account Executive", "Account Executive", "SDR"):
        row["manager_rep_id"] = random.choice(manager_ids)
    elif row["role"] == "Customer Success Manager":
        row["manager_rep_id"] = ""  # separate CS reporting line, not modeled further
    # Sales Director manager_rep_id stays "" (top of hierarchy)

active_rep_ids = [r["rep_id"] for r in sales_reps_rows if r["is_active"]]
rep_by_territory = {}
for r in sales_reps_rows:
    if r["is_active"]:
        rep_by_territory.setdefault(r["territory_id"], []).append(r["rep_id"])

# ---------------------------------------------------------------------------
# 7. campaigns
# ---------------------------------------------------------------------------
N_CAMPAIGNS = 180
CAMPAIGN_TYPES = ["Email", "Webinar", "Trade Show", "Social Media", "Content/SEO", "Paid Search", "Partner Event"]
CAMPAIGN_THEME = {
    "Email": ["Festive Season CRM Offer", "Year-End Renewal Drive", "New Feature Announcement"],
    "Webinar": ["CRM Best Practices for Indian SMEs", "Sales Automation Masterclass", "Lead Scoring Deep Dive"],
    "Trade Show": ["IT Expo", "Manufacturing Tech Summit", "Retail Tech Conclave"],
    "Social Media": ["LinkedIn Lead Gen Push", "Instagram Brand Awareness", "Twitter/X Product Launch"],
    "Content/SEO": ["CRM Buyer's Guide Content Push", "Industry Report SEO Campaign"],
    "Paid Search": ["Google Ads — CRM Software India", "Google Ads — Sales Automation Tools"],
    "Partner Event": ["Channel Partner Meet", "Reseller Enablement Day"],
}
campaign_start = date(2023, 4, 1)
campaigns_rows = []
for i in range(1, N_CAMPAIGNS + 1):
    cid = f"CAMP-{i:03d}"
    ctype = random.choice(CAMPAIGN_TYPES)
    theme = random.choice(CAMPAIGN_THEME[ctype])
    name = f"{theme} {random.choice(['FY24','FY25','FY26'])}-{random.choice(['Q1','Q2','Q3','Q4'])}"
    start_offset = random.randint(0, (today - campaign_start).days - 30)
    start = campaign_start + timedelta(days=start_offset)
    dur = random.randint(14, 90)
    ongoing = random.random() < 0.08 and (today - start).days < dur
    end = "" if ongoing else (start + timedelta(days=dur)).isoformat()
    budget = round(random.uniform(25000, 1500000), 2) if random.random() > 0.05 else ""
    target_ind = random.choice(industries_rows)["industry_id"] if random.random() > 0.3 else ""
    dept = random.choice(["DEPT-0005", "DEPT-0007"])
    campaigns_rows.append({
        "campaign_id": cid, "campaign_name": name, "campaign_type": ctype,
        "start_date": start.isoformat(), "end_date": end,
        "budget_inr": budget, "target_industry_id": target_ind,
        "owner_department_id": dept,
    })

# ---------------------------------------------------------------------------
# 8. companies
# ---------------------------------------------------------------------------
# Curated list of real, publicly well-known Indian companies used ONLY as an
# identity skin (name + broad public industry + broad public HQ city).
# No revenue/employee/GSTIN/pincode/website/contact data for these rows is
# real -- all such fields remain synthetic for every row, real or not.
REAL_COMPANIES = [
    ("Tata Consultancy Services","IT & Software Services","Mumbai"),
    ("Infosys","IT & Software Services","Bengaluru"),
    ("Wipro","IT & Software Services","Bengaluru"),
    ("HCL Technologies","IT & Software Services","Delhi-NCR"),
    ("Tech Mahindra","IT & Software Services","Pune"),
    ("Mphasis","IT & Software Services","Bengaluru"),
    ("Persistent Systems","IT & Software Services","Pune"),
    ("Zensar Technologies","IT & Software Services","Pune"),
    ("Cyient","IT & Software Services","Hyderabad"),
    ("KPIT Technologies","IT & Software Services","Pune"),
    ("Tata Elxsi","IT & Software Services","Bengaluru"),
    ("Zoho Corporation","IT & Software Services","Chennai"),
    ("Freshworks","IT & Software Services","Chennai"),
    ("Postman","IT & Software Services","Bengaluru"),
    ("Razorpay","IT & Software Services","Bengaluru"),
    ("Reliance Industries","Energy & Power","Mumbai"),
    ("Adani Enterprises","Energy & Power","Ahmedabad"),
    ("NTPC Limited","Energy & Power","Delhi-NCR"),
    ("Oil and Natural Gas Corporation","Energy & Power","Delhi-NCR"),
    ("Indian Oil Corporation","Energy & Power","Delhi-NCR"),
    ("Power Grid Corporation of India","Energy & Power","Delhi-NCR"),
    ("Bharat Petroleum Corporation","Energy & Power","Mumbai"),
    ("Tata Steel","Manufacturing (Industrial/Engineering)","Mumbai"),
    ("JSW Steel","Manufacturing (Industrial/Engineering)","Mumbai"),
    ("Hindalco Industries","Manufacturing (Industrial/Engineering)","Mumbai"),
    ("Larsen & Toubro","Infrastructure/EPC","Mumbai"),
    ("Bharat Forge","Manufacturing (Industrial/Engineering)","Pune"),
    ("Cummins India","Manufacturing (Industrial/Engineering)","Pune"),
    ("Thermax","Manufacturing (Industrial/Engineering)","Pune"),
    ("Siemens India","Manufacturing (Industrial/Engineering)","Mumbai"),
    ("ABB India","Manufacturing (Industrial/Engineering)","Bengaluru"),
    ("Bharat Heavy Electricals","Manufacturing (Industrial/Engineering)","Delhi-NCR"),
    ("Hindustan Aeronautics","Manufacturing (Industrial/Engineering)","Bengaluru"),
    ("Bharat Electronics","Manufacturing (Industrial/Engineering)","Bengaluru"),
    ("Mahindra & Mahindra","Automotive & Auto Components","Mumbai"),
    ("Bajaj Auto","Automotive & Auto Components","Pune"),
    ("Eicher Motors","Automotive & Auto Components","Chennai"),
    ("Ashok Leyland","Automotive & Auto Components","Chennai"),
    ("MRF Limited","Automotive & Auto Components","Chennai"),
    ("Apollo Tyres","Automotive & Auto Components","Delhi-NCR"),
    ("CEAT Limited","Automotive & Auto Components","Mumbai"),
    ("Bosch India","Automotive & Auto Components","Bengaluru"),
    ("ITC Limited","FMCG & Retail","Kolkata"),
    ("Hindustan Unilever","FMCG & Retail","Mumbai"),
    ("Dabur India","FMCG & Retail","Delhi-NCR"),
    ("Marico Limited","FMCG & Retail","Mumbai"),
    ("Britannia Industries","FMCG & Retail","Kolkata"),
    ("Nestle India","FMCG & Retail","Delhi-NCR"),
    ("Asian Paints","Chemicals","Mumbai"),
    ("Pidilite Industries","Chemicals","Mumbai"),
    ("Berger Paints India","Chemicals","Kolkata"),
    ("Trent Limited","E-commerce","Mumbai"),
    ("DMart (Avenue Supermarts)","E-commerce","Mumbai"),
    ("Shoppers Stop","E-commerce","Mumbai"),
    ("BigBasket","E-commerce","Bengaluru"),
    ("Lenskart","E-commerce","Delhi-NCR"),
    ("Nykaa","E-commerce","Mumbai"),
    ("Flipkart","E-commerce","Bengaluru"),
    ("Meesho","E-commerce","Bengaluru"),
    ("Zomato","Hospitality & Travel","Delhi-NCR"),
    ("Swiggy","Hospitality & Travel","Bengaluru"),
    ("Ola","Automotive & Auto Components","Bengaluru"),
    ("Urban Company","Professional Services","Delhi-NCR"),
    ("PolicyBazaar","BFSI","Delhi-NCR"),
    ("Paytm","BFSI","Delhi-NCR"),
    ("CRED","BFSI","Bengaluru"),
    ("Kotak Mahindra Bank","BFSI","Mumbai"),
    ("HDFC Bank","BFSI","Mumbai"),
    ("ICICI Bank","BFSI","Mumbai"),
    ("Axis Bank","BFSI","Mumbai"),
    ("IndusInd Bank","BFSI","Mumbai"),
    ("State Bank of India","BFSI","Mumbai"),
    ("Dr. Reddy's Laboratories","Pharmaceuticals & Healthcare","Hyderabad"),
    ("Cipla Limited","Pharmaceuticals & Healthcare","Mumbai"),
    ("Sun Pharmaceutical Industries","Pharmaceuticals & Healthcare","Mumbai"),
    ("PharmEasy","Pharmaceuticals & Healthcare","Mumbai"),
    ("1mg","Pharmaceuticals & Healthcare","Delhi-NCR"),
    ("Practo","Pharmaceuticals & Healthcare","Bengaluru"),
    ("upGrad","Education & EdTech","Mumbai"),
    ("Unacademy","Education & EdTech","Bengaluru"),
    ("Vedantu","Education & EdTech","Bengaluru"),
    ("Physics Wallah","Education & EdTech","Delhi-NCR"),
    ("Delhivery","Logistics & Supply Chain","Delhi-NCR"),
    ("Blue Dart Express","Logistics & Supply Chain","Mumbai"),
    ("DTDC Express","Logistics & Supply Chain","Bengaluru"),
    ("Mahindra Logistics","Logistics & Supply Chain","Mumbai"),
    ("GMR Group","Infrastructure/EPC","Delhi-NCR"),
    ("DLF Limited","Real Estate & Construction","Delhi-NCR"),
    ("Godrej Properties","Real Estate & Construction","Mumbai"),
    ("Oberoi Realty","Real Estate & Construction","Mumbai"),
    ("Prestige Estates Projects","Real Estate & Construction","Bengaluru"),
    ("Sobha Limited","Real Estate & Construction","Bengaluru"),
    ("Brigade Group","Real Estate & Construction","Bengaluru"),
    ("Bharti Airtel","Telecom","Delhi-NCR"),
    ("Vodafone Idea","Telecom","Mumbai"),
    ("Reliance Jio","Telecom","Mumbai"),
]
assert len(set(n for n, i, c in REAL_COMPANIES)) == len(REAL_COMPANIES)

# Public-knowledge legal type for each real company (deterministic, not randomized --
# random assignment previously mislabeled several govt-owned PSUs as plain "Public
# Limited"/"Private Limited"). PSU = govt-owned Public Sector Undertaking (even if
# also stock-exchange listed); Public Limited = listed private-sector company;
# Private Limited = unlisted company. This is public-knowledge categorization only,
# not a claim about any other attribute.
REAL_COMPANY_TYPE = {
    "NTPC Limited": "PSU", "Oil and Natural Gas Corporation": "PSU",
    "Indian Oil Corporation": "PSU", "Power Grid Corporation of India": "PSU",
    "Bharat Petroleum Corporation": "PSU", "Bharat Heavy Electricals": "PSU",
    "Hindustan Aeronautics": "PSU", "Bharat Electronics": "PSU",
    "State Bank of India": "PSU",
    "Zoho Corporation": "Private Limited", "Freshworks": "Private Limited",
    "Postman": "Private Limited", "Razorpay": "Private Limited",
    "CRED": "Private Limited", "Meesho": "Private Limited",
    "BigBasket": "Private Limited", "Lenskart": "Private Limited",
    "Urban Company": "Private Limited", "PharmEasy": "Private Limited",
    "1mg": "Private Limited", "Practo": "Private Limited",
    "upGrad": "Private Limited", "Unacademy": "Private Limited",
    "Vedantu": "Private Limited", "Physics Wallah": "Private Limited",
    "DTDC Express": "Private Limited", "Ola": "Private Limited",
    "Reliance Jio": "Private Limited", "Flipkart": "Private Limited",
    "Adani Enterprises": "Public Limited",
}
# Real companies confirmed publicly listed (NSE/BSE) -> Public Limited unless
# already overridden above as PSU or known-private.
KNOWN_LISTED_REAL = {
    "Tata Consultancy Services","Infosys","Wipro","HCL Technologies","Tech Mahindra",
    "Mphasis","Persistent Systems","Zensar Technologies","Cyient","KPIT Technologies",
    "Tata Elxsi","Reliance Industries","Tata Steel","JSW Steel","Hindalco Industries",
    "Larsen & Toubro","Bharat Forge","Cummins India","Thermax","Siemens India",
    "ABB India","Mahindra & Mahindra","Bajaj Auto","Eicher Motors","Ashok Leyland",
    "MRF Limited","Apollo Tyres","CEAT Limited","Bosch India","ITC Limited",
    "Hindustan Unilever","Dabur India","Marico Limited","Britannia Industries",
    "Nestle India","Asian Paints","Pidilite Industries","Berger Paints India",
    "Trent Limited","DMart (Avenue Supermarts)","Shoppers Stop","Nykaa","Zomato",
    "PolicyBazaar","Paytm","Kotak Mahindra Bank","HDFC Bank","ICICI Bank","Axis Bank",
    "IndusInd Bank","Dr. Reddy's Laboratories","Cipla Limited",
    "Sun Pharmaceutical Industries","Delhivery","GMR Group","DLF Limited",
    "Godrej Properties","Oberoi Realty","Prestige Estates Projects","Sobha Limited",
    "Brigade Group","Bharti Airtel","Vodafone Idea","Mahindra Logistics",
}
for nm in KNOWN_LISTED_REAL:
    REAL_COMPANY_TYPE.setdefault(nm, "Public Limited")
# Anything not explicitly classified defaults to Private Limited (safer default
# than randomly guessing "Public Limited" for an unverified entity).

# Realistic size-band override for well-known but mid-scale real companies
# (headcount in the low thousands, not the "large conglomerate" tier) --
# previously these were randomly assigned Enterprise 85% of the time regardless
# of company.
REAL_COMPANY_SIZE_HINT = {
    "Postman": "Large", "CRED": "Large", "Practo": "Large", "upGrad": "Large",
    "Vedantu": "Large", "Physics Wallah": "Large", "1mg": "Large",
    "PharmEasy": "Large", "Unacademy": "Large", "Urban Company": "Large",
    "BigBasket": "Large", "DTDC Express": "Large",
}

N_COMPANIES = 1200
N_REAL = len(REAL_COMPANIES)  # use the full curated real-company list (~8%); see data-quality report

SECTOR_WORDS = {
    "IND-01": ["Technologies","Softech","Infosystems","Digital Solutions","InfoTech","Software Labs","Systems","Cloud Solutions","Digital Ventures","Infotech Solutions"],
    "IND-02": ["Engineering Works","Precision Tools","Industries","Fabricators","Machine Works","Forge & Tools","Metalworks","Engineering Industries","Tool Craft","Precision Industries"],
    "IND-03": ["Textiles","Apparel","Fabrics","Garments","Textile Mills","Weaves","Fashion Exports","Textile Industries"],
    "IND-04": ["Pharmaceuticals","Healthcare","Lifesciences","Wellness","Diagnostics","Biotech","Medicare","Health Solutions"],
    "IND-05": ["Consumer Products","Foods","Retail Ventures","Provisions","FMCG Traders","Mart","Consumer Goods","Trading Co"],
    "IND-06": ["Financial Services","Capital","Insurance Brokers","Wealth Advisors","Finserv","Investments","Financial Partners","Capital Advisors"],
    "IND-07": ["Logistics","Freight Carriers","Supply Chain Solutions","Cargo Movers","Transport Co","Freight Lines","Logistics Solutions","Carriers"],
    "IND-08": ["Builders","Realty","Constructions","Infra Developers","Estates","Developers","Realty Ventures","Habitat"],
    "IND-09": ["EduTech","Learning Solutions","Academy","Institute","Skill Labs","Education Ventures","Learning Systems"],
    "IND-10": ["Auto Components","Motors","Auto Industries","Auto Ancillaries","Autoparts","Auto Engineering","Drivetrain Systems"],
    "IND-11": ["Agro Industries","AgriBusiness","Farm Exports","Agro Foods","Agro Ventures","Farm Produce","Agri Solutions"],
    "IND-12": ["Media Networks","Studios","Entertainment","Productions","Media Ventures","Broadcast Networks"],
    "IND-13": ["Power Solutions","Energy Systems","Renewables","Power Infra","Energy Ventures","Green Power"],
    "IND-14": ["E-Retail","Online Ventures","Marketplace","Digital Commerce","E-Commerce Solutions","Online Retail"],
    "IND-15": ["Hospitality Group","Resorts","Travels","Hotels & Inns","Hospitality Ventures","Holidays"],
    "IND-16": ["Telecom Services","Communications","Networks","Teleservices","Telecom Solutions"],
    "IND-17": ["Chemicals","Specialty Chemicals","Industries","Chem Industries","Chemical Works","Polymers"],
    "IND-18": ["Infra Projects","EPC Contractors","Constructions","Infra Ventures","Infrastructure Co","Projects Ltd"],
    "IND-19": ["Consulting","Advisory Services","& Associates","Business Solutions","Consultants","Advisory Partners"],
    "IND-20": ["State Development Corporation","Public Enterprises","Nigam Limited","State Infrastructure Corporation"],
}
TYPE_SUFFIX = {
    "Private Limited": "Private Limited",
    "Public Limited": "Limited",
    "LLP": "LLP",
    "Proprietorship": "",
    "Partnership": "& Co",
    "PSU": "Ltd (PSU)",
}
COMPANY_TYPE_WEIGHTS = [("Private Limited",0.62),("Public Limited",0.06),("LLP",0.14),
                         ("Proprietorship",0.10),("Partnership",0.06),("PSU",0.02)]
def weighted_choice(pairs):
    r = random.random(); c = 0.0
    for v, w in pairs:
        c += w
        if r <= c: return v
    return pairs[-1][0]

SIZE_WEIGHTS = [("Micro",0.18),("Small",0.32),("Mid",0.28),("Large",0.16),("Enterprise",0.06)]
REVBAND_BY_SIZE = {
    "Micro": ["₹0–1 Cr","₹1–5 Cr"], "Small": ["₹1–5 Cr","₹5–25 Cr"],
    "Mid": ["₹5–25 Cr","₹25–100 Cr"], "Large": ["₹25–100 Cr","₹100–1000 Cr"],
    "Enterprise": ["₹100–1000 Cr","₹1000 Cr+"],
}
IND_WEIGHTS = [
    ("IND-01",0.16),("IND-02",0.11),("IND-03",0.05),("IND-04",0.05),("IND-05",0.09),
    ("IND-06",0.05),("IND-07",0.06),("IND-08",0.05),("IND-09",0.04),("IND-10",0.06),
    ("IND-11",0.03),("IND-12",0.02),("IND-13",0.03),("IND-14",0.05),("IND-15",0.03),
    ("IND-16",0.02),("IND-17",0.04),("IND-18",0.03),("IND-19",0.02),("IND-20",0.01),
]

GENERIC_ADJECTIVES = [
    "Bharat","Suvidha","Trishul","Vega","Sanchar","Uday","Shakti","Nova","Prime","Sagar",
    "Mangal","Kiran","Swastik","Unnati","Disha","Vikas","Sahyog","Rachna","Pragati","Sankalp",
    "Anand","Omkar","Vishwas","Sanmarg","Utkarsh","Kalpataru","Siddhi","Ratna","Kirti","Sanchay",
    "Vaibhav","Chaitanya","Sparsh","Nirman","Setu","Kshitij","Aakash","Dhruv","Himalaya","Amrut",
]

used_company_names = set()
def synth_company_name(industry_id, company_type):
    for _ in range(50):
        fn, ln, _ = random.choice(rep_names)  # reuse surname pool, not tied to real reps
        # weight toward surname/city based names (much larger namespace: 60
        # surnames / 23 cities) and away from the thin generic-adjective pool,
        # to avoid template overuse (audit finding 13).
        pattern = random.choices(["surname_sector","city_sector","generic_sector"], weights=[0.45,0.35,0.20])[0]
        word = random.choice(SECTOR_WORDS[industry_id])
        if pattern == "surname_sector":
            base = f"{ln} {word}"
        elif pattern == "city_sector":
            base = f"{random.choice(list(CITY_TIER.keys()))} {word}"
        else:
            adj = random.choice(GENERIC_ADJECTIVES)
            base = f"{adj} {word}"
        suffix = TYPE_SUFFIX[company_type]
        name = f"{base} {suffix}".strip()
        if name not in used_company_names:
            used_company_names.add(name)
            return name
    raise RuntimeError("name space exhausted")

def synth_gstin(state):
    code = STATE_CODE.get(state, "27")
    pan = "".join(random.choices(string.ascii_uppercase, k=5)) + \
          "".join(random.choices(string.digits, k=4)) + \
          random.choice(string.ascii_uppercase)
    return f"{code}{pan}1Z{random.choice(string.digits+string.ascii_uppercase)}"

companies_rows = []
real_sample = random.sample(REAL_COMPANIES, N_REAL)
comp_created_start = date(2022, 6, 1)
used_domains = set()

def make_company(idx, real_tuple):
    cid = f"COMP-{idx:06d}"
    if real_tuple:
        name, ind_name, city = real_tuple
        industry_id = IND_BY_NAME[ind_name]
        real = True
        company_type = REAL_COMPANY_TYPE.get(name, "Private Limited")
        size = REAL_COMPANY_SIZE_HINT.get(name, "Enterprise")
    else:
        industry_id = weighted_choice(IND_WEIGHTS)
        company_type = weighted_choice(COMPANY_TYPE_WEIGHTS)
        if industry_id == "IND-20":
            company_type = "PSU"
        name = synth_company_name(industry_id, company_type)
        real = False
        size = weighted_choice(SIZE_WEIGHTS)
        # Indian company-law realism: a sole proprietorship or partnership firm
        # is not organized at Large/Enterprise headcount scale -- resample from
        # the Micro/Small/Mid band only for these legal types.
        if company_type in ("Proprietorship", "Partnership") and size in ("Large", "Enterprise"):
            size = weighted_choice([("Micro",0.35),("Small",0.45),("Mid",0.20)])
        city = pick_city()

    state, region, tier = CITY_TIER[city]
    rev_band = random.choice(REVBAND_BY_SIZE[size]) if random.random() > 0.1 else ""
    gstin = synth_gstin(state) if random.random() > (0.12 if size in ("Micro","Small") else 0.03) else ""
    pincode = f"{random.randint(100000,899999)}" if random.random() > (0.13 if size in ("Micro","Small") else 0.03) else ""
    domain_base = "".join(ch for ch in name.lower() if ch.isalnum())[:18] or f"company{idx}"
    candidate = f"www.{domain_base}.example"
    if candidate in used_domains:
        candidate = f"www.{domain_base}{idx}.example"  # disambiguate on truncation collision
    used_domains.add(candidate)
    website = candidate if random.random() > 0.08 else ""
    founded = random.randint(1998, 2023) if random.random() > 0.2 else ""
    created_days = random.randint(0, (today - comp_created_start).days)
    created_at = (comp_created_start + timedelta(days=created_days))
    created_dt = datetime.combine(created_at, datetime.min.time()) + timedelta(
        hours=random.randint(9,19), minutes=random.randint(0,59))

    terr_candidates = [t for t,(_,r,_) in [(tid, (n,rg,ti)) for tid,n,rg,ti in [(t[0],t[1],t[2],t[2]) for t in TERRITORIES]]]
    # pick a rep from a territory whose region matches company's region, else any active rep
    same_region_terrs = [t for t, n, r, f in TERRITORIES if r == region]
    candidate_reps = []
    for t in same_region_terrs:
        candidate_reps.extend(rep_by_territory.get(t, []))
    owner = random.choice(candidate_reps) if candidate_reps and random.random() > 0.10 else \
            (random.choice(active_rep_ids) if random.random() > 0.5 else "")

    row = {
        "company_id": cid, "company_name": name, "name_is_real_entity": real,
        "industry_id": industry_id, "sub_industry": pick_sub_industry(cid, industry_id),
        "company_size_band": size, "annual_revenue_band_inr": rev_band,
        "gstin": gstin, "city": city, "state": state, "region": region,
        "pincode": pincode, "website_domain": website, "company_type": company_type,
        "founded_year": founded, "account_owner_rep_id": owner,
        "account_status": "Prospect", "created_at": created_dt.isoformat(sep=" "),
    }
    return row

for i in range(1, N_REAL + 1):
    companies_rows.append(make_company(i, real_sample[i-1]))
for i in range(N_REAL + 1, N_COMPANIES + 1):
    companies_rows.append(make_company(i, None))

random.shuffle(companies_rows)
# re-issue sequential IDs after shuffle so ordering doesn't leak real-vs-synthetic pattern
for i, row in enumerate(companies_rows, start=1):
    row["company_id"] = f"COMP-{i:06d}"

# ---------------------------------------------------------------------------
# Write CSVs
# ---------------------------------------------------------------------------
def write_csv(name, rows, fieldnames):
    path = f"{OUT}/{name}.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return path

write_csv("industries", industries_rows, ["industry_id","industry_name","industry_category","is_active"])
write_csv("territories", territories_rows, ["territory_id","territory_name","region","primary_industry_focus"])
write_csv("departments", departments_rows, ["department_id","department_name","region_focus","created_at"])
write_csv("lead_sources", lead_sources_rows, ["lead_source_id","source_name","source_category"])
write_csv("products", products_rows, ["product_id","product_name","product_category","pricing_model","list_price_inr","is_active"])
write_csv("sales_reps", sales_reps_rows, ["rep_id","full_name","email","phone","department_id","manager_rep_id","role","territory_id","hire_date","is_active","termination_date"])
write_csv("campaigns", campaigns_rows, ["campaign_id","campaign_name","campaign_type","start_date","end_date","budget_inr","target_industry_id","owner_department_id"])
write_csv("companies", companies_rows, ["company_id","company_name","name_is_real_entity","industry_id","sub_industry","company_size_band","annual_revenue_band_inr","gstin","city","state","region","pincode","website_domain","company_type","founded_year","account_owner_rep_id","account_status","created_at"])

print("DONE")
print("industries:", len(industries_rows))
print("territories:", len(territories_rows))
print("departments:", len(departments_rows))
print("lead_sources:", len(lead_sources_rows))
print("products:", len(products_rows))
print("sales_reps:", len(sales_reps_rows))
print("campaigns:", len(campaigns_rows))
print("companies:", len(companies_rows))
