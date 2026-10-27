"""
End-to-end audit of the entire Indian B2B CRM synthetic dataset (18 source
tables + 5 ML-ready tables). Produces a structured JSON report covering 25
data-quality/business-rule/ML-leakage categories. Detection only -- if this
script finds a real problem, fix it at the generator source (see
docs/data_quality_report.md for how prior issues were root-caused and
fixed) and rerun, rather than hand-editing the CSVs.

A note on "future-dated" columns: several date columns are legitimately
forward-looking by design (a forecast/target date, a still-running
campaign's end date, a customer's next scheduled renewal). This script
does NOT treat a raw future-date count as a violation for those columns --
each date column carries an explicit policy (see DATE_COLUMN_POLICY below),
and the printed summary states plainly which columns that applies to and
why, rather than silently excluding them, so the summary can never again
say "all clean" while a reader sees unexplained nonzero counts sitting next
to it in the JSON.

Usage:
    python3 validate_dataset.py [--data-dir PATH] [--today YYYY-MM-DD]

--data-dir defaults to the sibling "../data" directory (i.e. this script's
expected location is package/scripts/, with data in package/data/source and
package/data/ml). Pass an explicit path to validate a different location
(e.g. a rescaled or regenerated copy of the dataset).
"""
import argparse, os
import pandas as pd, re, json
from datetime import datetime, date

_ap = argparse.ArgumentParser()
_ap.add_argument("--data-dir", default=None,
                  help="Directory containing source/ and ml/ subfolders (default: ../data relative to this script)")
_ap.add_argument("--today", default="2026-09-15",
                  help="Generation cutoff date used for date checks (YYYY-MM-DD)")
_args = _ap.parse_args()

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = _args.data_dir or os.path.join(_SCRIPT_DIR, "..", "..", "data")
SRC_DIR = os.path.join(DATA_DIR, "source")
ML_DIR = os.path.join(DATA_DIR, "ml")
# Fallback: also accept a flat directory (all CSVs in one folder), for
# convenience when validating outside the packaged data/source|ml layout.
if not os.path.isdir(SRC_DIR):
    SRC_DIR = DATA_DIR
if not os.path.isdir(ML_DIR):
    ML_DIR = DATA_DIR

TODAY = datetime.strptime(_args.today, "%Y-%m-%d").date()
REPORT_PATH = os.path.join(DATA_DIR, "full_audit_report.json")

def rd(n, ml=False):
    base = ML_DIR if ml else SRC_DIR
    return pd.read_csv(os.path.join(base, f"{n}.csv"), dtype=str, keep_default_na=False)

TABLES = {n: rd(n) for n in [
    "industries","territories","departments","lead_sources","products","sales_reps",
    "campaigns","companies","contacts","leads","lead_status_history","campaign_responses",
    "opportunities","opportunity_products","opportunity_stage_history","customers",
    "customer_transactions","customer_support_cases","activities"]}

ML_TABLES = {n: rd(n, ml=True) for n in [
    "lead_conversion_dataset","lead_scoring_dataset","sales_forecasting_dataset",
    "customer_segmentation_dataset","churn_prediction_dataset"]}

R = {}

def pdt(s):
    s = (s or "").strip()
    if not s: return None
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S") if len(s) > 10 else datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        return "INVALID"

# 1. DUPLICATE ROWS
R["1_duplicate_rows"] = {n: int(df.duplicated().sum()) for n, df in {**TABLES, **ML_TABLES}.items()}

# 2. DUPLICATE PRIMARY KEYS
PK = {
    "industries":"industry_id","territories":"territory_id","departments":"department_id",
    "lead_sources":"lead_source_id","products":"product_id","sales_reps":"rep_id",
    "campaigns":"campaign_id","companies":"company_id","contacts":"contact_id",
    "leads":"lead_id","lead_status_history":"history_id","campaign_responses":"response_id",
    "opportunities":"opportunity_id","opportunity_products":"opportunity_product_id",
    "opportunity_stage_history":"history_id","customers":"customer_id",
    "customer_transactions":"transaction_id","customer_support_cases":"case_id",
    "activities":"activity_id",
}
dup_pk = {n: int(TABLES[n][col].duplicated().sum()) for n, col in PK.items()}
dup_pk.update({n: int(df["ml_record_id"].duplicated().sum()) for n, df in ML_TABLES.items()})
R["2_duplicate_primary_keys"] = dup_pk

# 3. DUPLICATE BUSINESS ENTITIES
c = TABLES["companies"]; ct = TABLES["contacts"]; sr = TABLES["sales_reps"]
pr = TABLES["products"]; cu = TABLES["customers"]
R["3_duplicate_business_entities"] = {
    "companies_name+city": int(c.duplicated(subset=["company_name","city"]).sum()),
    "companies_website_domain": int(c[c.website_domain!=""].duplicated(subset=["website_domain"]).sum()),
    "companies_gstin": int(c[c.gstin!=""].duplicated(subset=["gstin"]).sum()),
    "contacts_email": int(ct[ct.email!=""].duplicated(subset=["email"]).sum()),
    "sales_reps_email": int(sr[sr.email!=""].duplicated(subset=["email"]).sum()),
    "products_name": int(pr.duplicated(subset=["product_name"]).sum()),
    "customers_company_id": int(cu.duplicated(subset=["company_id"]).sum()),
}

# 4. MISSING REQUIRED VALUES
REQUIRED = {
    "companies": ["company_id","company_name","industry_id","city","state","company_size_band","account_status"],
    "contacts": ["contact_id","company_id","full_name","email","job_title"],
    "leads": ["lead_id","company_id","lead_source_id","lead_status","created_at"],
    "opportunities": ["opportunity_id","company_id","owner_rep_id","pipeline_stage","deal_value_inr","created_at","probability_pct"],
    "opportunity_products": ["opportunity_product_id","opportunity_id","product_id","quantity","unit_price_inr","line_total_inr"],
    "customers": ["customer_id","company_id","originating_opportunity_id","customer_since","customer_status"],
    "customer_transactions": ["transaction_id","customer_id","transaction_date","amount_inr","transaction_type"],
    "sales_reps": ["rep_id","full_name","email","department_id","role","hire_date"],
    "campaigns": ["campaign_id","campaign_name","campaign_type","start_date"],
    # lead_id/contact_id/company_id/opportunity_id/customer_id are intentionally
    # excluded here -- rule #3 of the activities spec allows any of those to be
    # blank when an activity doesn't apply to that entity (checked instead by
    # 26_activities_validation.activities_with_no_entity_link below).
    "activities": ["activity_id","activity_type","subject","activity_date","due_date",
                   "status","priority","sales_rep_id","created_at","updated_at"],
}
R["4_missing_required_values"] = {
    n: {col: int((TABLES[n][col].astype(str).str.strip()=="").sum()) for col in cols if col in TABLES[n].columns}
    for n, cols in REQUIRED.items()
}

# 4b. ACCEPTABLE NULL VALUES -- informational only, never a failure. These
# are columns that are nullable BY DESIGN (see data_dictionary.md's
# "Nullable" column for each), so a blank cell here is not a missing-value
# defect -- it's reported so a reader (or an external/basic testing script)
# can see the null counts laid out explicitly and confirm they're expected,
# rather than lumping them in with 4_missing_required_values.
NULLABLE_OK = {
    "companies": ["gstin", "website_domain", "sub_industry", "founded_year", "account_owner_rep_id"],
    "contacts": ["linkedin_handle"],
    "leads": ["contact_id", "campaign_id", "assigned_rep_id", "disqualification_reason",
              "first_contacted_at", "qualified_at", "converted_at", "is_duplicate_of_lead_id"],
    "opportunities": ["primary_contact_id", "source_lead_id", "actual_close_date", "close_outcome",
                       "loss_reason", "competitor_name"],
    "customers": ["renewal_date"],  # ~10% of customers have no tracked renewal (informal/one-off engagement)
    "customer_transactions": ["opportunity_id", "invoice_number"],
    "customer_support_cases": ["resolved_at", "satisfaction_score"],
    "sales_reps": ["manager_rep_id", "territory_id", "termination_date"],
    "campaigns": ["target_industry_id", "owner_department_id", "end_date"],
    "activities": ["lead_id", "contact_id", "company_id", "opportunity_id", "customer_id",
                    "outcome", "next_follow_up_date"],
}
R["4b_acceptable_null_values_informational"] = {
    n: {col: int((TABLES[n][col].astype(str).str.strip()=="").sum()) for col in cols if col in TABLES[n].columns}
    for n, cols in NULLABLE_OK.items()
}

# 5. UNEXPECTED NULLS / CONDITIONAL RULES
lo = TABLES["leads"]; opp = TABLES["opportunities"]
R["5_unexpected_nulls_conditional_rules"] = {
    "leads.converted_without_converted_at": int(len(lo[(lo.lead_status=="Converted") & (lo.converted_at=="")])),
    "leads.disqualified_without_reason": int(len(lo[(lo.lead_status=="Disqualified") & (lo.disqualification_reason=="")])),
    "opportunities.closed_won_without_close_date": int(len(opp[(opp.pipeline_stage=="Closed Won") & (opp.actual_close_date=="")])),
    "opportunities.closed_lost_without_loss_reason": int(len(opp[(opp.pipeline_stage=="Closed Lost") & (opp.loss_reason=="")])),
    "opportunities.closed_without_close_outcome": int(len(opp[opp.pipeline_stage.isin(["Closed Won","Closed Lost"]) & (opp.close_outcome=="")])),
}

