#!/usr/bin/env python3
"""
Indian B2B CRM synthetic dataset — Phase 4: ML-ready derived datasets.
Built ENTIRELY by reading the validated Phase 1-3 source tables (never
independently invented) and applying documented, leakage-aware feature-
engineering rules. These are regenerable snapshots, not part of the
operational (OLTP) schema -- rerunning this script from the same source
tables reproduces the same output deterministically.
"""
import csv, random, json
from datetime import date, datetime, timedelta
from collections import defaultdict

random.seed(20260915)
IO = "/home/claude/crm_gen/output"
TODAY = date(2026, 9, 15)

def read_csv(name):
    with open(f"data/source/{name}.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def write_csv(name, rows, fieldnames):
    with open(f"data/ml/{name}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows: w.writerow(r)

companies = read_csv("companies")
contacts = read_csv("contacts")
leads = read_csv("leads")
lsh = read_csv("lead_status_history")
reps = read_csv("sales_reps")
lead_sources = read_csv("lead_sources")
opps = read_csv("opportunities")
oprod = read_csv("opportunity_products")
products = read_csv("products")
customers = read_csv("customers")
ctxn = read_csv("customer_transactions")
ccase = read_csv("customer_support_cases")

comp_by_id = {c["company_id"]: c for c in companies}
contact_by_id = {c["contact_id"]: c for c in contacts}
rep_by_id = {r["rep_id"]: r for r in reps}
src_by_id = {s["lead_source_id"]: s for s in lead_sources}
lsh_by_lead = defaultdict(list)
for r in lsh: lsh_by_lead[r["lead_id"]].append(r)
oprod_by_opp = defaultdict(list)
for r in oprod: oprod_by_opp[r["opportunity_id"]].append(r)
prod_by_id = {p["product_id"]: p for p in products}
txn_by_cust = defaultdict(list)
for r in ctxn: txn_by_cust[r["customer_id"]].append(r)
case_by_cust = defaultdict(list)
for r in ccase: case_by_cust[r["customer_id"]].append(r)
opp_by_id = {o["opportunity_id"]: o for o in opps}

def pdt(s):
    if not s: return None
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S") if len(s) > 10 else datetime.strptime(s, "%Y-%m-%d")

def pdate(s):
    d = pdt(s)
    return d.date() if d else None

def time_split(rows, date_key, train=0.70, val=0.15):
    """Chronological split -- earliest rows train, latest rows test. Never
    random: this is what 'time-aware splitting' means for entity-snapshot
    tables where the underlying process drifts over a multi-year window."""
    ordered = sorted(rows, key=lambda r: r[date_key])
    n = len(ordered)
    n_train = int(n*train); n_val = int(n*(train+val))
    for i, r in enumerate(ordered):
        r["dataset_split"] = "train" if i < n_train else ("validation" if i < n_val else "test")
    return rows

# =============================================================================
# 1. lead_conversion_dataset.csv
#    cutoff = qualified_at if reached, else first_contacted_at, else created_at
#    label = did this lead's own row end up 'Converted' (i.e. produced an
#    opportunity) -- this is a fact ABOUT THE LEAD, known only after cutoff,
#    so it is a valid supervised label, never a feature.
# =============================================================================
REP_HIST = defaultdict(list)  # rep_id -> sorted list of (created_at, resolved_bool, converted_bool)
for l in leads:
    if l["assigned_rep_id"] and l["lead_status"] in ("Converted","Disqualified","Dead"):
        REP_HIST[l["assigned_rep_id"]].append((pdt(l["created_at"]), l["lead_status"]=="Converted"))
for rid in REP_HIST: REP_HIST[rid].sort(key=lambda t: t[0])

def rep_trailing_conv_rate(rep_id, cutoff_dt):
    if not rep_id or rep_id not in REP_HIST:
        return None
    prior = [c for (dt, c) in REP_HIST[rep_id] if dt < cutoff_dt]
    if len(prior) < 5:
        return None
    return round(sum(prior)/len(prior), 3)

GLOBAL_PRIOR_CONV = []
for l in sorted(leads, key=lambda r: r["created_at"]):
    if l["lead_status"] in ("Converted","Disqualified","Dead"):
        GLOBAL_PRIOR_CONV.append((pdt(l["created_at"]), l["lead_status"]=="Converted"))
def global_trailing_conv_rate(cutoff_dt):
    prior = [c for (dt,c) in GLOBAL_PRIOR_CONV if dt < cutoff_dt]
    return round(sum(prior)/len(prior),3) if prior else 0.15

lead_conv_rows = []
for l in leads:
    company = comp_by_id[l["company_id"]]; contact = contact_by_id[l["contact_id"]]
    qualified = l["qualified_at"]; first_contact = l["first_contacted_at"]
    cutoff = qualified or first_contact or l["created_at"]
    cutoff_dt = pdt(cutoff)
    created_dt = pdt(l["created_at"])
    hist = [h for h in lsh_by_lead[l["lead_id"]] if pdt(h["changed_at"]) <= cutoff_dt]
    n_transitions = max(0, len(hist) - 1)  # exclude the initial "New" capture row
    rep_rate = rep_trailing_conv_rate(l["assigned_rep_id"], cutoff_dt)
    if rep_rate is None: rep_rate = global_trailing_conv_rate(cutoff_dt)

    lead_conv_rows.append({
        "ml_record_id": f"MLC-{len(lead_conv_rows)+1:06d}", "lead_id": l["lead_id"],
        "company_id": l["company_id"], "observation_cutoff_at": cutoff,
        "industry_id": company["industry_id"], "region": company["region"],
        "company_size_at_lead_time": l["company_size_at_lead_time"],
        "lead_source_category": src_by_id[l["lead_source_id"]]["source_category"],
        "campaign_sourced_flag": bool(l["campaign_id"]),
        "contact_seniority_level": contact["seniority_level"],
        "contact_is_decision_maker": contact["is_decision_maker"] == "True",
        "estimated_budget_known": bool(l["estimated_budget_inr"]),
        "estimated_budget_band": ("Unknown" if not l["estimated_budget_inr"] else
            "Low" if float(l["estimated_budget_inr"])<300000 else
            "Mid" if float(l["estimated_budget_inr"])<1500000 else "High"),
        "days_since_created_to_cutoff": (cutoff_dt - created_dt).days,
        "num_status_transitions_before_cutoff": n_transitions,
        "rep_assigned_flag": bool(l["assigned_rep_id"]),
        "rep_trailing_conversion_rate": rep_rate,
        "is_duplicate_lead": bool(l["is_duplicate_of_lead_id"]),
        "label_converted": l["lead_status"] == "Converted",
    })
time_split(lead_conv_rows, "observation_cutoff_at")

LC_FIELDS = ["ml_record_id","lead_id","company_id","observation_cutoff_at","industry_id","region",
    "company_size_at_lead_time","lead_source_category","campaign_sourced_flag","contact_seniority_level",
    "contact_is_decision_maker","estimated_budget_known","estimated_budget_band","days_since_created_to_cutoff",
    "num_status_transitions_before_cutoff","rep_assigned_flag","rep_trailing_conversion_rate",
    "is_duplicate_lead","label_converted","dataset_split"]
write_csv("lead_conversion_dataset", lead_conv_rows, LC_FIELDS)
print("lead_conversion_dataset:", len(lead_conv_rows),
      "positive rate:", round(sum(r["label_converted"] for r in lead_conv_rows)/len(lead_conv_rows),3))

# =============================================================================
# 2. lead_scoring_dataset.csv
#    cutoff = created_at (day 0) ONLY -- static firmographic/source features,
#    intentionally NO engagement-derived features (that's what separates this
#    from lead_conversion_dataset). estimated_budget_inr is deliberately
#    EXCLUDED here: Phase-2's generator ties its missingness to the lead's
#    eventual funnel stage, which is not truly known at day 0 -- see the
#    leakage audit for the full explanation.
# =============================================================================
lead_score_rows = []
for l in leads:
    company = comp_by_id[l["company_id"]]; contact = contact_by_id[l["contact_id"]]
    qualified = l["qualified_at"]; first_contact = l["first_contacted_at"]
    cutoff = qualified or first_contact or l["created_at"]
    cutoff_dt = pdt(cutoff)
    created_dt = pdt(l["created_at"])
    hist = [h for h in lsh_by_lead[l["lead_id"]] if pdt(h["changed_at"]) <= cutoff_dt]
    n_transitions = max(0, len(hist) - 1)
    rep_rate = rep_trailing_conv_rate(l["assigned_rep_id"], cutoff_dt)
    if rep_rate is None: rep_rate = global_trailing_conv_rate(cutoff_dt)
    
    lead_score_rows.append({
        "ml_record_id": f"MLS-{len(lead_score_rows)+1:06d}", "lead_id": l["lead_id"],
        "company_id": l["company_id"], "observation_cutoff_at": cutoff,
        "industry_id": company["industry_id"], "region": company["region"],
        "company_size_at_lead_time": l["company_size_at_lead_time"],
        "lead_source_category": src_by_id[l["lead_source_id"]]["source_category"],
        "campaign_sourced_flag": bool(l["campaign_id"]),
        "contact_seniority_level": contact["seniority_level"],
        "contact_is_decision_maker": contact["is_decision_maker"] == "True",
        "contact_department": contact["department"],
        "estimated_budget_known": bool(l["estimated_budget_inr"]),
        "estimated_budget_band": ("Unknown" if not l["estimated_budget_inr"] else
            "Low" if float(l["estimated_budget_inr"])<300000 else
            "Mid" if float(l["estimated_budget_inr"])<1500000 else "High"),
        "days_since_created_to_cutoff": (cutoff_dt - created_dt).days,
        "num_status_transitions_before_cutoff": n_transitions,
        "rep_assigned_flag": bool(l["assigned_rep_id"]),
        "rep_trailing_conversion_rate": rep_rate,
        "label_converted": l["lead_status"] == "Converted",
    })
time_split(lead_score_rows, "observation_cutoff_at")
LS_FIELDS = ["ml_record_id","lead_id","company_id","observation_cutoff_at","industry_id","region",
    "company_size_at_lead_time","lead_source_category","campaign_sourced_flag","contact_seniority_level",
    "contact_is_decision_maker","contact_department","estimated_budget_known","estimated_budget_band",
    "days_since_created_to_cutoff","num_status_transitions_before_cutoff","rep_assigned_flag",
    "rep_trailing_conversion_rate","label_converted","dataset_split"]
write_csv("lead_scoring_dataset", lead_score_rows, LS_FIELDS)
print("lead_scoring_dataset:", len(lead_score_rows),
      "positive rate:", round(sum(r["label_converted"] for r in lead_score_rows)/len(lead_score_rows),3))

# =============================================================================
# 3. sales_forecasting_dataset.csv
#    Unit: (department_id, month) -- departments whose reps actually own
#    opportunities (Enterprise Sales, SMB Sales, Inside Sales, Channel
#    Partnerships). All features computed strictly from data dated BEFORE the
#    period start; the label is the revenue realized DURING the period
#    (legitimately future relative to the feature cutoff -- that's what makes
#    it a forecasting target, not a leak).
# =============================================================================
OWNER_DEPTS = ["DEPT-0001","DEPT-0002","DEPT-0003","DEPT-0007"]
dept_name = {d["department_id"]: d["department_name"] for d in read_csv("departments")}
rep_dept = {r["rep_id"]: r["department_id"] for r in reps}

opps_enriched = []
for o in opps:
    o2 = dict(o)
    o2["dept"] = rep_dept.get(o["owner_rep_id"], "")
    o2["created_date"] = pdate(o["created_at"])
    o2["close_date"] = pdate(o["actual_close_date"]) if o["actual_close_date"] else None
    opps_enriched.append(o2)

def month_range(start: date, end: date):
    y, m = start.year, start.month
    out = []
    while (y, m) <= (end.year, end.month):
        out.append(date(y, m, 1))
        m += 1
        if m > 12: m = 1; y += 1
    return out

all_created = [o["created_date"] for o in opps_enriched]
range_start = date(min(all_created).year, min(all_created).month, 1)
range_end = date(TODAY.year, TODAY.month, 1)
months = month_range(range_start, range_end)

def month_add(d: date, n: int) -> date:
    y, m = d.year, d.month + n
    while m > 12: m -= 12; y += 1
    while m < 1: m += 12; y -= 1
    return date(y, m, 1)

forecast_rows = []
company_opps = [o for o in opps_enriched if o["dept"] in OWNER_DEPTS]

active_reps_count_by_month = {}
for mstart in months:
    active_reps_count_by_month[mstart] = sum(
        1 for r in reps if r["department_id"] in OWNER_DEPTS and
        datetime.strptime(r["hire_date"],"%Y-%m-%d").date() <= mstart and
        (r["is_active"]=="True" or (r["termination_date"] and datetime.strptime(r["termination_date"],"%Y-%m-%d").date() > mstart))
    )

for mstart in months:
    mend_excl = month_add(mstart, 1)
    if mstart >= range_end:  # current/incomplete month has no realized-to-date label -- skip
        continue
    # ---- features: strictly pre-period-start ----
    open_pipeline = [o for o in company_opps if o["created_date"] < mstart and
                      (o["close_date"] is None or o["close_date"] >= mstart)]
    pipeline_value = round(sum(float(o["deal_value_inr"]) for o in open_pipeline), 2)
    num_open = len(open_pipeline)
    trail3_start = month_add(mstart, -3)
    closed_trail3 = [o for o in company_opps if o["close_date"] and trail3_start <= o["close_date"] < mstart]
    won_trail3 = [o for o in closed_trail3 if o["close_outcome"]=="Won"]
    win_rate_trail3 = round(len(won_trail3)/len(closed_trail3),3) if closed_trail3 else None
    revenue_trail3 = round(sum(float(o["deal_value_inr"]) for o in won_trail3),2)
    trail6_start = month_add(mstart, -6)
    won_trail6 = [o for o in company_opps if o["close_date"] and trail6_start <= o["close_date"] < mstart and o["close_outcome"]=="Won"]
    avg_cycle_trail6 = round(sum((o["close_date"]-o["created_date"]).days for o in won_trail6)/len(won_trail6),1) if won_trail6 else None
    # ---- label: realized in period ----
    won_in_period = [o for o in company_opps if o["close_date"] and mstart <= o["close_date"] < mend_excl and o["close_outcome"]=="Won"]
    label_amount = round(sum(float(o["deal_value_inr"]) for o in won_in_period),2)

    forecast_rows.append({
        "ml_record_id": f"MLF-{len(forecast_rows)+1:05d}", "department_id": "ALL",
        "department_name": "Company Wide", "period_label": mstart.strftime("%Y-%m"),
        "period_start": mstart.isoformat(),
        "pipeline_value_open_at_period_start_inr": pipeline_value,
        "num_open_opportunities_at_period_start": num_open,
        "historical_win_rate_trailing_3mo": win_rate_trail3,
        "revenue_trailing_3mo_inr": revenue_trail3,
        "avg_deal_cycle_days_trailing_6mo": avg_cycle_trail6,
        "active_rep_count": active_reps_count_by_month[mstart],
        "seasonality_month": mstart.month,
        "label_actual_amount_inr": label_amount,
    })
time_split(forecast_rows, "period_start")
FC_FIELDS = ["ml_record_id","department_id","department_name","period_label","period_start",
    "pipeline_value_open_at_period_start_inr","num_open_opportunities_at_period_start",
    "historical_win_rate_trailing_3mo","revenue_trailing_3mo_inr","avg_deal_cycle_days_trailing_6mo",
    "active_rep_count","seasonality_month","label_actual_amount_inr","dataset_split"]
write_csv("sales_forecasting_dataset", forecast_rows, FC_FIELDS)
nonzero = sum(1 for r in forecast_rows if r["label_actual_amount_inr"]>0)
print("sales_forecasting_dataset:", len(forecast_rows), "rows, nonzero-revenue periods:", nonzero)

# =============================================================================
# 3b. cash_collections_forecasting_dataset.csv
#    Target definition: Net realized cash collections during the calendar month
#    from genuinely paid transactions (CustomerTransaction.payment_status == 'Paid'
#    and deleted_at is null), with refunds correctly deducted.
#    Excludes Pending, Overdue, and Partially Paid invoice face values.
#    All features are strictly derived from observations dated BEFORE period_start
#    (< period_start), preventing temporal leakage.
# =============================================================================
def normalize_cashflow_amt(amt_val, txn_type: str = "") -> float:
    try:
        val = float(amt_val or 0.0)
    except Exception:
        return 0.0
    is_refund = (txn_type == "Refund") or (val < 0)
    return -abs(val) if is_refund else abs(val)

parsed_txns = []
for t in ctxn:
    if t.get("deleted_at"): continue
    t_dt = pdate(t["transaction_date"])
    if not t_dt: continue
    ttype = t.get("transaction_type", "")
    net_amt = normalize_cashflow_amt(t["amount_inr"], ttype)
    parsed_txns.append({
        "transaction_id": t["transaction_id"],
        "date": t_dt,
        "amount": net_amt,
        "payment_status": t["payment_status"],
        "transaction_type": ttype
    })

cash_forecast_rows = []
for mstart in months:
    mend_excl = month_add(mstart, 1)
    if mstart >= range_end:
        continue

    # Features: STRICTLY before mstart (< mstart)
    open_pipeline = [o for o in company_opps if o["created_date"] < mstart and
                      (o["close_date"] is None or o["close_date"] >= mstart)]
    pipeline_value = round(sum(float(o["deal_value_inr"]) for o in open_pipeline), 2)
    num_open = len(open_pipeline)

    trail1_start = month_add(mstart, -1)
    paid_txns_trail1 = [t for t in parsed_txns if t["payment_status"] == "Paid" and trail1_start <= t["date"] < mstart]
    cash_rev_trail1 = round(sum(t["amount"] for t in paid_txns_trail1), 2)

    trail3_start = month_add(mstart, -3)
    paid_txns_trail3 = [t for t in parsed_txns if t["payment_status"] == "Paid" and trail3_start <= t["date"] < mstart]
    cash_rev_trail3 = round(sum(t["amount"] for t in paid_txns_trail3), 2)
    num_paid_txns_trail3 = len(paid_txns_trail3)

    closed_trail3 = [o for o in company_opps if o["close_date"] and trail3_start <= o["close_date"] < mstart]
    won_trail3 = [o for o in closed_trail3 if o["close_outcome"] == "Won"]
    win_rate_trail3 = round(len(won_trail3) / len(closed_trail3), 3) if closed_trail3 else 0.0
    opp_bookings_trail3 = round(sum(float(o["deal_value_inr"]) for o in won_trail3), 2)

    # Label: Net realized cash collections occurring DURING mstart <= date < mend_excl
    period_paid_txns = [t for t in parsed_txns if t["payment_status"] == "Paid" and mstart <= t["date"] < mend_excl]
    net_cash_label = round(sum(t["amount"] for t in period_paid_txns), 2)

    cash_forecast_rows.append({
        "ml_record_id": f"MLCF-{len(cash_forecast_rows)+1:05d}",
        "department_id": "ALL",
        "department_name": "Company Wide",
        "period_label": mstart.strftime("%Y-%m"),
        "period_start": mstart.isoformat(),
        "pipeline_value_open_at_period_start_inr": pipeline_value,
        "num_open_opportunities_at_period_start": num_open,
        "cash_revenue_trailing_1mo_inr": cash_rev_trail1,
        "cash_revenue_trailing_3mo_inr": cash_rev_trail3,
        "num_paid_txns_trailing_3mo": num_paid_txns_trail3,
        "opp_bookings_trailing_3mo_inr": opp_bookings_trail3,
        "historical_win_rate_trailing_3mo": win_rate_trail3,
        "active_rep_count": active_reps_count_by_month[mstart],
        "seasonality_month": mstart.month,
        "label_net_cash_collections_inr": net_cash_label,
    })

time_split(cash_forecast_rows, "period_start")
CASH_FC_FIELDS = [
    "ml_record_id", "department_id", "department_name", "period_label", "period_start",
    "pipeline_value_open_at_period_start_inr", "num_open_opportunities_at_period_start",
    "cash_revenue_trailing_1mo_inr", "cash_revenue_trailing_3mo_inr", "num_paid_txns_trailing_3mo",
    "opp_bookings_trailing_3mo_inr", "historical_win_rate_trailing_3mo",
    "active_rep_count", "seasonality_month", "label_net_cash_collections_inr", "dataset_split"
]
write_csv("cash_collections_forecasting_dataset", cash_forecast_rows, CASH_FC_FIELDS)
cash_nonzero = sum(1 for r in cash_forecast_rows if r["label_net_cash_collections_inr"] > 0)
print("cash_collections_forecasting_dataset:", len(cash_forecast_rows), "rows, nonzero-cash periods:", cash_nonzero)

# =============================================================================
# 4. customer_segmentation_dataset.csv
#    Unit: (customer_id, snapshot quarter-end). Unsupervised -- no label.
#    Every feature uses only transactions/cases dated <= snapshot_date.
# =============================================================================
def quarter_ends_between(start: date, end: date):
    out = []
    y, q = start.year, (start.month-1)//3
    while True:
        month_end = (q*3)+3
        yy = y + (1 if month_end>12 else 0)
        mm = month_end-12 if month_end>12 else month_end
        qd = date(yy, mm, 1) - timedelta(days=1) if mm != 12 else date(yy,12,31)
        # simpler: last day of that quarter's final month
        import calendar
        last_day = calendar.monthrange(yy, mm)[1]
        qd = date(yy, mm, last_day)
        if qd > end: break
        out.append(qd)
        q += 1
        if q > 3: q = 0; y += 1
    return out

seg_rows = []
for cust in customers:
    since = pdate(cust["customer_since"])
    company = comp_by_id[cust["company_id"]]
    txns = sorted(txn_by_cust[cust["customer_id"]], key=lambda t: t["transaction_date"])
    cases = sorted(case_by_cust[cust["customer_id"]], key=lambda c: c["opened_at"])
    orig_opp = opp_by_id.get(cust["originating_opportunity_id"])
    product_categories = set()
    if orig_opp:
        for ln in oprod_by_opp.get(orig_opp["opportunity_id"], []):
            product_categories.add(prod_by_id[ln["product_id"]]["product_category"])

    snapshots = quarter_ends_between(since, TODAY)
    if not snapshots or snapshots[-1] != TODAY:
        snapshots.append(TODAY)
    for snap in snapshots:
        txns_to_date = [t for t in txns if pdate(t["transaction_date"]) <= snap]
        if not txns_to_date:
            continue
        last_txn_date = max(pdate(t["transaction_date"]) for t in txns_to_date)
        txns_12mo = [t for t in txns_to_date if pdate(t["transaction_date"]) > snap - timedelta(days=365)]
        cases_to_date = [c for c in cases if pdate(c["opened_at"]) <= snap]
        cases_12mo = [c for c in cases_to_date if pdate(c["opened_at"]) > snap - timedelta(days=365)]
        # avg_satisfaction_score must be scoped to the SAME trailing-12mo window
        # as support_case_count_last_12mo (its neighboring column) -- computing
        # it from cases_to_date (all-time) instead let a customer with 0 cases
        # in the trailing window still show a non-null score carried over from
        # older, out-of-window cases, which is internally inconsistent with the
        # count sitting right next to it. Found via a missing-value audit that
        # cross-checked avg_satisfaction_score against support_case_count_last_12mo
        # (10/244 rows had count==0 but a non-null score) -- see
        # data_quality_report.md for the full root-cause writeup.
        resolved_scores = [int(float(c["satisfaction_score"])) for c in cases_12mo if c["satisfaction_score"]]

        seg_rows.append({
            "ml_record_id": f"MLG-{len(seg_rows)+1:06d}", "customer_id": cust["customer_id"],
            "company_id": cust["company_id"], "snapshot_date": snap.isoformat(),
            "recency_days_since_last_transaction": (snap - last_txn_date).days,
            "frequency_transactions_last_12mo": len(txns_12mo),
            "monetary_total_last_12mo_inr": round(sum(float(t["amount_inr"]) for t in txns_12mo), 2),
            "tenure_months_at_snapshot": round((snap - since).days / 30.44, 1),
            "support_case_count_last_12mo": len(cases_12mo),
            "avg_satisfaction_score": round(sum(resolved_scores)/len(resolved_scores),2) if resolved_scores else None,
            "product_category_diversity": len(product_categories),
            "industry_id": company["industry_id"], "company_size_band": company["company_size_band"],
            "customer_tier": cust["customer_tier"], "contract_type": cust["contract_type"],
            # NOTE: no "segment_label_cluster_id" (or similar) column here.
            # This is an UNSUPERVISED clustering/segmentation feature table --
            # there is no ground-truth cluster assignment to ship, and a
            # column that is 100% blank in every row (as an earlier revision
            # of this table had) is misleading: it looks like a label column
            # that failed to populate, rather than what it actually was (a
            # placeholder reserved for a downstream model's OUTPUT). Cluster
            # assignments are produced by running a clustering model
            # (k-means, hierarchical, etc.) against these RFM-style features
            # after delivery -- see ml_dataset_documentation.md and
            # ml_leakage_prevention.md rule 9.4, which already prohibited
            # ever populating this column upstream (that would be target
            # leakage for exactly this kind of model); removing the column
            # entirely is the same rule taken to its conclusion for a
            # feature table that has no target to leak.
        })
SG_FIELDS = ["ml_record_id","customer_id","company_id","snapshot_date","recency_days_since_last_transaction",
    "frequency_transactions_last_12mo","monetary_total_last_12mo_inr","tenure_months_at_snapshot",
    "support_case_count_last_12mo","avg_satisfaction_score","product_category_diversity","industry_id",
    "company_size_band","customer_tier","contract_type"]
write_csv("customer_segmentation_dataset", seg_rows, SG_FIELDS)
print("customer_segmentation_dataset:", len(seg_rows), "rows across", len(customers), "customers")

# =============================================================================
# 5. churn_prediction_dataset.csv
#    Unit: (customer_id, renewal-decision snapshot). A naive fixed-calendar
#    "no transaction in the next 90 days" proxy was tried first and produced
#    a ~91% positive rate -- an artifact, not a real signal: Annual/Multi-Year
#    customers legitimately go many months between transactions by design, so
#    an arbitrary 90-day window mislabels almost every healthy customer as
#    "churned". The corrected proxy ties the label to each customer's own
#    contract cadence: one snapshot per renewal cycle, taken 30 days BEFORE
#    that cycle's renewal is due, and the label is whether a Renewal
#    transaction actually lands in a window around that due date. This is
#    the standard subscription-churn framing (will this renewal happen) and
#    matches how Phase-3 itself generated renew/non-renew decisions. No
#    customer_churn_events table exists yet, so this remains a documented
#    proxy, not a ground-truth churn flag. customer_status (the FINAL,
#    current status) is deliberately EXCLUDED as a feature -- we have no
#    historical status-as-of-date table, so using it would leak the end
#    state into earlier snapshots.
# =============================================================================
CADENCE_DAYS = {"Monthly": 30, "Annual": 365, "Multi-Year": 730}
LEAD_DAYS = 30       # snapshot is taken this many days before the renewal is due
GRACE_BEFORE = 15    # renewal txn counted if it lands from (due - GRACE_BEFORE)
GRACE_AFTER = 45     # ... through (due + GRACE_AFTER)
PRIORITY_SCORE = {"Low":1,"Medium":2,"High":3,"Critical":4}

churn_rows = []
for cust in customers:
    since = pdate(cust["customer_since"])
    cadence = CADENCE_DAYS[cust["contract_type"]]
    txns = sorted(txn_by_cust[cust["customer_id"]], key=lambda t: t["transaction_date"])
    cases = sorted(case_by_cust[cust["customer_id"]], key=lambda c: c["opened_at"])

    due = since + timedelta(days=cadence)
    while due + timedelta(days=GRACE_AFTER) <= TODAY:
        snap = due - timedelta(days=LEAD_DAYS)
        txns_to_date = [t for t in txns if pdate(t["transaction_date"]) <= snap]
        if not txns_to_date:
            due += timedelta(days=cadence); continue
        last_txn_date = max(pdate(t["transaction_date"]) for t in txns_to_date)
        cases_90d = [c for c in cases if pdate(c["opened_at"]) <= snap and pdate(c["opened_at"]) > snap - timedelta(days=90)]
        amt_last90 = sum(float(t["amount_inr"]) for t in txns_to_date if pdate(t["transaction_date"]) > snap - timedelta(days=90))
        amt_prev90 = sum(float(t["amount_inr"]) for t in txns_to_date if snap - timedelta(days=180) < pdate(t["transaction_date"]) <= snap - timedelta(days=90))

        renewal_in_window = any(
            t["transaction_type"] == "Renewal" and
            due - timedelta(days=GRACE_BEFORE) <= pdate(t["transaction_date"]) <= due + timedelta(days=GRACE_AFTER)
            for t in txns
        )
        label_churn = not renewal_in_window

        churn_rows.append({
            "ml_record_id": f"MLH-{len(churn_rows)+1:06d}", "customer_id": cust["customer_id"],
            "company_id": cust["company_id"], "observation_snapshot_date": snap.isoformat(),
            "renewal_due_date": due.isoformat(),
            "tenure_months_at_snapshot": round((snap - since).days / 30.44, 1),
            "days_since_last_transaction_at_snapshot": (snap - last_txn_date).days,
            "support_case_count_trailing_90d": len(cases_90d),
            "avg_case_priority_trailing_90d": round(sum(PRIORITY_SCORE[c["priority"]] for c in cases_90d)/len(cases_90d),2) if cases_90d else None,
            "contract_type": cust["contract_type"], "customer_tier": cust["customer_tier"],
            "transaction_amount_trailing_90d_inr": round(amt_last90,2),
            "transaction_amount_trend_90d_inr": round(amt_last90 - amt_prev90, 2),
            "label_churned_within_horizon": label_churn, "horizon_days": GRACE_AFTER + LEAD_DAYS,
        })
        if label_churn:
            break  # relationship ended at this cycle -- no further renewal checkpoints to evaluate
        due += timedelta(days=cadence)
time_split(churn_rows, "observation_snapshot_date")
CH_FIELDS = ["ml_record_id","customer_id","company_id","observation_snapshot_date","renewal_due_date",
    "tenure_months_at_snapshot","days_since_last_transaction_at_snapshot","support_case_count_trailing_90d",
    "avg_case_priority_trailing_90d","contract_type","customer_tier","transaction_amount_trailing_90d_inr",
    "transaction_amount_trend_90d_inr","label_churned_within_horizon","horizon_days","dataset_split"]
write_csv("churn_prediction_dataset", churn_rows, CH_FIELDS)
if churn_rows:
    print("churn_prediction_dataset:", len(churn_rows),
          "positive(churn) rate:", round(sum(r["label_churned_within_horizon"] for r in churn_rows)/len(churn_rows),3))
else:
    print("churn_prediction_dataset: 0 rows (insufficient future runway at this data scale)")
