#!/usr/bin/env python3
"""
Indian B2B CRM synthetic dataset — Phase 3: opportunities, opportunity_products,
opportunity_stage_history, customers, customer_transactions, customer_support_cases.

Built strictly on top of the validated Phase-1/Phase-2 tables. Because opportunities
now exist, this phase ALSO back-fills the subset of Phase-2 leads that produced an
opportunity to lead_status='Converted' (previously withheld exactly for this reason),
and flips companies.account_status to 'Active Customer' for companies that became
customers. Both are declared and delivered as updated files, not silent edits.

customer_status intentionally excludes 'Churned' this phase -- that status requires
a customer_churn_events row (a table not yet generated), mirroring the same
no-status-without-its-supporting-table rule used for leads in Phase 2.
"""
import csv, random
from datetime import date, datetime, timedelta

random.seed(20260915)

IO = "/home/claude/crm_gen/output"
TODAY = date(2026, 9, 15)

def read_csv(name):
    with open(f"{IO}/{name}.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def write_csv(name, rows, fieldnames):
    with open(f"{IO}/{name}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)

companies = read_csv("companies")
contacts = read_csv("contacts")
leads = read_csv("leads")
lsh = read_csv("lead_status_history")
reps = read_csv("sales_reps")
products = read_csv("products")
industries = read_csv("industries")
territories = read_csv("territories")

comp_by_id = {c["company_id"]: c for c in companies}
contact_by_id = {c["contact_id"]: c for c in contacts}
rep_by_id = {r["rep_id"]: r for r in reps}
terr_by_id = {t["territory_id"]: t for t in territories}
prod_by_id = {p["product_id"]: p for p in products}

active_sales_reps = [r for r in reps if r["is_active"] == "True"
                      and r["role"] in ("SDR","Account Executive","Senior Account Executive","Sales Manager")]
active_csms = [r for r in reps if r["is_active"] == "True" and r["role"] == "Customer Success Manager"]
reps_by_region = {}
for r in active_sales_reps:
    reps_by_region.setdefault(terr_by_id[r["territory_id"]]["region"], []).append(r)
csms_by_region = {}
for r in active_csms:
    csms_by_region.setdefault(terr_by_id[r["territory_id"]]["region"], []).append(r)

def weighted_choice(pairs):
    r = random.random(); c = 0.0
    for v, w in pairs:
        c += w
        if r <= c: return v
    return pairs[-1][0]

def parse_dt(s):
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S") if s else None

# The lead's own "qualified_at" column tracks the MQL milestone, not the later
# Sales-Qualified (SQL) milestone -- the SQL transition's own dwell time (from
# the Phase-2 funnel walk) can land many days after qualified_at. Opportunities
# (and their derived "Converted" timestamp) must be anchored to when the lead
# actually reached SQL, never to the earlier MQL date, or converted_at can end
# up earlier than the lead's own SQL-transition history row.
SQL_REACHED_AT = {}
for r in lsh:
    if r["status_to"] == "Sales Qualified (SQL)":
        SQL_REACHED_AT[r["lead_id"]] = parse_dt(r["changed_at"])

SIZE_CYCLE_MULT = {"Micro":0.8,"Small":0.9,"Mid":1.0,"Large":1.35,"Enterprise":1.7}
IND_CYCLE_MULT = {
    "IND-02":1.4,"IND-08":1.4,"IND-18":1.5,"IND-04":1.2,"IND-06":1.2,"IND-10":1.2,
    "IND-01":1.0,"IND-19":1.0,"IND-16":1.0,"IND-13":1.3,"IND-17":1.2,
    "IND-05":0.8,"IND-14":0.7,"IND-09":0.8,"IND-15":0.8,"IND-12":0.9,"IND-11":1.1,"IND-07":1.0,
    "IND-03":1.0,"IND-20":1.5,
}
INDUSTRY_FIT = {  # CRM product/market fit modifier feeding the quality index
    "IND-01":0.08,"IND-06":0.08,"IND-19":0.08,"IND-14":0.06,"IND-09":0.05,"IND-16":0.05,
    "IND-04":0.03,"IND-05":0.03,"IND-15":0.02,"IND-10":0.02,"IND-02":0.0,"IND-03":0.0,
    "IND-07":0.0,"IND-08":-0.02,"IND-12":0.0,"IND-13":-0.02,"IND-17":-0.02,"IND-18":-0.03,
    "IND-11":-0.03,"IND-20":-0.05,
}
SOURCE_QUALITY = {
    "SRC-03":0.15, "SRC-07":0.12, "SRC-12":0.15,  # Referral, Partner, Existing Upsell(unused Phase2)
    "SRC-02":0.08, "SRC-11":0.07, "SRC-08":0.06,   # Inbound Call, Webinar, IndiaMART
    "SRC-01":0.05,"SRC-09":0.05,"SRC-10":0.05,     # Website, Google Ads, Organic
    "SRC-04":0.02,"SRC-05":0.02,"SRC-06":0.0,      # Trade Show, LinkedIn Outbound, Cold Email
}
SIZE_QUALITY = {"Micro":0.0,"Small":0.03,"Mid":0.08,"Large":0.08,"Enterprise":0.06}

def lead_quality_index(lead, contact, company):
    q = 0.35
    q += SOURCE_QUALITY.get(lead["lead_source_id"], 0.0)
    if contact["is_decision_maker"] == "True": q += 0.15
    if contact["seniority_level"] in ("Director","VP","C-Level"): q += 0.08
    if lead["estimated_budget_inr"]:
        q += 0.10
        if float(lead["estimated_budget_inr"]) > 1_000_000: q += 0.05
    q += SIZE_QUALITY.get(company["company_size_band"], 0.0)
    q += INDUSTRY_FIT.get(company["industry_id"], 0.0)
    q += 0.05 if lead["assigned_rep_id"] else -0.10
    return max(0.05, min(0.95, q))

STAGE_ORDER = ["Qualification","Discovery","Solution Fit","Proposal","Negotiation"]
STAGE_PROB_BAND = {
    "Qualification": (10,20), "Discovery": (20,35), "Solution Fit": (35,50),
    "Proposal": (50,70), "Negotiation": (70,85), "Closed Won": (100,100), "Closed Lost": (0,0),
}
# (advance_base, lost_base, stall) -- advance/lost shift with quality index q, stall is fixed "deal went quiet"
STAGE_OUTCOME = {
    # (advance_base, lost_base, stall) -- SQL-qualified leads are already deep-funnel,
    # so late-stage advance rates run high (design-doc funnel: ~65-75% eventual win
    # rate among opportunities that reach Negotiation).
    "Qualification": (0.72, 0.16, 0.12),
    "Discovery":     (0.74, 0.14, 0.12),
    "Solution Fit":  (0.76, 0.12, 0.12),
    "Proposal":      (0.78, 0.12, 0.10),
    "Negotiation":   (0.80, 0.12, 0.08),  # "advance" here means Closed Won
}
EARLY_LOSS_REASONS = [("No Budget",0.30),("Timing",0.25),("No Decision",0.20),("Lost Contact",0.15),("Feature Gap",0.10)]
LATE_LOSS_REASONS = [("Price",0.28),("Competitor",0.27),("No Budget",0.15),("Feature Gap",0.15),("No Decision",0.10),("Timing",0.05)]
COMPETITOR_TAGS = ["Competitor A (Regional CRM)","Competitor B (International CRM)","Competitor C (Point Solution)","In-house/Spreadsheet Status Quo"]

DWELL_BAND = {"Qualification":(3,10),"Discovery":(5,15),"Solution Fit":(7,20),"Proposal":(7,21),"Negotiation":(5,18)}

def dwell(stage, mult):
    lo, hi = DWELL_BAND[stage]
    return max(1, int(round(random.randint(lo,hi) * mult)))

def simulate_opportunity(created_dt: date, cycle_mult: float, q: float):
    """Returns (final_stage, close_outcome, loss_reason, actual_close_date, stage_history)
    stage_history: list of (from, to, date)"""
    history = [("", "Qualification", created_dt)]
    cur_dt = created_dt
    stage_i = 0
    outcome = None
    loss_reason = ""
    actual_close = None
    while stage_i < len(STAGE_ORDER):
        stage = STAGE_ORDER[stage_i]
        if cur_dt >= TODAY:
            break  # stalls open, out of runway
        adv_base, lost_base, stall = STAGE_OUTCOME[stage]
        # shift advance/lost by quality index, keep stall fixed, renormalize
        adv = adv_base + 0.20*(q-0.5)
        lost = lost_base - 0.15*(q-0.5)
        adv = max(0.05, adv); lost = max(0.03, lost)
        tot_move = adv + lost
        remaining = 1 - stall
        adv_p = stall + (adv/tot_move)*remaining if tot_move>0 else stall
        # roll
        r = random.random()
        step = timedelta(days=dwell(stage, cycle_mult))
        next_dt = cur_dt + step
        if r < stall:
            break  # stalls open at this stage (deal gone quiet)
        elif r < stall + (remaining * adv/tot_move):
            # advance (or win, if this was Negotiation)
            if next_dt > TODAY:
                break  # not enough runway -- stays open at current stage
            cur_dt = next_dt
            if stage == "Negotiation":
                outcome = "Won"; actual_close = cur_dt
                history.append((stage, "Closed Won", cur_dt))
                stage_i = len(STAGE_ORDER)
                break
            else:
                nxt_stage = STAGE_ORDER[stage_i+1]
                history.append((stage, nxt_stage, cur_dt))
                stage_i += 1
        else:
            # lost
            if next_dt > TODAY: next_dt = TODAY
            cur_dt = next_dt
            outcome = "Lost"
            loss_reason = weighted_choice(EARLY_LOSS_REASONS if stage in ("Qualification","Discovery") else LATE_LOSS_REASONS)
            actual_close = cur_dt
            history.append((stage, "Closed Lost", cur_dt))
            break
    final_stage = history[-1][1]
    return final_stage, outcome, loss_reason, actual_close, history

# ---------------------------------------------------------------------------
# Product bundle per opportunity, sized to company
# ---------------------------------------------------------------------------
BASE_PRODUCT_BY_SIZE = {"Micro":"PROD-001","Small":"PROD-001","Mid":"PROD-002","Large":"PROD-002","Enterprise":"PROD-003"}
ADDON_POOL = ["PROD-004","PROD-005","PROD-006","PROD-007","PROD-008","PROD-009","PROD-011","PROD-013","PROD-014","PROD-016","PROD-018"]

def build_products_for_opportunity(company):
    base = BASE_PRODUCT_BY_SIZE[company["company_size_band"]]
    chosen = [base]
    n_extra = weighted_choice([(0,0.35),(1,0.35),(2,0.22),(3,0.08)])
    pool = [p for p in ADDON_POOL if p != base]
    chosen += random.sample(pool, min(n_extra, len(pool)))
    lines = []
    for pid in chosen:
        p = prod_by_id[pid]
        qty = 1
        if p["pricing_model"] == "Usage-based":
            qty = random.randint(1,5)
        unit_price = float(p["list_price_inr"])
        discount = weighted_choice([(0,0.35),(5,0.30),(10,0.20),(15,0.10),(20,0.05)])
        line_total = round(qty * unit_price * (1 - discount/100), 2)
        lines.append({"product_id": pid, "quantity": qty, "unit_price_inr": unit_price,
                       "discount_pct": discount, "line_total_inr": line_total})
    return lines

# ---------------------------------------------------------------------------
# Pass 1: build opportunities from Sales Qualified (SQL) leads
# ---------------------------------------------------------------------------
opportunities_rows = []
opportunity_products_rows = []
opp_stage_history_rows = []
opp_idx = 0
oppr_idx = 0
osh_idx = 0
converted_lead_ids = []  # for Phase-2 backfill

sql_leads = [l for l in leads if l["lead_status"] == "Sales Qualified (SQL)"]

def pick_owner_rep(company, created_dt, fallback_rep_id):
    if fallback_rep_id and fallback_rep_id in rep_by_id:
        r = rep_by_id[fallback_rep_id]
        if r["is_active"]=="True" and datetime.strptime(r["hire_date"],"%Y-%m-%d").date() <= created_dt:
            return fallback_rep_id
    region = company["region"]
    pool = [r for r in reps_by_region.get(region, []) if datetime.strptime(r["hire_date"],"%Y-%m-%d").date() <= created_dt]
    if not pool:
        pool = [r for r in active_sales_reps if datetime.strptime(r["hire_date"],"%Y-%m-%d").date() <= created_dt]
    return random.choice(pool)["rep_id"] if pool else ""

for lead in sql_leads:
    company = comp_by_id[lead["company_id"]]
    contact = contact_by_id[lead["contact_id"]]
    q = lead_quality_index(lead, contact, company)
    p_create = max(0.30, min(0.90, 0.35 + 0.55*q))
    if random.random() > p_create:
        continue

    sql_dt = SQL_REACHED_AT.get(lead["lead_id"])
    anchor_dt = (sql_dt or parse_dt(lead["qualified_at"])).date()
    lag = timedelta(days=random.randint(1,10))
    created_dt = anchor_dt + lag
    if created_dt >= TODAY:
        continue  # not enough runway to have become an opportunity yet

    opp_idx += 1
    opportunity_id = f"OPP-{opp_idx:06d}"
    owner_rep = pick_owner_rep(company, created_dt, lead["assigned_rep_id"])
    cycle_mult = SIZE_CYCLE_MULT[company["company_size_band"]] * IND_CYCLE_MULT.get(company["industry_id"],1.0)

    final_stage, outcome, loss_reason, actual_close, walk = simulate_opportunity(created_dt, cycle_mult, q)

    lines = build_products_for_opportunity(company)
    deal_value = round(sum(l["line_total_inr"] for l in lines), 2)
    for ln in lines:
        oppr_idx += 1
        opportunity_products_rows.append({
            "opportunity_product_id": f"OPPR-{oppr_idx:07d}", "opportunity_id": opportunity_id,
            "product_id": ln["product_id"], "quantity": ln["quantity"],
            "unit_price_inr": ln["unit_price_inr"], "discount_pct": ln["discount_pct"],
            "line_total_inr": ln["line_total_inr"],
        })

    lo, hi = STAGE_PROB_BAND[final_stage]
    probability_pct = hi if final_stage == "Closed Won" else (lo if final_stage == "Closed Lost" else random.randint(lo,hi))
    forecast_category = ("Closed Won" if final_stage=="Closed Won" else "Closed Lost" if final_stage=="Closed Lost"
                          else "Commit" if final_stage=="Negotiation" else "Best Case" if final_stage=="Proposal" else "Pipeline")
    expected_close = created_dt + timedelta(days=int(30*cycle_mult) + sum(DWELL_BAND[s][1] for s in STAGE_ORDER)*cycle_mult//3)
    competitor_name = ""
    if final_stage=="Closed Lost" and loss_reason=="Competitor":
        competitor_name = random.choice(COMPETITOR_TAGS)

    opportunities_rows.append({
        "opportunity_id": opportunity_id, "company_id": company["company_id"],
        "primary_contact_id": lead["contact_id"], "source_lead_id": lead["lead_id"],
        "owner_rep_id": owner_rep, "opportunity_name": f"{company['company_name']} — CRM Deal {opp_idx}",
        "pipeline_stage": final_stage, "forecast_category": forecast_category,
        "deal_value_inr": deal_value, "probability_pct": probability_pct,
        "expected_close_date": expected_close.isoformat(),
        "actual_close_date": actual_close.isoformat() if actual_close else "",
        "close_outcome": outcome if outcome else "",
        "loss_reason": loss_reason,
        "competitor_name": competitor_name,
        "opportunity_type": "New Business",
        "created_at": datetime.combine(created_dt, datetime.min.time()).replace(
            hour=random.randint(9,19), minute=random.randint(0,59)).isoformat(sep=" "),
    })
    prev_date = created_dt
    for i,(f,t,d) in enumerate(walk):
        osh_idx += 1
        days_prev = (d - prev_date).days if i>0 else ""
        opp_stage_history_rows.append({
            "history_id": f"OSH-{osh_idx:07d}", "opportunity_id": opportunity_id,
            "stage_from": f, "stage_to": t,
            "changed_at": datetime.combine(d, datetime.min.time()).replace(
                hour=random.randint(9,19), minute=random.randint(0,59)).isoformat(sep=" "),
            "days_in_previous_stage": days_prev,
        })
        prev_date = d
    converted_lead_ids.append((lead["lead_id"], opportunity_id, owner_rep,
        datetime.combine(created_dt, datetime.min.time()).replace(hour=random.randint(9,19), minute=random.randint(0,59))))

print("Opportunities from leads:", len(opportunities_rows))
print("  Closed Won:", sum(1 for o in opportunities_rows if o["close_outcome"]=="Won"))
print("  Closed Lost:", sum(1 for o in opportunities_rows if o["close_outcome"]=="Lost"))
print("  Open:", sum(1 for o in opportunities_rows if o["close_outcome"]==""))

# ---------------------------------------------------------------------------
# Customers: exactly one per company, only from that company's first Closed Won
# opportunity (business rule 5 of the finalized schema).
# ---------------------------------------------------------------------------
customers_rows = []
cust_idx = 0
TIER_BANDS = [(200_000,"Bronze"),(1_000_000,"Silver"),(5_000_000,"Gold"),(float("inf"),"Platinum")]
def tier_for(value):
    for cap, name in TIER_BANDS:
        if value <= cap: return name
    return "Platinum"

won_opps = [o for o in opportunities_rows if o["close_outcome"] == "Won"]
won_opps.sort(key=lambda o: o["actual_close_date"])
company_has_customer = set()
customer_by_company = {}
opp_quality = {}  # opportunity_id -> quality index, for engagement-tier correlation
for lead_id, opp_id, owner_rep, created_dt in converted_lead_ids:
    pass  # quality recomputed below directly where needed

for o in won_opps:
    if o["company_id"] in company_has_customer:
        continue  # subsequent won opps for an existing customer -> handled as upsell revenue, not a new customer row
    company_has_customer.add(o["company_id"])
    company = comp_by_id[o["company_id"]]
    lead = next((l for l in leads if l["lead_id"] == o["source_lead_id"]), None)
    contact = contact_by_id[o["primary_contact_id"]]
    q = lead_quality_index(lead, contact, company) if lead else 0.5

    cust_idx += 1
    customer_id = f"CUST-{cust_idx:06d}"
    close_dt = date.fromisoformat(o["actual_close_date"])
    # customer_since is invoicing/onboarding lag after close, but must never
    # exceed "today" -- an opportunity can legitimately close on the cutoff
    # date itself, and un-clamped lag would push the customer record into the future.
    customer_since = min(close_dt + timedelta(days=random.randint(0,3)), TODAY)

    engagement = weighted_choice([("High", 0.15+0.25*q), ("Medium", 0.55), ("Low", max(0.05,0.30-0.25*q))])
    # renormalize isn't strictly required for a synthetic weighting draw; weighted_choice
    # degrades gracefully (falls back to last option) if weights don't sum to 1.

    contract_type = weighted_choice([("Annual",0.55),("Monthly",0.25),("Multi-Year",0.20)])
    if company["company_size_band"] in ("Large","Enterprise") and random.random() < 0.35:
        contract_type = "Multi-Year"

    region = company["region"]
    csm_pool = csms_by_region.get(region, active_csms)
    csm = random.choice(csm_pool)["rep_id"] if csm_pool else ""

    if engagement == "High":
        status = weighted_choice([("Active",0.95),("At Risk",0.05)])
    elif engagement == "Medium":
        status = weighted_choice([("Active",0.80),("At Risk",0.15),("Paused",0.05)])
    else:
        status = weighted_choice([("Active",0.50),("At Risk",0.35),("Paused",0.15)])

    customers_rows.append({
        "customer_id": customer_id, "company_id": company["company_id"],
        "originating_opportunity_id": o["opportunity_id"], "customer_since": customer_since.isoformat(),
        "csm_rep_id": csm, "customer_tier": tier_for(float(o["deal_value_inr"])),
        "contract_type": contract_type, "renewal_date": "",  # backfilled after transactions
        "customer_status": status,
    })
    customer_by_company[o["company_id"]] = {"row": customers_rows[-1], "engagement": engagement,
                                              "opp": o, "customer_since": customer_since}

print("Customers created:", len(customers_rows))

# ---------------------------------------------------------------------------
# customer_transactions
# ---------------------------------------------------------------------------
customer_transactions_rows = []
txn_idx = 0
inv_idx = 0
CADENCE_DAYS = {"Monthly": 30, "Annual": 365, "Multi-Year": 730}
RENEW_PROB = {"High": 0.90, "Medium": 0.68, "Low": 0.35}

def next_invoice():
    global inv_idx
    inv_idx += 1
    return f"INV-2025-{inv_idx:06d}"

def payment_status_draw(engagement):
    if engagement == "Low":
        return weighted_choice([("Paid",0.45),("Pending",0.15),("Overdue",0.30),("Partially Paid",0.10)])
    if engagement == "Medium":
        return weighted_choice([("Paid",0.68),("Pending",0.15),("Overdue",0.12),("Partially Paid",0.05)])
    return weighted_choice([("Paid",0.85),("Pending",0.08),("Overdue",0.04),("Partially Paid",0.03)])

for company_id, info in customer_by_company.items():
    cust = info["row"]; engagement = info["engagement"]; opp = info["opp"]; since = info["customer_since"]
    base_amount = float(opp["deal_value_inr"])
    cadence = CADENCE_DAYS[cust["contract_type"]]

    # initial sale (clamp: customer_since can already equal TODAY, and an
    # unclamped +0..5 day invoicing lag could then push the transaction date
    # into the future)
    txn_idx += 1
    first_txn_date = min(since + timedelta(days=random.randint(0,5)), TODAY)
    customer_transactions_rows.append({
        "transaction_id": f"TXN-{txn_idx:07d}", "customer_id": cust["customer_id"],
        "opportunity_id": opp["opportunity_id"], "transaction_date": first_txn_date.isoformat(),
        "transaction_type": "New Sale", "amount_inr": round(base_amount,2),
        "payment_status": payment_status_draw(engagement), "invoice_number": next_invoice(),
    })
    last_txn_date = first_txn_date
    last_active_date = first_txn_date

    next_renew = since + timedelta(days=cadence)
    renewal_count = 0
    while next_renew <= TODAY:
        if random.random() > RENEW_PROB[engagement]:
            break  # non-renewal -- customer goes quiet from here (natural churn signal, no further transactions)
        renewal_count += 1
        variance = random.uniform(-0.15, 0.15)
        amount = round(base_amount * (1+variance), 2)
        txn_idx += 1
        customer_transactions_rows.append({
            "transaction_id": f"TXN-{txn_idx:07d}", "customer_id": cust["customer_id"],
            "opportunity_id": opp["opportunity_id"], "transaction_date": next_renew.isoformat(),
            "transaction_type": "Renewal", "amount_inr": amount,
            "payment_status": payment_status_draw(engagement), "invoice_number": next_invoice(),
        })
        last_txn_date = next_renew
        last_active_date = next_renew

        # possible upsell shortly after a successful renewal
        upsell_p = {"High":0.35,"Medium":0.18,"Low":0.05}[engagement]
        if random.random() < upsell_p:
            up_date = next_renew + timedelta(days=random.randint(5,45))
            if up_date <= TODAY:
                txn_idx += 1
                up_amount = round(base_amount * random.uniform(0.10, 0.40), 2)
                customer_transactions_rows.append({
                    "transaction_id": f"TXN-{txn_idx:07d}", "customer_id": cust["customer_id"],
                    "opportunity_id": "", "transaction_date": up_date.isoformat(),
                    "transaction_type": "Upsell", "amount_inr": up_amount,
                    "payment_status": payment_status_draw(engagement), "invoice_number": next_invoice(),
                })
                last_active_date = max(last_active_date, up_date)
        next_renew = next_renew + timedelta(days=cadence)

    # occasional refund (rare, shortly after a transaction, small negative amount)
    if random.random() < 0.03:
        ref_date = last_txn_date + timedelta(days=random.randint(3,20))
        if ref_date <= TODAY:
            txn_idx += 1
            customer_transactions_rows.append({
                "transaction_id": f"TXN-{txn_idx:07d}", "customer_id": cust["customer_id"],
                "opportunity_id": "", "transaction_date": ref_date.isoformat(),
                "transaction_type": "Refund", "amount_inr": -round(base_amount*random.uniform(0.05,0.20),2),
                "payment_status": "Paid", "invoice_number": next_invoice(),
            })

    # occasional downgrade for low-engagement customers late in their tenure
    if engagement == "Low" and random.random() < 0.15 and last_active_date + timedelta(days=30) <= TODAY:
        dg_date = last_active_date + timedelta(days=random.randint(15,45))
        if dg_date <= TODAY:
            txn_idx += 1
            customer_transactions_rows.append({
                "transaction_id": f"TXN-{txn_idx:07d}", "customer_id": cust["customer_id"],
                "opportunity_id": "", "transaction_date": dg_date.isoformat(),
                "transaction_type": "Downgrade", "amount_inr": -round(base_amount*random.uniform(0.10,0.30),2),
                "payment_status": payment_status_draw(engagement), "invoice_number": next_invoice(),
            })

    # renewal_date: next cadence boundary after the last transaction actually recorded
    if random.random() < 0.90:  # ~10% of customers have no tracked renewal date (informal/one-off engagement)
        renewal_dt = last_txn_date + timedelta(days=cadence)
        cust["renewal_date"] = renewal_dt.isoformat()

        # customer_status was drawn independently of the renewal simulation
        # above (it's an engagement-tier draw made at customer-creation time,
        # before we know whether this customer actually renews on schedule).
        # That can leave a customer marked "Active" even though the renewal
        # simulation just determined they missed a renewal that's already due
        # -- a real logical inconsistency between renewal_date and
        # customer_status, not a realistic one. Correct it here, using only
        # the just-computed renewal_dt (never a fresh random draw), so status
        # always agrees with what the transaction history actually shows.
        if cust["customer_status"] == "Active" and renewal_dt < TODAY:
            overdue_days = (TODAY - renewal_dt).days
            cust["customer_status"] = "Paused" if overdue_days >= 90 else "At Risk"

print("customer_transactions:", len(customer_transactions_rows))

# ---------------------------------------------------------------------------
# customer_support_cases
# ---------------------------------------------------------------------------
customer_support_cases_rows = []
case_idx = 0
CASE_TYPE_WEIGHTS = [("Technical Issue",0.35),("Billing Query",0.15),("Feature Request",0.15),
                     ("Onboarding Help",0.10),("Complaint",0.10),("General Query",0.15)]
N_CASES_BY_ENGAGEMENT = {"Low":[(0,0.35),(1,0.40),(2,0.25)],
                          "Medium":[(1,0.30),(2,0.35),(3,0.25),(4,0.10)],
                          "High":[(2,0.25),(3,0.30),(4,0.25),(5,0.15),(6,0.05)]}

contacts_by_company = {}
for c in contacts:
    contacts_by_company.setdefault(c["company_id"], []).append(c)

for company_id, info in customer_by_company.items():
    cust = info["row"]; engagement = info["engagement"]; since = info["customer_since"]
    status = cust["customer_status"]
    n_cases = weighted_choice(N_CASES_BY_ENGAGEMENT[engagement])
    span_days = max(0, (TODAY - since).days)  # 0 when the customer was created today -- no future overflow
    company_contacts = contacts_by_company.get(company_id, [])
    for _ in range(n_cases):
        case_idx += 1
        opened = since + timedelta(days=random.randint(0, span_days))
        opened_full_dt = datetime.combine(opened, datetime.min.time()).replace(
            hour=random.randint(9,19), minute=random.randint(0,59))
        case_type = weighted_choice(CASE_TYPE_WEIGHTS)
        if status == "At Risk":
            priority = weighted_choice([("Low",0.10),("Medium",0.30),("High",0.35),("Critical",0.25)])
            case_status = weighted_choice([("Open",0.15),("In Progress",0.20),("Escalated",0.20),("Resolved",0.30),("Closed",0.15)])
        else:
            priority = weighted_choice([("Low",0.30),("Medium",0.40),("High",0.22),("Critical",0.08)])
            case_status = weighted_choice([("Open",0.08),("In Progress",0.12),("Escalated",0.05),("Resolved",0.50),("Closed",0.25)])
        resolved_at = ""
        satisfaction = ""
        if case_status in ("Resolved","Closed"):
            # built from opened_full_dt by construction so resolved is always
            # strictly after opened, even when both land on the same calendar day
            resolved_dt = opened_full_dt + timedelta(hours=random.randint(2, 240))
            today_end = datetime.combine(TODAY, datetime.min.time()).replace(hour=23, minute=59)
            if resolved_dt > today_end: resolved_dt = today_end
            resolved_at = resolved_dt.isoformat(sep=" ")
            satisfaction = str(weighted_choice([(5,0.15),(4,0.30),(3,0.25),(2,0.20),(1,0.10)])) if status=="At Risk" else \
                            str(weighted_choice([(5,0.35),(4,0.35),(3,0.20),(2,0.07),(1,0.03)]))
        contact_id = random.choice(company_contacts)["contact_id"] if company_contacts and random.random()>0.1 else ""
        customer_support_cases_rows.append({
            "case_id": f"CASE-{case_idx:07d}", "customer_id": cust["customer_id"], "contact_id": contact_id,
            "case_type": case_type, "priority": priority, "status": case_status,
            "opened_at": opened_full_dt.isoformat(sep=" "),
            "resolved_at": resolved_at, "satisfaction_score": satisfaction,
        })

print("customer_support_cases:", len(customer_support_cases_rows))

# ---------------------------------------------------------------------------
# Write Phase-3 CSVs
# ---------------------------------------------------------------------------
write_csv("opportunities", opportunities_rows, ["opportunity_id","company_id","primary_contact_id","source_lead_id",
    "owner_rep_id","opportunity_name","pipeline_stage","forecast_category","deal_value_inr","probability_pct",
    "expected_close_date","actual_close_date","close_outcome","loss_reason","competitor_name","opportunity_type","created_at"])
write_csv("opportunity_products", opportunity_products_rows, ["opportunity_product_id","opportunity_id","product_id",
    "quantity","unit_price_inr","discount_pct","line_total_inr"])
write_csv("opportunity_stage_history", opp_stage_history_rows, ["history_id","opportunity_id","stage_from","stage_to",
    "changed_at","days_in_previous_stage"])
write_csv("customers", customers_rows, ["customer_id","company_id",
    "originating_opportunity_id","customer_since","csm_rep_id","customer_tier","contract_type","renewal_date","customer_status"])
write_csv("customer_transactions", customer_transactions_rows, ["transaction_id","customer_id","opportunity_id",
    "transaction_date","transaction_type","amount_inr","payment_status","invoice_number"])
write_csv("customer_support_cases", customer_support_cases_rows, ["case_id","customer_id","contact_id","case_type",
    "priority","status","opened_at","resolved_at","satisfaction_score"])

# ---------------------------------------------------------------------------
# Backfill Phase-2 leads / lead_status_history for leads that produced an
# opportunity: SQL leads can now legitimately move to 'Converted'.
# ---------------------------------------------------------------------------
converted_map = {lid: (oid, rep, dt) for lid, oid, rep, dt in converted_lead_ids}
for l in leads:
    if l["lead_id"] in converted_map:
        oid, rep, dt = converted_map[l["lead_id"]]
        l["lead_status"] = "Converted"
        l["converted_at"] = dt.isoformat(sep=" ")

new_lsh_rows = []
next_lsh_idx = max(int(r["history_id"].split("-")[1]) for r in lsh) if lsh else 0
for l in leads:
    if l["lead_id"] in converted_map:
        oid, rep, dt = converted_map[l["lead_id"]]
        next_lsh_idx += 1
        new_lsh_rows.append({
            "history_id": f"LSH-{next_lsh_idx:07d}", "lead_id": l["lead_id"],
            "status_from": "Sales Qualified (SQL)", "status_to": "Converted",
            "changed_at": dt.isoformat(sep=" "), "changed_by_rep_id": rep,
        })
lsh_updated = lsh + new_lsh_rows

write_csv("leads", leads, ["lead_id","company_id","contact_id","lead_source_id","campaign_id",
    "assigned_rep_id","lead_status","disqualification_reason","industry_interest_id","estimated_budget_inr",
    "company_size_at_lead_time","created_at","first_contacted_at","qualified_at","converted_at","is_duplicate_of_lead_id"])
write_csv("lead_status_history", lsh_updated, ["history_id","lead_id","status_from","status_to","changed_at","changed_by_rep_id"])

# ---------------------------------------------------------------------------
# Backfill companies.account_status -> 'Active Customer' for companies that
# now have a customer row.
# ---------------------------------------------------------------------------
for c in companies:
    if c["company_id"] in customer_by_company:
        c["account_status"] = "Active Customer"
write_csv("companies", companies, ["company_id","company_name","name_is_real_entity","industry_id","sub_industry",
    "company_size_band","annual_revenue_band_inr","gstin","city","state","region","pincode","website_domain",
    "company_type","founded_year","account_owner_rep_id","account_status","created_at"])

print("Backfilled leads converted:", len(converted_map))
print("Backfilled companies -> Active Customer:", sum(1 for c in companies if c["account_status"]=="Active Customer"))