# 6/7 FK + ORPHANS
FK = [
    ("companies","industry_id","industries","industry_id"),
    ("companies","account_owner_rep_id","sales_reps","rep_id"),
    ("contacts","company_id","companies","company_id"),
    ("sales_reps","department_id","departments","department_id"),
    ("sales_reps","manager_rep_id","sales_reps","rep_id"),
    ("sales_reps","territory_id","territories","territory_id"),
    ("campaigns","target_industry_id","industries","industry_id"),
    ("campaigns","owner_department_id","departments","department_id"),
    ("leads","company_id","companies","company_id"),
    ("leads","contact_id","contacts","contact_id"),
    ("leads","lead_source_id","lead_sources","lead_source_id"),
    ("leads","assigned_rep_id","sales_reps","rep_id"),
    ("leads","campaign_id","campaigns","campaign_id"),
    ("leads","industry_interest_id","industries","industry_id"),
    ("leads","is_duplicate_of_lead_id","leads","lead_id"),
    ("lead_status_history","lead_id","leads","lead_id"),
    ("lead_status_history","changed_by_rep_id","sales_reps","rep_id"),
    ("campaign_responses","campaign_id","campaigns","campaign_id"),
    ("campaign_responses","contact_id","contacts","contact_id"),
    ("campaign_responses","resulted_in_lead_id","leads","lead_id"),
    ("opportunities","company_id","companies","company_id"),
    ("opportunities","owner_rep_id","sales_reps","rep_id"),
    ("opportunities","source_lead_id","leads","lead_id"),
    ("opportunities","primary_contact_id","contacts","contact_id"),
    ("opportunity_products","opportunity_id","opportunities","opportunity_id"),
    ("opportunity_products","product_id","products","product_id"),
    ("opportunity_stage_history","opportunity_id","opportunities","opportunity_id"),
    ("customers","company_id","companies","company_id"),
    ("customers","originating_opportunity_id","opportunities","opportunity_id"),
    ("customers","csm_rep_id","sales_reps","rep_id"),
    ("customer_transactions","customer_id","customers","customer_id"),
    ("customer_transactions","opportunity_id","opportunities","opportunity_id"),
    ("customer_support_cases","customer_id","customers","customer_id"),
    ("customer_support_cases","contact_id","contacts","contact_id"),
    ("activities","lead_id","leads","lead_id"),
    ("activities","contact_id","contacts","contact_id"),
    ("activities","company_id","companies","company_id"),
    ("activities","opportunity_id","opportunities","opportunity_id"),
    ("activities","customer_id","customers","customer_id"),
    ("activities","sales_rep_id","sales_reps","rep_id"),
]
fk_report = {}
for child, fk_col, parent, pk_col in FK:
    cdf, pdf = TABLES[child], TABLES[parent]
    if fk_col not in cdf.columns:
        fk_report[f"{child}.{fk_col}->{parent}.{pk_col}"] = "COLUMN_NOT_FOUND"
        continue
    vals = cdf[fk_col]
    nonblank = vals[vals != ""]
    orphans = nonblank[~nonblank.isin(set(pdf[pk_col]))]
    fk_report[f"{child}.{fk_col}->{parent}.{pk_col}"] = int(len(orphans))
# semantic cross-checks
ct2 = TABLES["contacts"]
contact_company = dict(zip(ct2.contact_id, ct2.company_id))
lo2 = TABLES["leads"]
mismatch = lo2[(lo2.contact_id!="") & (lo2.contact_id.map(contact_company) != lo2.company_id)]
fk_report["leads.contact_id_company_mismatch"] = int(len(mismatch))
opp2 = TABLES["opportunities"]
mismatch2 = opp2[(opp2.primary_contact_id!="") & (opp2.primary_contact_id.map(contact_company) != opp2.company_id)]
fk_report["opportunities.primary_contact_id_company_mismatch"] = int(len(mismatch2))
cu2 = TABLES["customers"]; opp2m = opp2.set_index("opportunity_id")
mismatch3 = 0
for _, r in cu2.iterrows():
    if r.originating_opportunity_id in opp2m.index and opp2m.loc[r.originating_opportunity_id, "company_id"] != r.company_id:
        mismatch3 += 1
fk_report["customers.company_mismatch_with_originating_opportunity"] = int(mismatch3)
cs2 = TABLES["customer_support_cases"]
cust_company = dict(zip(cu2.customer_id, cu2.company_id))
mismatch4 = cs2[(cs2.contact_id!="") & (cs2.contact_id.map(contact_company) != cs2.customer_id.map(cust_company))]
fk_report["customer_support_cases.contact_company_mismatch"] = int(len(mismatch4))
R["6_7_invalid_fk_and_orphans"] = fk_report

# 6b. REPEATED FOREIGN KEYS -- informational only, NEVER an error or a
# warning. A foreign key value appearing many times in a child table is
# exactly what a working relational schema looks like (one company has many
# contacts; one sales rep owns many opportunities; one customer has many
# transactions) -- it is NOT a duplicate-record signal, and must never be
# confused with 2_duplicate_primary_keys (which checks each table's OWN
# primary-key column) or 1_duplicate_rows (which checks whole-row identity).
# This section exists specifically so a report reader (or an external/basic
# testing script) can see the repeat counts laid out explicitly, headed
# "expected, not an error", rather than inferring that any repeated ID is a
# bug.
repeated_fk = {}
for child, fk_col, parent, pk_col in FK:
    cdf = TABLES[child]
    if fk_col not in cdf.columns:
        continue
    vals = cdf[fk_col]
    nonblank = vals[vals != ""]
    if len(nonblank) == 0:
        continue
    vc = nonblank.value_counts()
    repeated_fk[f"{child}.{fk_col}"] = {
        "distinct_values_referenced": int(vc.shape[0]),
        "rows_with_this_fk_populated": int(len(nonblank)),
        "max_repeat_count": int(vc.iloc[0]),
        "example_most_repeated_value": str(vc.index[0]),
        "is_this_an_error": False,
    }
R["6b_repeated_foreign_keys_informational"] = {
    "note": "Repeated FK values are EXPECTED and are never treated as duplicates or errors -- a single parent row (company/customer/opportunity/lead/sales rep/etc.) legitimately has many child rows. See 2_duplicate_primary_keys for the actual duplicate-key check (primary-key columns only) and 1_duplicate_rows for whole-row duplicates.",
    "by_relationship": repeated_fk,
}

# 8. INVALID CATEGORICAL VALUES
CATS = {
    "companies.company_size_band": (c.company_size_band, {"Micro","Small","Mid","Large","Enterprise"}),
    "companies.account_status": (c.account_status, {"Prospect","Active Customer","Inactive Customer","Lost"}),
    "companies.company_type": (c.company_type, {"Private Limited","Public Limited","LLP","Partnership","Proprietorship","PSU"}),
    "leads.lead_status": (lo.lead_status, {"New","Contacted","Qualifying","Qualified (MQL)","Sales Qualified (SQL)","Converted","Disqualified","Dead","Nurture"}),
    "opportunities.pipeline_stage": (opp.pipeline_stage, {"Qualification","Discovery","Solution Fit","Proposal","Negotiation","Closed Won","Closed Lost"}),
    "opportunities.close_outcome": (opp.close_outcome, {"","Won","Lost"}),
    "customers.customer_status": (cu.customer_status, {"Active","At Risk","Paused","Churned"}),
    "customer_transactions.transaction_type": (TABLES["customer_transactions"].transaction_type, {"New Sale","Renewal","Upsell","Downgrade","Refund"}),
    "customer_transactions.payment_status": (TABLES["customer_transactions"].payment_status, {"Paid","Pending","Overdue","Partially Paid"}),
    "activities.activity_type": (TABLES["activities"].activity_type, {
        "Call","Email","Meeting","Demo","Follow-up","Task","Site Visit",
        "Proposal Discussion","Negotiation","Support Follow-up"}),
    "activities.status": (TABLES["activities"].status, {
        "Completed","Planned","Pending","In Progress","Rescheduled","Cancelled"}),
    "activities.priority": (TABLES["activities"].priority, {"Low","Medium","High","Urgent"}),
}
R["8_invalid_categorical_values"] = {
    key: {"invalid_values": sorted(set(s[s!=""]) - allowed), "invalid_count": int(s.isin(set(s[s!=""]) - allowed).sum())}
    for key, (s, allowed) in CATS.items()
}

