#!/usr/bin/env python3
"""
Indian B2B CRM synthetic dataset — Phase 2: contacts, leads, lead_status_history,
campaign_responses. Built strictly on top of the validated Phase-1 master tables
(no columns/rows in those tables are modified). No opportunities or customers
exist yet, so:
  - lead_source 'Existing Customer Upsell' is excluded (no customers exist).
  - no lead reaches 'Converted' status this phase (that requires an opportunity
    row, which doesn't exist until Phase 3) -- the funnel's terminal "ready"
    state this phase is 'Sales Qualified (SQL)'.
"""
import csv, random, math
from datetime import date, datetime, timedelta

random.seed(20260915)  # same deterministic seed family as Phase 1

IN = "/home/claude/crm_gen/output"
OUT = "/home/claude/crm_gen/output"
TODAY = date(2026, 9, 15)

def read_csv(name):
    with open(f"{IN}/{name}.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

companies = read_csv("companies")
reps = read_csv("sales_reps")
lead_sources = read_csv("lead_sources")
campaigns = read_csv("campaigns")
industries = read_csv("industries")
territories = read_csv("territories")

rep_by_id = {r["rep_id"]: r for r in reps}
terr_by_id = {t["territory_id"]: t for t in territories}
active_sales_reps = [r for r in reps if r["is_active"] == "True"
                      and r["role"] in ("SDR","Account Executive","Senior Account Executive","Sales Manager")]
reps_by_region = {}
for r in active_sales_reps:
    region = terr_by_id[r["territory_id"]]["region"]
    reps_by_region.setdefault(region, []).append(r)

industry_ids = [i["industry_id"] for i in industries]

# ---------------------------------------------------------------------------
# Name pools (kept separate word lists from Phase 1 reps but same style/realism;
# overlap with rep names is fine -- common Indian names repeat across a real
# population -- uniqueness is enforced on email, not on name)
# ---------------------------------------------------------------------------
FIRST_NAMES = [
    "Rohit","Sandeep","Vikas","Ajay","Rakesh","Sunil","Yogesh","Mahesh","Ramesh","Dinesh",
    "Neeraj","Pradeep","Sachin","Vinod","Ravi","Sameer","Tarun","Vishal","Gaurav","Nitin",
    "Meenal","Shraddha","Aparna","Rekha","Geeta","Seema","Reena","Namita","Payal","Bhavna",
    "Farhana","Nasreen","Shabana","Yasmin","Mohammed","Asif","Tahir","Waseem","Khalid","Javed",
    "Harjot","Jasmeet","Ramandeep","Sukhwinder","Daljit","Parminder","Jaspreet","Amarjit","Ranjit","Balwinder",
    "Anjali","Snehal","Madhuri","Sarita","Vaishali","Pratima","Sujata","Rupali","Manisha","Jyoti",
    "Suraj","Abhishek","Nikhil","Saurabh","Rajat","Tushar","Varun","Siddharth","Akash","Rohan",
    "Lalitha","Padma","Vasantha","Jayanthi","Sudha","Uma","Malathi","Vani","Revathi","Anitha",
]
LAST_NAMES = [
    "Rane","Sable","Bhagat","Apte","Ketkar","Gokhale","Phadke","Athavale","Kolhapure","Bapat",
    "Mistry","Wadia","Contractor","Engineer","Daruwala","Elavia","Guzder","Vachha","Bilimoria","Cama",
    "Krishnamurthy","Subramaniam","Ramaswamy","Natarajan","Balasubramanian","Chandrasekaran","Padmanabhan","Vaidyanathan","Sundararajan","Raghunathan",
    "Bose","Sengupta","Dasgupta","Bhattacharya","Chakraborty","Sarkar","Roy","Basu","Lahiri","Chowdhury",
    "Aggarwal","Goyal","Mittal","Goel","Garg","Singhal","Jindal","Bhalla","Arora","Chadha",
    "Fernandes","D'Souza","Pinto","Rodrigues","Lobo","Pereira","Gomes","Rebello","Vaz","Coelho",
]
JOB_TITLE_BY_DEPT = {
    "Procurement": {"Junior":"Purchase Executive","Mid":"Procurement Officer","Senior":"Senior Procurement Officer",
        "Manager":"Procurement Manager","Director":"Head of Procurement","VP":"VP Procurement","C-Level":"Chief Procurement Officer"},
    "IT": {"Junior":"IT Executive","Mid":"System Administrator","Senior":"Senior IT Analyst",
        "Manager":"IT Manager","Director":"IT Director","VP":"VP Technology","C-Level":"Chief Technology Officer"},
    "Finance": {"Junior":"Accounts Executive","Mid":"Finance Analyst","Senior":"Senior Finance Analyst",
        "Manager":"Finance Manager","Director":"Finance Director","VP":"VP Finance","C-Level":"Chief Financial Officer"},
    "Operations": {"Junior":"Operations Executive","Mid":"Operations Coordinator","Senior":"Senior Operations Executive",
        "Manager":"Operations Manager","Director":"Operations Director","VP":"VP Operations","C-Level":"Chief Operating Officer"},
    "HR": {"Junior":"HR Executive","Mid":"HR Generalist","Senior":"Senior HR Executive",
        "Manager":"HR Manager","Director":"HR Director","VP":"VP Human Resources","C-Level":"Chief Human Resources Officer"},
    "Marketing": {"Junior":"Marketing Executive","Mid":"Marketing Associate","Senior":"Senior Marketing Executive",
        "Manager":"Marketing Manager","Director":"Marketing Director","VP":"VP Marketing","C-Level":"Chief Marketing Officer"},
    "Sales": {"Junior":"Sales Executive","Mid":"Business Development Executive","Senior":"Senior Sales Executive",
        "Manager":"Sales Manager","Director":"Sales Director","VP":"VP Sales","C-Level":"Chief Revenue Officer"},
    "Founder/Owner": {"Junior":"Proprietor","Mid":"Partner","Senior":"Managing Partner",
        "Manager":"Director","Director":"Managing Director","VP":"Managing Director","C-Level":"Founder & CEO"},
}
DEPTS = list(JOB_TITLE_BY_DEPT.keys())
SENIORITY = ["Junior","Mid","Senior","Manager","Director","VP","C-Level"]

def unique_person():
    return random.choice(FIRST_NAMES), random.choice(LAST_NAMES)

# ---------------------------------------------------------------------------
# Company sizing helpers
# ---------------------------------------------------------------------------
SIZE_LEAD_PROB = {"Micro":0.25,"Small":0.40,"Mid":0.55,"Large":0.70,"Enterprise":0.80}
SIZE_CONTACT_CAP = {"Micro":1,"Small":2,"Mid":2,"Large":3,"Enterprise":4}
SIZE_CYCLE_MULT = {"Micro":0.75,"Small":0.85,"Mid":1.0,"Large":1.3,"Enterprise":1.6}
IND_CYCLE_MULT = {  # longer cycles for capital/infra-heavy verticals, shorter for retail/e-comm/edtech
    "IND-02":1.4,"IND-08":1.4,"IND-18":1.5,"IND-04":1.2,"IND-06":1.2,"IND-10":1.2,
    "IND-01":1.0,"IND-19":1.0,"IND-16":1.0,"IND-13":1.3,"IND-17":1.2,
    "IND-05":0.8,"IND-14":0.7,"IND-09":0.8,"IND-15":0.8,"IND-12":0.9,"IND-11":1.1,"IND-07":1.0,
    "IND-03":1.0,"IND-20":1.5,
}
LEAD_COUNT_WEIGHTS = [(1,0.55),(2,0.25),(3,0.12),(4,0.05),(5,0.02),(6,0.008),(7,0.0015),(8,0.0005)]

def weighted_choice(pairs):
    r = random.random(); c = 0.0
    for v, w in pairs:
        c += w
        if r <= c: return v
    return pairs[-1][0]

MONTH_WEIGHT = {1:1.3,2:1.3,3:1.5,4:0.9,5:0.9,6:0.95,7:1.0,8:1.0,9:1.05,10:0.75,11:0.7,12:0.75}
def weighted_date_in_range(start: date, end: date):
    span = (end - start).days
    if span <= 0:
        return start
    for _ in range(30):
        offset = random.randint(0, span)
        d = start + timedelta(days=offset)
        if random.random() < MONTH_WEIGHT.get(d.month,1.0) / 1.5:
            return d
    return start + timedelta(days=random.randint(0, span))

# ---------------------------------------------------------------------------
# Select companies that will have lead activity
# ---------------------------------------------------------------------------
comp_created = {c["company_id"]: datetime.strptime(c["created_at"], "%Y-%m-%d %H:%M:%S").date() for c in companies}
selected = []
for c in companies:
    p = SIZE_LEAD_PROB[c["company_size_band"]]
    if c["name_is_real_entity"] == "True":
        p = min(0.95, p * 1.5)
    if random.random() < p:
        n_leads = weighted_choice(LEAD_COUNT_WEIGHTS)
        selected.append((c, n_leads))

# ---------------------------------------------------------------------------
# Generate contacts + leads together per selected company
# ---------------------------------------------------------------------------
contacts_rows = []
leads_rows = []
lead_status_history_rows = []
contact_idx = 0
lead_idx = 0
lsh_idx = 0
used_contact_emails = set()

def make_domain(company):
    if company["website_domain"]:
        return company["website_domain"].replace("www.", "")
    base = "".join(ch for ch in company["company_name"].lower() if ch.isalnum())[:16] or "biz"
    return f"{base}.example"

active_campaigns_by_type = {}
for camp in campaigns:
    active_campaigns_by_type.setdefault(camp["campaign_type"], []).append(camp)

SOURCE_TO_CAMPAIGN_TYPE = {
    "Webinar": "Webinar", "Trade Show/Exhibition": "Trade Show", "Google Ads": "Paid Search",
    "Cold Email": "Email", "LinkedIn Outbound": "Social Media", "Partner Channel": "Partner Event",
}
LEAD_SOURCE_WEIGHTS = [
    ("SRC-01",0.20),("SRC-02",0.08),("SRC-03",0.10),("SRC-04",0.07),("SRC-05",0.12),
    ("SRC-06",0.08),("SRC-07",0.09),("SRC-08",0.10),("SRC-09",0.08),("SRC-10",0.05),
    ("SRC-11",0.06),  # SRC-12 Existing Customer Upsell excluded (0 weight -- no customers exist yet)
]
src_by_id = {s["lead_source_id"]: s for s in lead_sources}

DISQ_REASON_WEIGHTS_EARLY = [("Invalid Contact",1.0)]  # exit at New
DISQ_REASON_WEIGHTS_MID = [("Unresponsive",0.5),("Bad Timing",0.25),("No Need",0.15),("Budget",0.10)]
DISQ_REASON_WEIGHTS_LATE = [("Budget",0.30),("No Authority",0.25),("No Need",0.20),("Competitor Chosen",0.15),("Bad Timing",0.10)]
DEAD_REASONS = {"Unresponsive","Invalid Contact","Bad Timing"}

def pick_campaign(source_id, created_dt):
    ctype = SOURCE_TO_CAMPAIGN_TYPE.get(src_by_id[source_id]["source_name"])
    if not ctype:
        return None
    candidates = active_campaigns_by_type.get(ctype, [])
    valid = []
    for camp in candidates:
        cstart = datetime.strptime(camp["start_date"], "%Y-%m-%d").date()
        cend = datetime.strptime(camp["end_date"], "%Y-%m-%d").date() if camp["end_date"] else (TODAY)
        if cstart <= created_dt <= cend + timedelta(days=14):
            valid.append(camp)
    if not valid:
        return None
    return random.choice(valid)

def pick_rep(company, created_dt):
    region = company["region"]
    owner = company["account_owner_rep_id"]
    if owner and owner in rep_by_id:
        r = rep_by_id[owner]
        if r["is_active"] == "True" and r["role"] in ("SDR","Account Executive","Senior Account Executive","Sales Manager") \
           and datetime.strptime(r["hire_date"], "%Y-%m-%d").date() <= created_dt and random.random() < 0.70:
            return owner
    pool = [r for r in reps_by_region.get(region, []) if datetime.strptime(r["hire_date"], "%Y-%m-%d").date() <= created_dt]
    if not pool:
        pool = [r for r in active_sales_reps if datetime.strptime(r["hire_date"], "%Y-%m-%d").date() <= created_dt]
    if not pool:
        return ""
    return random.choice(pool)["rep_id"]

for company, n_leads in selected:
    cstart = comp_created[company["company_id"]]
    n_contacts = min(SIZE_CONTACT_CAP[company["company_size_band"]], max(1, n_leads))
    # build contact skeletons
    company_contacts = []
    domain = make_domain(company)
    for ci in range(n_contacts):
        fn, ln = unique_person()
        # small/micro companies: owner/founder-style contact more likely (esp. first contact)
        if company["company_size_band"] in ("Micro","Small") and ci == 0 and random.random() < 0.55:
            dept = "Founder/Owner"
            seniority = random.choice(["Senior","Director","C-Level"])
        else:
            dept = random.choice(DEPTS)
            seniority = weighted_choice([("Junior",0.10),("Mid",0.25),("Senior",0.25),
                                          ("Manager",0.22),("Director",0.12),("VP",0.04),("C-Level",0.02)])
        job_title = JOB_TITLE_BY_DEPT[dept][seniority]
        is_dm = seniority in ("Director","VP","C-Level") or dept == "Founder/Owner" or \
                (seniority == "Manager" and random.random() < 0.5)
        contact_idx += 1
        cid = f"CONT-{contact_idx:06d}"
        # Corporate email systems and LinkedIn slugs strip apostrophes/punctuation
        # from names (e.g. "D'Souza" -> "dsouza"); build the local-part from an
        # alnum-only version of each name component so real-looking surnames like
        # D'Souza never leak an unrealistic apostrophe into an email address.
        fn_e = "".join(ch for ch in fn.lower() if ch.isalnum())
        ln_e = "".join(ch for ch in ln.lower() if ch.isalnum())
        for attempt in range(20):
            email = f"{fn_e}.{ln_e}{contact_idx}@{domain}"
            if email not in used_contact_emails:
                used_contact_emails.add(email); break
        phone = f"+91-{random.choice([7,8,9])}{random.randint(100000000,999999999)}" if random.random() > 0.14 else ""
        linkedin = f"linkedin.com/in/{fn_e}-{ln_e}-{contact_idx}" if random.random() > 0.55 else ""
        row = {
            "contact_id": cid, "company_id": company["company_id"], "full_name": f"{fn} {ln}",
            "job_title": job_title, "seniority_level": seniority, "department": dept,
            "email": email, "phone": phone, "is_primary_contact": ci == 0,
            "linkedin_handle": linkedin, "is_decision_maker": is_dm, "created_at": "",  # backfilled below
        }
        company_contacts.append(row)

    # generate lead creation dates for this company (sorted). Leads must start
    # at least 1 full calendar day after the company record was created, so no
    # same-day random-time ordering ambiguity is possible against companies.created_at.
    range_start = max(cstart, date(2022,7,1)) + timedelta(days=1)
    lead_created_dates = sorted(weighted_date_in_range(range_start, TODAY) for _ in range(n_leads))

    contact_min_lead_date = {c["contact_id"]: None for c in company_contacts}
    prior_leads_at_company = []

    for created_dt in lead_created_dates:
        # weight contact selection toward earlier (primary) contacts somewhat
        weights = [0.5 if c["is_primary_contact"] else 0.5/max(1,n_contacts-1) for c in company_contacts]
        tot = sum(weights)
        r = random.random()*tot; cum=0.0; chosen = company_contacts[0]
        for c,w in zip(company_contacts, weights):
            cum += w
            if r <= cum: chosen = c; break
        if contact_min_lead_date[chosen["contact_id"]] is None or created_dt < contact_min_lead_date[chosen["contact_id"]]:
            contact_min_lead_date[chosen["contact_id"]] = created_dt

        source_id = weighted_choice(LEAD_SOURCE_WEIGHTS)
        campaign = pick_campaign(source_id, created_dt)
        rep_id = pick_rep(company, created_dt)

        lead_idx += 1
        lead_id = f"LEAD-{lead_idx:06d}"

        cycle_mult = SIZE_CYCLE_MULT[company["company_size_band"]] * IND_CYCLE_MULT.get(company["industry_id"], 1.0)

        # --- simulate the funnel walk ---
        history = [("", "New", created_dt)]
        cur_dt = created_dt
        status = "New"
        first_contacted_at = None
        qualified_at = None
        disq_reason = ""

        def dwell(lo, hi):
            return max(1, int(round(random.randint(lo, hi) * cycle_mult)))

        stopped = False
        # New -> exit / stall / advance
        if not stopped:
            roll = random.random()
            if roll < 0.05:
                status = "Disqualified"; disq_reason = "Invalid Contact"
                cur_dt = cur_dt + timedelta(days=dwell(1,3))
                if cur_dt > TODAY: cur_dt = TODAY
                history.append(("New","Disqualified",cur_dt)); stopped = True
            elif roll < 0.15:
                stopped = True  # stall at New
            else:
                step = timedelta(days=dwell(0,3))
                if cur_dt + step > TODAY:
                    stopped = True
                else:
                    cur_dt += step; status = "Contacted"; first_contacted_at = cur_dt
                    history.append(("New","Contacted",cur_dt))
        if not stopped and status == "Contacted" and cur_dt < TODAY:
            roll = random.random()
            if roll < 0.08:
                status = "Dead"; disq_reason = weighted_choice(DISQ_REASON_WEIGHTS_MID)
                step = timedelta(days=dwell(2,7))
                cur_dt = min(cur_dt+step, TODAY); history.append(("Contacted","Dead",cur_dt)); stopped=True
            elif roll < 0.12:
                status = "Disqualified"; disq_reason = weighted_choice(DISQ_REASON_WEIGHTS_MID)
                step = timedelta(days=dwell(2,7))
                cur_dt = min(cur_dt+step, TODAY); history.append(("Contacted","Disqualified",cur_dt)); stopped=True
            elif roll < 0.22:
                stopped = True
            else:
                step = timedelta(days=dwell(1,7))
                if cur_dt + step > TODAY:
                    stopped = True
                else:
                    cur_dt += step; status = "Qualifying"
                    history.append(("Contacted","Qualifying",cur_dt))
        if not stopped and status == "Qualifying" and cur_dt < TODAY:
            roll = random.random()
            if roll < 0.10:
                status = "Disqualified"; disq_reason = weighted_choice(DISQ_REASON_WEIGHTS_MID)
                step = timedelta(days=dwell(3,10))
                cur_dt = min(cur_dt+step, TODAY); history.append(("Qualifying","Disqualified",cur_dt)); stopped=True
            elif roll < 0.16:
                status = "Nurture"
                step = timedelta(days=dwell(3,10))
                cur_dt = min(cur_dt+step, TODAY); history.append(("Qualifying","Nurture",cur_dt)); stopped=True
            elif roll < 0.28:
                stopped = True
            else:
                step = timedelta(days=dwell(3,14))
                if cur_dt + step > TODAY:
                    stopped = True
                else:
                    cur_dt += step; status = "Qualified (MQL)"; qualified_at = cur_dt
                    history.append(("Qualifying","Qualified (MQL)",cur_dt))
        if not stopped and status == "Qualified (MQL)" and cur_dt < TODAY:
            roll = random.random()
            if roll < 0.14:
                status = "Disqualified"; disq_reason = weighted_choice(DISQ_REASON_WEIGHTS_LATE)
                step = timedelta(days=dwell(5,15))
                cur_dt = min(cur_dt+step, TODAY); history.append(("Qualified (MQL)","Disqualified",cur_dt)); stopped=True
            elif roll < 0.20:
                status = "Nurture"
                step = timedelta(days=dwell(5,15))
                cur_dt = min(cur_dt+step, TODAY); history.append(("Qualified (MQL)","Nurture",cur_dt)); stopped=True
            elif roll < 0.32:
                stopped = True
            else:
                step = timedelta(days=dwell(5,21))
                if cur_dt + step > TODAY:
                    stopped = True
                else:
                    cur_dt += step; status = "Sales Qualified (SQL)"
                    history.append(("Qualified (MQL)","Sales Qualified (SQL)",cur_dt))
        if not stopped and status == "Sales Qualified (SQL)" and cur_dt < TODAY:
            roll = random.random()
            if roll < 0.15:
                status = "Disqualified" if random.random() < 0.6 else "Dead"
                disq_reason = weighted_choice(DISQ_REASON_WEIGHTS_LATE) if status=="Disqualified" else weighted_choice(DISQ_REASON_WEIGHTS_MID)
                step = timedelta(days=dwell(5,20))
                cur_dt = min(cur_dt+step, TODAY); history.append(("Sales Qualified (SQL)",status,cur_dt)); stopped=True
            # else: remains SQL, stalled awaiting opportunity creation (Phase 3)

        # qualified_at must be set if the lead ever reached MQL or beyond, even if it later moved on
        if qualified_at is None:
            for (f,t,d) in history:
                if t == "Qualified (MQL)":
                    qualified_at = d
        if first_contacted_at is None:
            for (f,t,d) in history:
                if t == "Contacted":
                    first_contacted_at = d

        # A lead still sitting untouched at New (never contacted) may not yet be
        # triaged to a rep -- realistic unassigned-queue backlog. Only applies
        # when the lead never advanced past New.
        if len(history) == 1 and random.random() < 0.35:
            rep_id = ""

        for i, (f,t,d) in enumerate(history):
            lsh_idx += 1
            # the initial "New" entry represents lead capture, not a rep action --
            # system-generated, so changed_by_rep_id is null there regardless of
            # whether/which rep is later assigned.
            changed_by = "" if i == 0 else rep_id
            lead_status_history_rows.append({
                "history_id": f"LSH-{lsh_idx:07d}", "lead_id": lead_id,
                "status_from": f, "status_to": t,
                "changed_at": datetime.combine(d, datetime.min.time()).replace(
                    hour=random.randint(9,19), minute=random.randint(0,59)).isoformat(sep=" "),
                "changed_by_rep_id": changed_by,
            })

        # estimated_budget: MNAR -- missing more often early-stage / junior contact
        contact_seniority = chosen["seniority_level"]
        early_stage = status in ("New","Contacted")
        miss_p = 0.60 if (early_stage or contact_seniority in ("Junior","Mid")) else 0.15
        est_budget = "" if random.random() < miss_p else int(round(random.uniform(50000, 3500000), -3))

        industry_interest_roll = random.random()
        if industry_interest_roll < 0.70:
            industry_interest_id = company["industry_id"]
        elif industry_interest_roll < 0.85:
            industry_interest_id = ""
        else:
            industry_interest_id = random.choice(industry_ids)

        is_dup = ""
        if prior_leads_at_company and random.random() < 0.04:
            is_dup = random.choice(prior_leads_at_company)

        leads_rows.append({
            "lead_id": lead_id, "company_id": company["company_id"], "contact_id": chosen["contact_id"],
            "lead_source_id": source_id, "campaign_id": campaign["campaign_id"] if campaign else "",
            "assigned_rep_id": rep_id, "lead_status": status, "disqualification_reason": disq_reason,
            "industry_interest_id": industry_interest_id, "estimated_budget_inr": est_budget,
            "company_size_at_lead_time": company["company_size_band"],
            "created_at": datetime.combine(created_dt, datetime.min.time()).replace(
                hour=random.randint(9,19), minute=random.randint(0,59)).isoformat(sep=" "),
            "first_contacted_at": datetime.combine(first_contacted_at, datetime.min.time()).replace(
                hour=random.randint(9,19), minute=random.randint(0,59)).isoformat(sep=" ") if first_contacted_at else "",
            "qualified_at": datetime.combine(qualified_at, datetime.min.time()).replace(
                hour=random.randint(9,19), minute=random.randint(0,59)).isoformat(sep=" ") if qualified_at else "",
            "converted_at": "",  # never set this phase -- no opportunities exist yet
            "is_duplicate_of_lead_id": is_dup,
        })
        prior_leads_at_company.append(lead_id)

    for c in company_contacts:
        first_lead_dt = contact_min_lead_date[c["contact_id"]]
        # contacts must be strictly earlier than the first lead that references
        # them, and strictly later than the company record -- offset >=1 day
        # (never 0) so no same-day random-time ambiguity is possible either way.
        offset = timedelta(days=random.randint(1,3))
        created = max(cstart + timedelta(days=1), (first_lead_dt - offset)) if first_lead_dt else cstart + timedelta(days=1)
        if first_lead_dt and created >= first_lead_dt:
            created = first_lead_dt - timedelta(days=1)
        if created < cstart + timedelta(days=1):
            created = cstart + timedelta(days=1)
        # contact time-of-day drawn from an earlier band (6-8) than leads (9-19)
        # as a deterministic safety net for the rare case where clamping still
        # leaves a contact on the same calendar date as its earliest lead.
        c["created_at"] = datetime.combine(created, datetime.min.time()).replace(
            hour=random.randint(6,8), minute=random.randint(0,59)).isoformat(sep=" ")
        c["is_primary_contact"] = c["is_primary_contact"]
        c["is_decision_maker"] = c["is_decision_maker"]
        contacts_rows.append(c)

# ---------------------------------------------------------------------------
# campaign_responses: one per campaign-linked lead (converted-intent response)
# plus extra non-converting responses (opened/clicked/no-response) from the
# same contact pool, so funnel/campaign metrics have a realistic wide top.
# ---------------------------------------------------------------------------
campaign_responses_rows = []
resp_idx = 0
leads_by_campaign = {}
for l in leads_rows:
    if l["campaign_id"]:
        leads_by_campaign.setdefault(l["campaign_id"], []).append(l)

RESPONSE_TYPE_CONVERTING = {"Webinar":"Registered","Trade Show":"Attended","Paid Search":"Requested Demo",
                             "Email":"Requested Demo","Social Media":"Requested Demo","Partner Event":"Attended"}
RESPONSE_TYPE_NONCONVERTING_WEIGHTS = [("Opened",0.40),("Clicked",0.28),("Downloaded Content",0.14),
                                        ("No Response",0.13),("Registered",0.05)]

contacts_by_company = {}
for c in contacts_rows:
    contacts_by_company.setdefault(c["company_id"], []).append(c)
all_contacts_flat = contacts_rows

for camp in campaigns:
    cid = camp["campaign_id"]
    ctype = camp["campaign_type"]
    linked_leads = leads_by_campaign.get(cid, [])
    cstart = datetime.strptime(camp["start_date"], "%Y-%m-%d").date()
    cend = datetime.strptime(camp["end_date"], "%Y-%m-%d").date() if camp["end_date"] else TODAY
    for l in linked_leads:
        resp_idx += 1
        lead_created_date = datetime.strptime(l["created_at"], "%Y-%m-%d %H:%M:%S").date()
        resp_date = lead_created_date - timedelta(days=random.randint(0,2))
        resp_date = max(resp_date, cstart)
        campaign_responses_rows.append({
            "response_id": f"CRSP-{resp_idx:07d}", "campaign_id": cid, "contact_id": l["contact_id"],
            "response_type": RESPONSE_TYPE_CONVERTING.get(ctype,"Requested Demo"),
            "response_date": datetime.combine(resp_date, datetime.min.time()).replace(
                hour=random.randint(9,19), minute=random.randint(0,59)).isoformat(sep=" "),
            "resulted_in_lead_id": l["lead_id"],
        })
    # extra non-converting responses: ~1.3x the converting count, min 2 if campaign has any linked leads,
    # else a small trickle for campaigns that generated no lead at all (still had some engagement)
    n_extra = max(2, int(round(len(linked_leads) * 1.3))) if linked_leads else random.randint(0,3)
    span = (cend - cstart).days
    if span <= 0 or (n_extra == 0):
        continue
    for _ in range(n_extra):
        contact = random.choice(all_contacts_flat)
        contact_created = datetime.strptime(contact["created_at"], "%Y-%m-%d %H:%M:%S").date()
        lo = max(cstart, contact_created)
        if lo > cend:
            continue
        resp_date = lo + timedelta(days=random.randint(0, (cend-lo).days))
        resp_idx += 1
        campaign_responses_rows.append({
            "response_id": f"CRSP-{resp_idx:07d}", "campaign_id": cid, "contact_id": contact["contact_id"],
            "response_type": weighted_choice(RESPONSE_TYPE_NONCONVERTING_WEIGHTS),
            "response_date": datetime.combine(resp_date, datetime.min.time()).replace(
                hour=random.randint(9,19), minute=random.randint(0,59)).isoformat(sep=" "),
            "resulted_in_lead_id": "",
        })

# ---------------------------------------------------------------------------
# Write CSVs
# ---------------------------------------------------------------------------
def write_csv(name, rows, fieldnames):
    with open(f"{OUT}/{name}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)

write_csv("contacts", contacts_rows, ["contact_id","company_id","full_name","job_title","seniority_level",
    "department","email","phone","is_primary_contact","linkedin_handle","is_decision_maker","created_at"])
write_csv("leads", leads_rows, ["lead_id","company_id","contact_id","lead_source_id","campaign_id",
    "assigned_rep_id","lead_status","disqualification_reason","industry_interest_id","estimated_budget_inr",
    "company_size_at_lead_time","created_at","first_contacted_at","qualified_at","converted_at","is_duplicate_of_lead_id"])
write_csv("lead_status_history", lead_status_history_rows, ["history_id","lead_id","status_from","status_to","changed_at","changed_by_rep_id"])
write_csv("campaign_responses", campaign_responses_rows, ["response_id","campaign_id","contact_id","response_type","response_date","resulted_in_lead_id"])

print("companies with lead activity:", len(selected), "/", len(companies))
print("contacts:", len(contacts_rows))
print("leads:", len(leads_rows))
print("lead_status_history:", len(lead_status_history_rows))
print("campaign_responses:", len(campaign_responses_rows))