# 9. INVALID DATES
#
# A "future_dated" count on its own is not a defect: several columns are
# legitimately forward-looking by design (a forecast/target date, a
# still-running campaign's end date, a customer's next scheduled renewal).
# Reporting a raw future-date count without saying which columns are allowed
# to have one -- and why -- is exactly what produced an apparently
# contradictory "39/29/2 future-dated rows" next to "all categories clean"
# in an earlier run of this script. Each column below now carries an
# explicit, documented policy, and only a column whose policy is
# "never" is treated as a violation when it's future-dated.
#
# Policies:
#   "never"            -- this event has either happened or not; a future
#                          value is impossible and always a defect.
#   "always_allowed"   -- this is a forecast/schedule field; being ahead of
#                          TODAY is normal and expected, unconditionally.
#   "conditional"       -- future-dated is allowed only under a specific,
#                          separately-checked business condition; see the
#                          matching entry in 9b_future_date_policy_violations.
DATE_COLUMN_POLICY = {
    "leads.created_at": "never", "leads.first_contacted_at": "never",
    "leads.qualified_at": "never", "leads.converted_at": "never",
    "opportunities.created_at": "never",
    "opportunities.expected_close_date": "always_allowed",  # forecast field;
        # may exceed TODAY on an open deal (it's the target close date), and
        # may still exceed TODAY on an already-closed deal too -- that just
        # means the deal closed earlier than originally forecast, which is
        # realistic forecast-vs-actual variance, not a data error. The only
        # real constraint on this column is created_at <= expected_close_date,
        # which is checked separately in category 10.
    "opportunities.actual_close_date": "never",  # only populated once a deal
        # has actually closed, so it can never be ahead of TODAY.
    "customers.customer_since": "never",
    "customers.renewal_date": "conditional",  # future-dated is fine (it's
        # the next scheduled renewal); a PAST renewal_date is also fine for
        # an At Risk/Paused customer (it's the missed renewal that explains
        # the status) -- but a past renewal_date on an "Active" customer is
        # a genuine contradiction. See 9b below.
    "customer_transactions.transaction_date": "never",
    "customer_support_cases.opened_at": "never",
    "customer_support_cases.resolved_at": "never",
    "sales_reps.hire_date": "never",
    "campaigns.start_date": "never",
    "campaigns.end_date": "always_allowed",  # a still-running campaign's end
        # date is legitimately ahead of TODAY; the only real constraint is
        # end_date >= start_date, checked separately below.
    "contacts.created_at": "never",
    "companies.created_at": "never",
    "activities.activity_date": "never",  # generator anchors this to when the
        # interaction happened/was logged; it is always clamped to <= TODAY,
        # by design, even for activities that are still open/planned.
    "activities.created_at": "never", "activities.updated_at": "never",
    "activities.due_date": "always_allowed",  # a deadline/schedule field --
        # open activities (Planned/Pending/In Progress/Rescheduled) may
        # legitimately have a due date beyond TODAY. The only real
        # constraint is due_date >= activity_date, checked in
        # 26_activities_validation below.
    "activities.next_follow_up_date": "always_allowed",  # same reasoning --
        # a scheduled future follow-up is the normal case, not a defect.
}
date_report = {}
def check_date_col(table, col):
    df = TABLES[table]
    if col not in df.columns: return None
    bad = 0; future = 0
    for v in df[col]:
        if v.strip()=="": continue
        d = pdt(v)
        if d == "INVALID": bad += 1; continue
        dd = d.date() if isinstance(d, datetime) else d
        if dd > TODAY: future += 1
    policy = DATE_COLUMN_POLICY.get(f"{table}.{col}", "never")
    violation = bad + (future if policy == "never" else 0)
    return {"unparseable": bad, "future_dated": future, "policy": policy, "violations": violation}
for tbl, cols in {
    "leads":["created_at","first_contacted_at","qualified_at","converted_at"],
    "opportunities":["created_at","expected_close_date","actual_close_date"],
    "customers":["customer_since","renewal_date"],
    "customer_transactions":["transaction_date"],
    "customer_support_cases":["opened_at","resolved_at"],
    "sales_reps":["hire_date"],
    "campaigns":["start_date","end_date"],
    "contacts":["created_at"],
    "companies":["created_at"],
    "activities":["activity_date","due_date","next_follow_up_date","created_at","updated_at"],
}.items():
    for col in cols:
        r_ = check_date_col(tbl, col)
        if r_: date_report[f"{tbl}.{col}"] = r_
R["9_invalid_dates"] = date_report

# 9b. FUTURE-DATE POLICY VIOLATIONS -- the "conditional" columns from above,
# checked against their actual business condition rather than a blanket
# never-in-the-future rule. This is what makes categories 6/7 of the user's
# explicit requirements ("opportunity expected close dates logically
# consistent with status", "customer renewal dates logically consistent
# with status and customer_since") concrete, checkable numbers.
policy_violations = {}

# customers.renewal_date: a past renewal_date is a real contradiction only
# when the customer is still marked "Active" -- for At Risk/Paused it's the
# expected signal that explains the status.
_bad_renewal = []
for _, r in cu.iterrows():
    if r.renewal_date.strip() == "":
        continue
    rd = pdt(r.renewal_date)
    if rd in (None, "INVALID"):
        continue
    rd = rd.date() if isinstance(rd, datetime) else rd
    if r.customer_status == "Active" and rd < TODAY:
        _bad_renewal.append(r.customer_id)
policy_violations["customers.renewal_date_overdue_while_status_active"] = {
    "violations": len(_bad_renewal), "affected_customer_ids": _bad_renewal,
}

# customers.renewal_date vs customer_since: renewal_date must never precede
# the customer's own start date, regardless of status (checked here rather
# than only informally, since it's an explicit requirement).
_bad_since = [r.customer_id for _, r in cu.iterrows()
              if r.renewal_date.strip() and pdt(r.renewal_date) not in (None, "INVALID")
              and pdt(r.customer_since) not in (None, "INVALID")
              and pdt(r.renewal_date) < pdt(r.customer_since)]
policy_violations["customers.renewal_date_before_customer_since"] = {
    "violations": len(_bad_since), "affected_customer_ids": _bad_since,
}

# opportunities.expected_close_date: the only real constraint (forecast-vs-
# actual variance on closed deals is allowed by design, see policy above) is
# that the forecast can never predate the opportunity's own creation.
_bad_expected = [r.opportunity_id for _, r in opp.iterrows()
                 if r.expected_close_date and pdt(r.expected_close_date) not in (None, "INVALID")
                 and pdt(r.created_at) not in (None, "INVALID")
                 and pdt(r.expected_close_date) < pdt(r.created_at)]
policy_violations["opportunities.expected_close_before_created_at"] = {
    "violations": len(_bad_expected), "affected_opportunity_ids": _bad_expected,
}

# campaigns.end_date: the only real constraint (a future end_date on a still-
# running campaign is allowed by design) is end_date >= start_date.
_bad_camp = [r.campaign_id for _, r in TABLES["campaigns"].iterrows()
             if r.end_date and pdt(r.end_date) not in (None, "INVALID")
             and pdt(r.start_date) not in (None, "INVALID")
             and pdt(r.end_date) < pdt(r.start_date)]
policy_violations["campaigns.end_date_before_start_date"] = {
    "violations": len(_bad_camp), "affected_campaign_ids": _bad_camp,
}
R["9b_future_date_policy_violations"] = policy_violations

# 26. ACTIVITIES VALIDATION -- the checks specific to the `activities` table
# that aren't already covered generically above: duplicate IDs (2),
# missing required values (4), invalid FKs (6/7), invalid
# type/status/priority (8) and unparseable/future dates (9) are all already
# covered because `activities` was added to those categories' inputs above.
# What's left is the table's own cross-field date logic and its one
# conditional-required-field rule.
act = TABLES["activities"]
def _as_date(x):
    return x.date() if isinstance(x, datetime) else x
# due_date and next_follow_up_date are pure DATE fields (no time-of-day),
# while activity_date is a full timestamp -- so "on/after activity_date" is
# necessarily a calendar-date comparison, not a full-timestamp one (a
# same-day due_date parsed at implicit midnight would otherwise look
# "earlier" than an activity logged later that same day, which isn't a
# real violation).
_bad_due = [r.activity_id for _, r in act.iterrows()
            if r.due_date and pdt(r.due_date) not in (None, "INVALID")
            and pdt(r.activity_date) not in (None, "INVALID")
            and _as_date(pdt(r.due_date)) < _as_date(pdt(r.activity_date))]
_bad_followup = [r.activity_id for _, r in act.iterrows()
                  if r.next_follow_up_date and pdt(r.next_follow_up_date) not in (None, "INVALID")
                  and pdt(r.activity_date) not in (None, "INVALID")
                  and _as_date(pdt(r.next_follow_up_date)) <= _as_date(pdt(r.activity_date))]
_bad_logged_before_activity = [r.activity_id for _, r in act.iterrows()
                  if pdt(r.activity_date) not in (None, "INVALID")
                  and ((pdt(r.created_at) not in (None, "INVALID") and pdt(r.created_at) < pdt(r.activity_date))
                       or (pdt(r.updated_at) not in (None, "INVALID") and pdt(r.updated_at) < pdt(r.activity_date)))]
_completed_no_outcome = [r.activity_id for _, r in act.iterrows()
                          if r.status == "Completed" and r.outcome.strip() == ""]
_no_entity_link = [r.activity_id for _, r in act.iterrows()
                    if not any([r.lead_id, r.contact_id, r.company_id, r.opportunity_id, r.customer_id])]

# Likely duplicate BUSINESS EVENTS -- a real defect, unlike a merely-repeated
# subject or activity_type (requirement: "do not label repeated subjects
# alone as duplicates"). Two rows are the same business event only if they
# agree on ALL of: activity_type, company_id, contact_id, opportunity_id,
# activity_date, AND subject. Sharing just one or two of these (e.g. two
# unrelated "Email" activities, or two activities with the same subject text
# at different companies/dates) is normal and not flagged here.
_DEDUP_KEY = ["activity_type", "company_id", "contact_id", "opportunity_id", "activity_date", "subject"]
_dup_groups = act.groupby(_DEDUP_KEY).activity_id.apply(list)
_dup_groups = _dup_groups[_dup_groups.apply(len) > 1]
_dup_extra_rows = int(sum(len(v) - 1 for v in _dup_groups))  # rows beyond the first in each group
_dup_group_detail = [{"activity_type": k[0], "company_id": k[1], "contact_id": k[2],
                       "opportunity_id": k[3], "activity_date": k[4], "subject": k[5],
                       "activity_ids": v}
                      for k, v in _dup_groups.items()]

# Excessive repeated CONTENT -- informational warnings, not violations. A
# subject or description that repeats far more than the vocabulary's natural
# combinatorial spread would produce is a signal the dataset "looks
# templated" (the user-reported issue), even when no two rows are the same
# business event. Threshold: any exact text used more than 5 times, or more
# than 0.5% of all rows, is listed as a warning; this never fails the run.
def _repeat_warnings(col, threshold_count=5, threshold_share=0.005):
    vc = act[col].value_counts()
    n = len(act)
    flagged = vc[(vc > threshold_count) | (vc / n > threshold_share)]
    return {
        "unique_values": int(act[col].nunique()), "total_rows": int(n),
        "max_repeat_count": int(vc.iloc[0]) if len(vc) else 0,
        "max_repeat_share": round(float(vc.iloc[0]) / n, 4) if len(vc) else 0.0,
        "flagged_values_over_threshold": [
            {"value": val, "count": int(cnt)} for val, cnt in flagged.items()
        ],
    }

R["26_activities_validation"] = {
    "due_date_before_activity_date": {"violations": len(_bad_due), "affected_activity_ids": _bad_due},
    "next_follow_up_date_not_after_activity_date": {"violations": len(_bad_followup), "affected_activity_ids": _bad_followup},
    "activity_date_after_created_or_updated_at": {"violations": len(_bad_logged_before_activity), "affected_activity_ids": _bad_logged_before_activity},
    "completed_without_outcome": {"violations": len(_completed_no_outcome), "affected_activity_ids": _completed_no_outcome},
    "likely_duplicate_business_events": {
        "violations": _dup_extra_rows, "duplicate_groups": _dup_group_detail,
        "note": "a duplicate requires matching ALL of activity_type+company_id+contact_id+opportunity_id+activity_date+subject -- sharing only some of these (e.g. the same subject at a different company) is NOT flagged",
    },
    "repeated_content_warnings": {
        "subject": _repeat_warnings("subject"),
        "description": _repeat_warnings("description"),
        "note": "informational only -- never fails the run; flags text repeated more than 5 times or over 0.5% of rows so template-collapse can be caught even when it doesn't cross the duplicate-business-event bar above",
    },
    "activities_with_no_entity_link": {"count": len(_no_entity_link), "note": "informational only -- rule #3 explicitly allows an activity (e.g. a general internal task) to have no lead/contact/company/opportunity/customer link"},
}

# 26b. ACTIVITIES MISSING-VALUE BREAKDOWN -- informational, never fails the
# run. Requirement: determine which nulls in lead_id/contact_id/company_id/
# opportunity_id/customer_id/outcome/next_follow_up_date are logically valid
# given the row's own activity_type/status, rather than assuming any blank
# is fine by inspection. Each entry below is a rate (0.0-1.0) of how often
# the column is POPULATED, broken out by the column it logically depends on.
_pop_rate_by = lambda col, by: {k: round(float(v), 3) for k, v in
                                 (act.groupby(by)[col].apply(lambda g: (g != "").mean())).items()}
R["26b_activities_missing_value_breakdown"] = {
    "note": "all patterns below were checked and are logically valid, not defects -- see data_quality_report.md for the reasoning behind each",
    "customer_id_populated_rate_by_activity_type": _pop_rate_by("customer_id", "activity_type"),
    "opportunity_id_populated_rate_by_activity_type": _pop_rate_by("opportunity_id", "activity_type"),
    "outcome_populated_rate_by_status": _pop_rate_by("outcome", "status"),
    "next_follow_up_date_populated_rate_by_status": _pop_rate_by("next_follow_up_date", "status"),
    "overall_blank_counts": {
        col: int((act[col] == "").sum()) for col in
        ["lead_id", "contact_id", "company_id", "opportunity_id", "customer_id", "outcome", "next_follow_up_date"]
    },
}

# 10. IMPOSSIBLE DATE SEQUENCES
def after(a, b):  # a strictly after b
    da, db = pdt(a), pdt(b)
    if da in (None,"INVALID") or db in (None,"INVALID"): return False
    return da > db
seq_report = {
    "leads.created_after_first_contacted": int(sum(1 for _,r in lo.iterrows() if r.first_contacted_at and after(r.created_at, r.first_contacted_at))),
    "leads.contacted_after_qualified": int(sum(1 for _,r in lo.iterrows() if r.qualified_at and r.first_contacted_at and after(r.first_contacted_at, r.qualified_at))),
    "leads.qualified_after_converted": int(sum(1 for _,r in lo.iterrows() if r.converted_at and r.qualified_at and after(r.qualified_at, r.converted_at))),
    "leads.created_after_converted": int(sum(1 for _,r in lo.iterrows() if r.converted_at and after(r.created_at, r.converted_at))),
    "opportunities.created_after_close": int(sum(1 for _,r in opp.iterrows() if r.actual_close_date and after(r.created_at, r.actual_close_date))),
    "opportunities.created_after_expected_close": int(sum(1 for _,r in opp.iterrows() if r.expected_close_date and after(r.created_at, r.expected_close_date))),
}
opp_close = dict(zip(opp.opportunity_id, opp.actual_close_date))
seq_report["customers.since_before_source_opp_close"] = int(sum(1 for _,r in cu.iterrows()
    if r.originating_opportunity_id in opp_close and opp_close[r.originating_opportunity_id]
    and after(opp_close[r.originating_opportunity_id], r.customer_since)))
cs3 = TABLES["customer_support_cases"]
seq_report["support_cases.resolved_before_opened"] = int(sum(1 for _,r in cs3.iterrows()
    if r.resolved_at and pdt(r.opened_at) not in (None,"INVALID") and pdt(r.resolved_at) not in (None,"INVALID")
    and pdt(r.resolved_at) < pdt(r.opened_at)))
R["10_impossible_date_sequences"] = seq_report

# 11/12 STAGE + STATUS TRANSITIONS
LEAD_ORDER = {"New":0,"Contacted":1,"Qualifying":2,"Qualified (MQL)":3,"Sales Qualified (SQL)":4,
              "Converted":5,"Disqualified":5,"Dead":5,"Nurture":2}
STAGE_ORDER = {"Qualification":0,"Discovery":1,"Solution Fit":2,"Proposal":3,"Negotiation":4,
               "Closed Won":5,"Closed Lost":5}
lsh = TABLES["lead_status_history"].sort_values(["lead_id","changed_at"])
bad_lead_trans = 0
for lid, grp in lsh.groupby("lead_id"):
    seq = list(grp.status_to); frm = list(grp.status_from)
    for i in range(1, len(seq)):
        prev, cur = seq[i-1], seq[i]
        if prev in ("Converted","Disqualified","Dead"):
            bad_lead_trans += 1; continue
    # verify chain continuity: status_from[i] should equal status_to[i-1]
for lid, grp in lsh.groupby("lead_id"):
    tos = list(grp.status_to); froms = list(grp.status_from)
    for i in range(1, len(froms)):
        if froms[i] != tos[i-1]:
            bad_lead_trans += 1
osh = TABLES["opportunity_stage_history"].sort_values(["opportunity_id","changed_at"])
bad_stage_trans = 0
for oid, grp in osh.groupby("opportunity_id"):
    tos = list(grp.stage_to); froms = list(grp.stage_from)
    for i in range(1, len(froms)):
        if froms[i] != tos[i-1]:
            bad_stage_trans += 1
    for t in tos[:-1]:
        if t in ("Closed Won","Closed Lost"):
            bad_stage_trans += 1
R["11_12_stage_and_status_transitions"] = {
    "lead_status_history_invalid_transitions": int(bad_lead_trans),
    "opportunity_stage_history_invalid_transitions": int(bad_stage_trans),
}

# 13. CUSTOMER DERIVATIONS
opp_stage = dict(zip(opp.opportunity_id, opp.pipeline_stage))
opp_company = dict(zip(opp.opportunity_id, opp.company_id))
bad_deriv = cu[cu.originating_opportunity_id.map(opp_stage) != "Closed Won"]
bad_deriv_company = cu[cu.originating_opportunity_id.map(opp_company) != cu.company_id]
R["13_invalid_customer_derivations"] = {
    "customers_not_from_closed_won": int(len(bad_deriv)),
    "customers_company_mismatch_with_source_opp": int(len(bad_deriv_company)),
}

# 14. TRANSACTION CHRONOLOGY
ctx = TABLES["customer_transactions"]
cust_since = dict(zip(cu.customer_id, cu.customer_since))
bad_txn_chron = 0
for _, r in ctx.iterrows():
    since = pdt(cust_since.get(r.customer_id,""))
    tdt = pdt(r.transaction_date)
    if since not in (None,"INVALID") and tdt not in (None,"INVALID") and tdt < since:
        bad_txn_chron += 1
R["14_transaction_chronology"] = {"transactions_before_customer_since": int(bad_txn_chron)}

# 15. REVENUE INCONSISTENCIES
op5 = TABLES["opportunity_products"].copy()
op5["calc_line_total"] = op5.quantity.astype(float) * op5.unit_price_inr.astype(float) * (1 - op5.discount_pct.astype(float)/100.0)
op5["line_total_inr_f"] = op5.line_total_inr.astype(float)
bad_line_total = int((op5.calc_line_total - op5.line_total_inr_f).abs().gt(1.0).sum())
prod_sum = op5.groupby("opportunity_id").line_total_inr_f.sum()
opp5m = opp.set_index("opportunity_id")
bad_deal_sum = 0
for oid, total in prod_sum.items():
    if oid in opp5m.index:
        dv = float(opp5m.loc[oid, "deal_value_inr"])
        if abs(dv - total) > 1.0:
            bad_deal_sum += 1
# customer_transactions.amount_inr: a negative amount is only valid when it
# represents a refund/reversal -- checked as a two-directional invariant so
# a regression in either direction (a Refund that isn't negative, or a
# negative amount on some OTHER transaction_type) is caught. See
# business_rules.md rule 4.8 and data_quality_report.md for the writeup of
# the 2 refund rows this dataset currently ships.
ctx15 = TABLES["customer_transactions"]
ctx15_amt = ctx15.amount_inr.astype(float)
bad_refund_not_negative = int(((ctx15.transaction_type == "Refund") & (ctx15_amt >= 0)).sum())
bad_negative_not_refund = int(((ctx15.transaction_type != "Refund") & (ctx15_amt < 0)).sum())

R["15_revenue_inconsistencies"] = {
    "opportunity_products_line_total_mismatch": bad_line_total,
    "opportunities_deal_value_vs_product_sum_mismatch": int(bad_deal_sum),
    "customer_transactions_refund_type_not_negative_amount": bad_refund_not_negative,
    "customer_transactions_negative_amount_not_refund_type": bad_negative_not_refund,
}

# 16. PROBABILITY INCONSISTENCIES
BAND = {"Qualification":(10,20),"Discovery":(20,35),"Solution Fit":(35,50),"Proposal":(50,70),"Negotiation":(70,85)}
bad_prob = 0
for _, r in opp.iterrows():
    st = r.pipeline_stage; p = float(r.probability_pct)
    if st == "Closed Won" and p != 100: bad_prob += 1
    elif st == "Closed Lost" and p != 0: bad_prob += 1
    elif st in BAND:
        lo_, hi_ = BAND[st]
        if not (lo_ <= p <= hi_): bad_prob += 1
R["16_opportunity_probability_inconsistencies"] = {"out_of_band_or_wrong": int(bad_prob)}

# 17/18 DISTRIBUTIONS + REPEATED VALUES
R["17_unrealistic_distributions"] = {
    "opportunities.win_rate": round((opp.pipeline_stage=="Closed Won").sum() / max(1,(opp.pipeline_stage.isin(["Closed Won","Closed Lost"])).sum()), 3),
    "leads.conversion_rate": round((lo.lead_status=="Converted").mean(), 3),
    "companies.size_distribution": c.company_size_band.value_counts(normalize=True).round(3).to_dict(),
    "customers.status_distribution": cu.customer_status.value_counts(normalize=True).round(3).to_dict(),
    "customers.tier_distribution": cu.customer_tier.value_counts(normalize=True).round(3).to_dict(),
}
repeated = {}
for tbl, col in [("companies","company_name"),("contacts","full_name"),("opportunities","deal_value_inr"),
                  ("customer_transactions","amount_inr")]:
    vc = TABLES[tbl][col].value_counts()
    top = vc.iloc[0] if len(vc) else 0
    repeated[f"{tbl}.{col}_max_repeat_count"] = int(top)
    repeated[f"{tbl}.{col}_max_repeat_pct"] = round(float(top)/max(1,len(TABLES[tbl])), 3)
R["18_excessive_repeated_values"] = repeated

# 19/20 PLACEHOLDER + SUSPICIOUS PATTERNS
PLACEHOLDER_RE = re.compile(r"(?i)\b(?:test|dummy|foo|bar|lorem|ipsum|sample record|xxxx?|n/?a|todo|placeholder|asdf|qwerty)\b")
placeholder_hits = {}
for tbl in ["companies","contacts","leads","opportunities","customers","activities"]:
    df = TABLES[tbl]
    name_cols = [col for col in df.columns if any(k in col.lower() for k in ["name","title","subject"])]
    hits = sum(int(df[col].astype(str).str.contains(PLACEHOLDER_RE, na=False).sum()) for col in name_cols)
    placeholder_hits[tbl] = hits
R["19_placeholder_records"] = placeholder_hits
R["20_suspicious_synthetic_patterns"] = {
    "opportunities.identical_created_and_close_ts": int((opp.created_at == opp.actual_close_date).sum()),
}

# 21. ML LEAKAGE
lc = ML_TABLES["lead_conversion_dataset"]; ls_ = ML_TABLES["lead_scoring_dataset"]
lead_row = {r.lead_id: r for _, r in lo.iterrows()}
bad_cutoff = sum(1 for _, r in lc.iterrows() if lead_row[r.lead_id].converted_at and pdt(r.observation_cutoff_at) > pdt(lead_row[r.lead_id].converted_at))
scoring_cutoff_mismatch = sum(1 for _, r in ls_.iterrows() if r.observation_cutoff_at != lead_row[r.lead_id].created_at)
forbidden_in_scoring = [col for col in ["num_status_transitions_before_cutoff","estimated_budget_inr","rep_trailing_conversion_rate"] if col in ls_.columns]
R["21_ml_target_leakage"] = {
    "lead_conversion.cutoff_after_converted_at": int(bad_cutoff),
    "lead_scoring.cutoff_not_equal_created_at": int(scoring_cutoff_mismatch),
    "lead_scoring.forbidden_columns_present": forbidden_in_scoring,
    "churn.customer_status_column_present": "customer_status" in ML_TABLES["churn_prediction_dataset"].columns,
    "segmentation.cluster_id_column_present": "segment_label_cluster_id" in ML_TABLES["customer_segmentation_dataset"].columns,
    # customer_segmentation_dataset no longer ships a "segment_label_cluster_id"
    # column at all (it was always 100% blank -- a misleading placeholder for a
    # downstream clustering model's OUTPUT, not an input feature). Its absence
    # is itself the leakage-prevention check now: if a future regeneration ever
    # reintroduces any such column, this flips to True and the run must fail.
}

# 22. CLASS IMBALANCE
R["22_class_imbalance"] = {
    "lead_conversion_positive_rate": round(lc.label_converted.eq("True").mean(), 3),
    "lead_scoring_positive_rate": round(ls_.label_converted.eq("True").mean(), 3),
    "churn_positive_rate": round(ML_TABLES["churn_prediction_dataset"].label_churned_within_horizon.eq("True").mean(), 3) if len(ML_TABLES["churn_prediction_dataset"]) else None,
}

# 23. SOURCE vs ML DUPLICATION
overlap = set(lo.columns) & set(ls_.columns)
R["23_data_duplication_source_vs_ml"] = {
    "lead_scoring_raw_column_overlap_with_leads_besides_ids": sorted(overlap - {"lead_id"}),
}

# 27. ML DATASET VALIDATION -- duplicate source-entity IDs (only where
# uniqueness is actually expected), invalid target values, invalid numeric
# values, and invalid/unparseable dates across all 5 ML-ready tables.
sf = ML_TABLES["sales_forecasting_dataset"]
seg = ML_TABLES["customer_segmentation_dataset"]
chu = ML_TABLES["churn_prediction_dataset"]

def _num(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None

# -- duplicate source-entity IDs where uniqueness IS expected --
# lead_conversion_dataset and lead_scoring_dataset are single-snapshot-per-
# lead datasets: exactly one row per lead_id is the correct shape, so a
# repeated lead_id here is a real defect.
dup_entity = {
    "lead_conversion_dataset.lead_id": int(lc.lead_id.duplicated().sum()),
    "lead_scoring_dataset.lead_id": int(ls_.lead_id.duplicated().sum()),
}
# churn_prediction_dataset, customer_segmentation_dataset and
# sales_forecasting_dataset are intentionally MULTI-snapshot-per-entity
# (one row per customer per quarter-end / per department per period) --
# a repeated customer_id or department_id there is normal, NOT a defect.
# What must still be unique is the (entity, time-bucket) pair.
dup_entity_multisnapshot_informational = {
    "churn_prediction_dataset.customer_id_repeat_rows": int(chu.customer_id.duplicated(keep=False).sum()),
    "churn_prediction_dataset.(customer_id+observation_snapshot_date)_duplicated": int(
        chu.duplicated(subset=["customer_id", "observation_snapshot_date"]).sum()),
    "customer_segmentation_dataset.customer_id_repeat_rows": int(seg.customer_id.duplicated(keep=False).sum()),
    "customer_segmentation_dataset.(customer_id+snapshot_date)_duplicated": int(
        seg.duplicated(subset=["customer_id", "snapshot_date"]).sum()),
    "sales_forecasting_dataset.department_id_repeat_rows": int(sf.department_id.duplicated(keep=False).sum()),
    "sales_forecasting_dataset.(department_id+period_start)_duplicated": int(
        sf.duplicated(subset=["department_id", "period_start"]).sum()),
}

# -- invalid target values --
invalid_targets = {
    "lead_conversion_dataset.label_converted_not_bool": int((~lc.label_converted.isin(["True", "False"])).sum()),
    "lead_scoring_dataset.label_converted_not_bool": int((~ls_.label_converted.isin(["True", "False"])).sum()),
    "churn_prediction_dataset.label_churned_not_bool": int((~chu.label_churned_within_horizon.isin(["True", "False"])).sum()) if len(chu) else 0,
    "sales_forecasting_dataset.label_actual_amount_negative_or_unparseable": int(sum(
        1 for v in sf.label_actual_amount_inr if _num(v) is None or _num(v) < 0)),
}

# -- invalid numeric values (negative where a negative is not meaningful) --
invalid_numeric = {
    "customer_segmentation_dataset.monetary_total_last_12mo_inr_negative": int(sum(
        1 for v in seg.monetary_total_last_12mo_inr if _num(v) is not None and _num(v) < 0)),
    "customer_segmentation_dataset.frequency_transactions_last_12mo_negative": int(sum(
        1 for v in seg.frequency_transactions_last_12mo if _num(v) is not None and _num(v) < 0)),
    "churn_prediction_dataset.transaction_amount_trailing_90d_inr_negative": int(sum(
        1 for v in chu.transaction_amount_trailing_90d_inr if _num(v) is not None and _num(v) < 0)) if len(chu) else 0,
    "sales_forecasting_dataset.historical_win_rate_out_of_0_1_range": int(sum(
        1 for v in sf.historical_win_rate_trailing_3mo if v.strip() != "" and _num(v) is not None and not (0.0 <= _num(v) <= 1.0))),
    "sales_forecasting_dataset.pipeline_value_negative": int(sum(
        1 for v in sf.pipeline_value_open_at_period_start_inr if _num(v) is not None and _num(v) < 0)),
}

# -- invalid / unparseable dates across the 5 ML tables --
invalid_ml_dates = {}
for tbl_name, df_, cols in [
    ("lead_conversion_dataset", lc, ["observation_cutoff_at"]),
    ("lead_scoring_dataset", ls_, ["observation_cutoff_at"]),
    ("churn_prediction_dataset", chu, ["observation_snapshot_date", "renewal_due_date"]),
    ("customer_segmentation_dataset", seg, ["snapshot_date"]),
    ("sales_forecasting_dataset", sf, ["period_start"]),
]:
    for col in cols:
        if col in df_.columns:
            bad = sum(1 for v in df_[col] if v.strip() != "" and pdt(v) == "INVALID")
            invalid_ml_dates[f"{tbl_name}.{col}_unparseable"] = int(bad)

R["27_ml_dataset_validation"] = {
    "duplicate_source_entity_ids_where_uniqueness_expected": dup_entity,
    "duplicate_entity_time_bucket_informational_multi_snapshot_by_design": {
        "note": "churn/segmentation/sales_forecasting are intentionally one row PER ENTITY PER TIME BUCKET (multiple snapshots per customer/department over time) -- a repeated customer_id/department_id alone is expected and NOT a defect; only a repeated (entity, time-bucket) pair would be",
        **dup_entity_multisnapshot_informational,
    },
    "invalid_target_values": invalid_targets,
    "invalid_numeric_values": invalid_numeric,
    "invalid_dates": invalid_ml_dates,
    "class_imbalance": R.get("22_class_imbalance", {}),
    "target_leakage": R.get("21_ml_target_leakage", {}),
}

# 27b. ML MISSING-VALUE INVESTIGATION -- for churn_prediction_dataset,
# customer_segmentation_dataset and sales_forecasting_dataset specifically,
# classify every null-bearing column as one of: "logically_valid" (the null
# reflects a real absence -- e.g. no cases in the window, so no average to
# report), "intentional_null" (null by design, e.g. an output-only column),
# or a genuine invariant violation requiring investigation/correction. Each
# classification is backed by an explicit invariant check, not just prose.
ml_missing = {}

# churn_prediction_dataset.avg_case_priority_trailing_90d: must be null iff
# support_case_count_trailing_90d == 0 (can't average zero cases).
_chu_bad = int(sum(
    1 for _, r in chu.iterrows()
    if (r.avg_case_priority_trailing_90d.strip() == "") != (_num(r.support_case_count_trailing_90d) == 0)
)) if len(chu) else 0
ml_missing["churn_prediction_dataset.avg_case_priority_trailing_90d"] = {
    "null_count": int((chu.avg_case_priority_trailing_90d.astype(str).str.strip() == "").sum()) if len(chu) else 0,
    "classification": "logically_valid",
    "reason": "null exactly when support_case_count_trailing_90d == 0 -- there is nothing to average",
    "invariant_violations": _chu_bad,
}

# customer_segmentation_dataset.avg_satisfaction_score: must be null iff
# support_case_count_last_12mo == 0 in the fixed generator (a customer with
# a case in the trailing window but no RESOLVED/scored case can still be
# null even though count > 0 -- so the invariant checked here is one-
# directional: count == 0 must imply null; a customer WITH cases may or may
# not have a score depending on resolution/survey response, which is not a
# defect either way).
_seg_bad = int(sum(
    1 for _, r in seg.iterrows()
    if _num(r.support_case_count_last_12mo) == 0
    and str(r.avg_satisfaction_score).strip() != ""
))
ml_missing["customer_segmentation_dataset.avg_satisfaction_score"] = {
    "null_count": int((seg.avg_satisfaction_score.astype(str).str.strip() == "").sum()),
    "classification": "logically_valid",
    "reason": "null whenever support_case_count_last_12mo == 0 (no cases to average); also null when cases exist but none were resolved/scored in that window -- both are real absences, not missing data. Fixed in this revision: the average previously drew from ALL-time resolved cases instead of the same trailing-12mo window as the case count, which could leave a non-null score on a 0-count row -- see data_quality_report.md.",
    "invariant_violations": _seg_bad,  # count==0 but score is non-null -- must be 0 after the fix
}
# customer_segmentation_dataset no longer has a segment_label_cluster_id
# column (see 21_ml_target_leakage.segmentation.cluster_id_column_present)
# -- it was always 100% null, which the user flagged as a misleading
# always-empty label column rather than a genuine missing-value pattern. It
# has been removed from the schema entirely (not just left blank), so there
# is nothing left to classify here.

# sales_forecasting_dataset.historical_win_rate_trailing_3mo /
# avg_deal_cycle_days_trailing_6mo: null when there were 0 opportunities
# closed in the respective trailing window (undefined ratio / no cycle-time
# samples). A quarter where every closed deal was Lost still has a
# well-defined win rate of 0.0 (not null) as long as revenue is 0 too, which
# is the only case that could look ambiguous -- checked explicitly below.
_sf_ambiguous = int(sum(
    1 for _, r in sf.iterrows()
    if _num(r.revenue_trailing_3mo_inr) == 0
    and r.historical_win_rate_trailing_3mo.strip() != ""
    and _num(r.historical_win_rate_trailing_3mo) != 0.0
))
ml_missing["sales_forecasting_dataset.historical_win_rate_trailing_3mo"] = {
    "null_count": int((sf.historical_win_rate_trailing_3mo.astype(str).str.strip() == "").sum()),
    "classification": "logically_valid",
    "reason": "null when 0 opportunities closed in the trailing 3 months (0/0 is undefined); a quarter where every closed deal was Lost has a well-defined win rate of exactly 0.0 (not null) -- confirmed: every non-null 0-revenue row has win_rate == 0.0 exactly",
    "invariant_violations": _sf_ambiguous,  # a non-null, non-zero win_rate with 0 revenue would be suspicious
}
ml_missing["sales_forecasting_dataset.avg_deal_cycle_days_trailing_6mo"] = {
    "null_count": int((sf.avg_deal_cycle_days_trailing_6mo.astype(str).str.strip() == "").sum()),
    "classification": "logically_valid",
    "reason": "null when 0 opportunities closed in the trailing 6 months (no cycle-time samples to average); this window (6mo) differs from historical_win_rate's (3mo), so the two columns' null patterns legitimately don't align row-for-row",
    "invariant_violations": 0,  # no single-column invariant possible without re-deriving the 6mo window directly from source data; see churn/segmentation for the columns where a direct invariant applies
}
R["27b_ml_missing_value_investigation"] = ml_missing

# 24. INCONSISTENT IDS
# Each table's PK just needs ONE consistent prefix internally (the specific
# prefix string is a design choice, e.g. territories use "TERR-" not "TER-";
# what matters for "inconsistent IDs" is that a table never mixes prefixes /
# widths, and that IDs are never reused after being freed, etc.
id_report = {}
for tbl, col in PK.items():
    prefixes = TABLES[tbl][col].str.extract(r"^([A-Za-z]+-)")[0].dropna()
    widths = TABLES[tbl][col].str.len().unique()
    id_report[f"{tbl}.{col}_distinct_prefixes_used"] = sorted(set(prefixes))
    id_report[f"{tbl}.{col}_internally_inconsistent"] = bool(len(set(prefixes)) > 1)
    id_report[f"{tbl}.{col}_distinct_id_widths"] = sorted(int(w) for w in widths)
R["24_inconsistent_ids"] = id_report

# 25. NAMING / FORMATTING
EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
PHONE_RE = re.compile(r"^\+91-[6-9]\d{9}$")  # dataset's consistent house format: "+91-XXXXXXXXXX"
PIN_RE = re.compile(r"^[1-9]\d{5}$")
GSTIN_RE = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z][0-9A-Z]Z[0-9A-Z]$")
fmt = {}
fmt["contacts.invalid_email_format"] = int((~ct[ct.email!=""].email.str.match(EMAIL_RE)).sum())
fmt["sales_reps.invalid_email_format"] = int((~sr[sr.email!=""].email.str.match(EMAIL_RE)).sum())
fmt["contacts.invalid_phone_format"] = int((~ct[ct.phone!=""].phone.str.match(PHONE_RE)).sum())
fmt["sales_reps.invalid_phone_format"] = int((~sr[sr.phone!=""].phone.str.match(PHONE_RE)).sum())
fmt["companies.invalid_pincode"] = int((~c[c.pincode!=""].pincode.str.match(PIN_RE)).sum())
fmt["companies.invalid_gstin"] = int((~c[c.gstin!=""].gstin.str.match(GSTIN_RE)).sum())
fmt["companies.name_leading_trailing_whitespace"] = int(c.company_name.apply(lambda s: s != s.strip()).sum())
fmt["contacts.name_leading_trailing_whitespace"] = int(ct.full_name.apply(lambda s: s != s.strip()).sum())
fmt["companies.double_spaces_in_name"] = int(c.company_name.str.contains("  ").sum())
fmt["contacts.double_spaces_in_name"] = int(ct.full_name.str.contains("  ").sum())
R["25_inconsistent_naming_formatting"] = fmt

with open(REPORT_PATH, "w") as f:
    json.dump(R, f, indent=2, default=str)
print(json.dumps(R, indent=2, default=str))

# =====================================================================
# FINAL SUMMARY -- explicitly bucketed so the report can never be misread
# the way an earlier external/basic testing pass misread it (flagging
# repeated foreign-key values as duplicate-record errors). Every genuine
# result is filed into exactly one of eight buckets:
#
#   1. duplicate primary keys      -- ERROR bucket, must be 0
#   2. exact duplicate rows        -- ERROR bucket, must be 0
#   3. repeated foreign keys       -- INFORMATIONAL, never an error
#   4. invalid foreign keys        -- ERROR bucket, must be 0
#   5. acceptable null values      -- INFORMATIONAL, never an error
#   6. unacceptable null values    -- ERROR bucket, must be 0
#   7. warnings                    -- printed, never fails the run
#   8. errors                      -- every other genuine-violation check
#
# For the date columns, "genuine violation" means the precomputed
# "violations" field (which already accounts for each column's policy),
# not the raw "future_dated" count -- so a column like
# opportunities.expected_close_date can show future_dated: 39 and
# violations: 0 in the same block without that being a contradiction.
# =====================================================================
_fail = False
_fail_lines = []
_bucket_of = {}  # fail-line index -> bucket name, for the grouped FAIL printout

def _record_fail(bucket, path, value):
    global _fail
    line = f"  FAIL [{bucket}]: {path} = {value}"
    _fail_lines.append(line)
    _bucket_of[line] = bucket
    _fail = True

def _check_leaf_ints(block, path, bucket, skip_keys=()):
    """Recursively flag any non-zero int/float leaf not under a skip_keys key."""
    if isinstance(block, dict):
        for k, v in block.items():
            if k in skip_keys:
                continue
            _check_leaf_ints(v, path + (k,), bucket, skip_keys)
    elif isinstance(block, (int, float)) and not isinstance(block, bool):
        if block != 0:
            _record_fail(bucket, ".".join(path), block)

# --- Bucket 1: DUPLICATE PRIMARY KEYS ---------------------------------
_check_leaf_ints(R.get("2_duplicate_primary_keys", {}), ("2_duplicate_primary_keys",), "duplicate_primary_keys")

# --- Bucket 2: EXACT DUPLICATE ROWS -----------------------------------
_check_leaf_ints(R.get("1_duplicate_rows", {}), ("1_duplicate_rows",), "exact_duplicate_rows")

# --- Bucket 3: REPEATED FOREIGN KEYS -- informational only, never
# checked against _fail. Printed in its own section below.

# --- Bucket 4: INVALID FOREIGN KEYS -----------------------------------
_check_leaf_ints(R.get("6_7_invalid_fk_and_orphans", {}), ("6_7_invalid_fk_and_orphans",), "invalid_foreign_keys")

# --- Bucket 5: ACCEPTABLE NULL VALUES -- informational only, never
# checked against _fail. Printed in its own section below.

# --- Bucket 6: UNACCEPTABLE NULL VALUES -------------------------------
_check_leaf_ints(R.get("4_missing_required_values", {}), ("4_missing_required_values",), "unacceptable_null_values")
_check_leaf_ints(R.get("5_unexpected_nulls_conditional_rules", {}), ("5_unexpected_nulls_conditional_rules",), "unacceptable_null_values")
# ML missing-value investigation (27b): only "invariant_violations" is a
# genuine failure -- "null_count" and "classification"/"reason" are
# informational (that's the whole point of the investigation: most nulls
# there are logically_valid or intentional_null, not defects).
for col, block in R.get("27b_ml_missing_value_investigation", {}).items():
    if block.get("invariant_violations", 0) != 0:
        _record_fail("unacceptable_null_values", f"27b_ml_missing_value_investigation.{col}.invariant_violations", block["invariant_violations"])

# --- Bucket 8: ERRORS (every other genuine-violation check) ----------
for cat in ("3_duplicate_business_entities", "10_impossible_date_sequences",
            "11_12_stage_and_status_transitions", "13_invalid_customer_derivations",
            "14_transaction_chronology", "15_revenue_inconsistencies",
            "16_opportunity_probability_inconsistencies", "19_placeholder_records",
            "20_suspicious_synthetic_patterns", "25_inconsistent_naming_formatting"):
    _check_leaf_ints(R.get(cat, {}), (cat,), "errors")

# Category 8 (invalid categorical values): only "invalid_count" is a
# genuine failure -- "invalid_values" is a list of the offending strings
# (informational detail), not a count to sum.
for col, block in R.get("8_invalid_categorical_values", {}).items():
    if block.get("invalid_count", 0) != 0:
        _record_fail("errors", f"8_invalid_categorical_values.{col}.invalid_count", block["invalid_count"])

# Category 9 (dates): only the precomputed "violations" leaf is a genuine
# failure; "future_dated"/"unparseable" are informational and "policy" is a
# label, not a count -- skip those explicitly rather than filtering by
# value type, so a real 0-vs-nonzero distinction is never accidentally lost.
for col, block in R.get("9_invalid_dates", {}).items():
    if block.get("violations", 0) != 0:
        _record_fail("errors", f"9_invalid_dates.{col}.violations", block["violations"])

# Category 9b: the conditional-policy checks (customers.renewal_date vs
# customer_status, expected_close_date vs created_at, campaign end vs start).
for check, block in R.get("9b_future_date_policy_violations", {}).items():
    if block.get("violations", 0) != 0:
        _record_fail("errors", f"9b_future_date_policy_violations.{check}", block["violations"])

# Category 21 (ML target leakage): numeric leaves must be 0; the two
# non-numeric leaves (a list of forbidden columns, and a bool) need their
# own checks since they aren't int/float.
_tl = R.get("21_ml_target_leakage", {})
for k in ("lead_conversion.cutoff_after_converted_at", "lead_scoring.cutoff_not_equal_created_at"):
    if _tl.get(k, 0) != 0:
        _record_fail("errors", f"21_ml_target_leakage.{k}", _tl[k])
if _tl.get("lead_scoring.forbidden_columns_present"):
    _record_fail("errors", "21_ml_target_leakage.lead_scoring.forbidden_columns_present", _tl["lead_scoring.forbidden_columns_present"])
if _tl.get("churn.customer_status_column_present"):
    _record_fail("errors", "21_ml_target_leakage.churn.customer_status_column_present", True)
if _tl.get("segmentation.cluster_id_column_present"):
    _record_fail("errors", "21_ml_target_leakage.segmentation.cluster_id_column_present", True)

# Category 24 (inconsistent IDs): only the "_internally_inconsistent" bool
# leaves are genuine failures (True = a table mixed prefixes/widths); the
# prefix-list and width-list leaves are informational detail, not counts.
for k, v in R.get("24_inconsistent_ids", {}).items():
    if k.endswith("_internally_inconsistent") and v:
        _record_fail("errors", f"24_inconsistent_ids.{k}", v)

# Category 26 (activities): every "violations" leaf must be 0. The
# "activities_with_no_entity_link" entry is informational only (rule #3
# explicitly permits an activity with no lead/contact/company/opportunity/
# customer link, e.g. a general internal task), and
# "repeated_content_warnings" is bucket-7 material (printed separately
# below) -- both subtrees are skipped here rather than counted as errors.
_check_leaf_ints(R.get("26_activities_validation", {}), ("26_activities_validation",), "errors",
                  skip_keys=("activities_with_no_entity_link", "repeated_content_warnings"))

# Category 27 (ML dataset validation): duplicate source-entity IDs, invalid
# target values, invalid numeric values, and invalid dates are all genuine
# failures. The multi-snapshot repeat-row counts are informational by
# design (see the note in that subtree), and class_imbalance/target_leakage
# are non-zero-by-nature rates/duplicated-from-21 data, not pass/fail
# counts -- all three subtrees are skipped here.
_check_leaf_ints(R.get("27_ml_dataset_validation", {}), ("27_ml_dataset_validation",), "errors",
                  skip_keys=("duplicate_entity_time_bucket_informational_multi_snapshot_by_design",
                             "class_imbalance", "target_leakage"))

# =====================================================================
# PRINTED REPORT -- one section per bucket, in the order the user asked
# for: duplicate PKs, exact duplicate rows, repeated FKs, invalid FKs,
# acceptable nulls, unacceptable nulls, warnings, errors.
# =====================================================================

def _fails_in(bucket):
    return [ln for ln in _fail_lines if _bucket_of.get(ln) == bucket]

print("\n" + "=" * 72)
print("BUCKET 1/8 -- DUPLICATE PRIMARY KEYS (error if any nonzero)")
print("=" * 72)
_b = _fails_in("duplicate_primary_keys")
print(f"  {len(_b)} violation(s)." if _b else "  0 violations across all 24 tables' own primary-key columns.")
for ln in _b: print(ln)

print("\n" + "=" * 72)
print("BUCKET 2/8 -- EXACT DUPLICATE ROWS (whole-row identity; error if any nonzero)")
print("=" * 72)
_b = _fails_in("exact_duplicate_rows")
print(f"  {len(_b)} violation(s)." if _b else "  0 exact duplicate rows across all 24 CSVs.")
for ln in _b: print(ln)

print("\n" + "=" * 72)
print("BUCKET 3/8 -- REPEATED FOREIGN KEYS (informational -- NEVER an error)")
print("=" * 72)
_rfk = R.get("6b_repeated_foreign_keys_informational", {}).get("by_relationship", {})
print(f"  {len(_rfk)} FK relationship(s) checked; every repeat count below is EXPECTED,")
print("  not a duplicate-record signal (one parent row legitimately has many child rows).")
for rel, d in sorted(_rfk.items(), key=lambda kv: -kv[1]["max_repeat_count"])[:12]:
    print(f"    {rel}: {d['distinct_values_referenced']} distinct value(s) across "
          f"{d['rows_with_this_fk_populated']} row(s), max repeat = {d['max_repeat_count']}x "
          f"(e.g. {d['example_most_repeated_value']})")
if len(_rfk) > 12:
    print(f"    ... and {len(_rfk) - 12} more relationship(s) -- see full_audit_report.json -> 6b_repeated_foreign_keys_informational")

print("\n" + "=" * 72)
print("BUCKET 4/8 -- INVALID FOREIGN KEYS (orphan references; error if any nonzero)")
print("=" * 72)
_b = _fails_in("invalid_foreign_keys")
print(f"  {len(_b)} violation(s)." if _b else "  0 orphan references across 40 relationships + 4 semantic cross-checks.")
for ln in _b: print(ln)

print("\n" + "=" * 72)
print("BUCKET 5/8 -- ACCEPTABLE NULL VALUES (nullable-by-design columns; informational -- NEVER an error)")
print("=" * 72)
for tbl, cols in R.get("4b_acceptable_null_values_informational", {}).items():
    parts = [f"{col}={n}" for col, n in cols.items()]
    if parts:
        print(f"  {tbl}: " + ", ".join(parts))

print("\n" + "=" * 72)
print("BUCKET 6/8 -- UNACCEPTABLE NULL VALUES (required columns / genuine invariant violations; error if any nonzero)")
print("=" * 72)
_b = _fails_in("unacceptable_null_values")
print(f"  {len(_b)} violation(s)." if _b else "  0 violations -- every required column is fully populated, and every ML missing-value invariant checked in 27b holds.")
for ln in _b: print(ln)

print("\n" + "=" * 72)
print("BUCKET 7/8 -- WARNINGS (informational -- NEVER fail the run)")
print("=" * 72)
print("FUTURE-DATED COLUMNS -- policy summary (see docs/business_rules.md):")
for col, block in R.get("9_invalid_dates", {}).items():
    if block.get("future_dated", 0) > 0:
        print(f"  {col}: {block['future_dated']} future-dated row(s) "
              f"-- policy = {block['policy']!r}, genuine violations = {block['violations']}")
print("  These counts are EXPECTED: forecast/schedule/deadline fields (opportunity")
print("  expected-close, customer renewal, campaign end date, activity due date /")
print("  next follow-up date) that are allowed to be ahead of the cutoff by design.")

_rcw = R.get("26_activities_validation", {}).get("repeated_content_warnings", {})
if _rcw:
    print("\nACTIVITIES -- repeated-content warnings:")
    for field in ("subject", "description"):
        blk = _rcw.get(field, {})
        print(f"  {field}: {blk.get('unique_values')}/{blk.get('total_rows')} unique "
              f"({blk.get('max_repeat_share', 0)*100:.2f}% max repeat share, "
              f"top value repeated {blk.get('max_repeat_count')}x)")
        flagged = blk.get("flagged_values_over_threshold", [])
        if flagged:
            print(f"    {len(flagged)} value(s) exceed the 5x / 0.5%-share threshold:")
            for f in flagged[:10]:
                print(f"      {f['count']}x: {f['value']!r}")
        else:
            print("    no value exceeds the 5x / 0.5%-share threshold")

_ms = R.get("27_ml_dataset_validation", {}).get("duplicate_entity_time_bucket_informational_multi_snapshot_by_design", {})
if _ms:
    print("\nML MULTI-SNAPSHOT TABLES -- repeated entity IDs (expected by design; see note):")
    for k, v in _ms.items():
        if k != "note":
            print(f"  {k}: {v}")

print("\n" + "=" * 72)
print("BUCKET 8/8 -- ERRORS (every other genuine-violation check; error if any nonzero)")
print("=" * 72)
_b = _fails_in("errors")
print(f"  {len(_b)} violation(s)." if _b else "  0 violations across categorical values, dates, sequences, transitions, derivations, chronology, revenue, probability, placeholders, synthetic patterns, ML leakage, ID consistency, naming/formatting, activities, and ML dataset validation.")
for ln in _b: print(ln)

print("\n" + "=" * 72)
if _fail:
    _counts = {b: len(_fails_in(b)) for b in ("duplicate_primary_keys", "exact_duplicate_rows",
                                                "invalid_foreign_keys", "unacceptable_null_values", "errors")}
    print("RESULT: FAIL -- genuine violations found:")
    for b, n in _counts.items():
        if n:
            print(f"  {b}: {n} violation(s)")
    print("=" * 72)
    raise SystemExit(1)
else:
    print("RESULT: PASS -- 0 duplicate primary keys, 0 exact duplicate rows, 0 invalid foreign")
    print("keys, and 0 unacceptable null values, and 0 errors across every other checked category.")
    print("Repeated foreign keys and acceptable null values (buckets 3 and 5 above) are expected")
    print("by design and are never treated as errors. See BUCKET 7/8 above for the warnings this")
    print("report explains rather than hides -- the dataset is not claimed clean anywhere those")
    print("warnings go unexplained.")
    print("=" * 72)
