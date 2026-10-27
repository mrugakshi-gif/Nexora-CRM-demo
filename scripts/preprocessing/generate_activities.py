"""
Phase 5: CRM activities generator.

Adds the `activities.csv` table (calls, emails, meetings, demos,
follow-ups, tasks, site visits, proposal/negotiation discussions, and
support follow-ups) to the already-generated Indian B2B CRM dataset.

MUST be run AFTER the full Phase 1-3 pipeline (generate_master_tables.py,
generate_contacts_leads.py, generate_opps_customers.py) so it can draw only
existing, valid IDs. It does not modify any existing table -- it only reads
them and writes output/activities.csv. Uses the same fixed seed so the run
is fully reproducible, and consumes its own dedicated random.Random()
instance seeded from the project seed rather than the shared `random`
module, so re-running this script alone never perturbs any other
generator's RNG stream/output if run in a different order.

v2 (this revision): a user review of v1 found no exact duplicate rows and
no genuine business-event duplicates (same activity_type + company_id +
contact_id + opportunity_id + activity_date + subject), but flagged that
subjects/descriptions/outcomes were repeated far more than a real CRM log
would produce -- because v1 built them from a small, mostly-generic
template pool (20 topics; Email/Task subjects didn't even include the
company name). This version:
  - widens every text vocabulary substantially (topics, outcome openings/
    closings, next-step phrases, description phrasings) so the combinatorial
    space is orders of magnitude larger than the row count,
  - makes every subject context-specific (company name always included;
    contact name included where one is set), so two unrelated activities
    essentially never produce the same subject text,
  - builds `outcome` compositionally (opening + specific result + a
    concrete next-step/detail clause) instead of picking from a short fixed
    list, so completed activities very rarely share exact wording,
  - runs an explicit post-generation business-event dedup pass (grouping by
    activity_type/company_id/contact_id/opportunity_id/activity_date/
    subject) that PERTURBS -- not deletes -- any true duplicate it finds
    (nudges the activity_date and re-rolls the subject/description/outcome
     for the duplicate row) so real business events are never silently
    dropped and the total row count is preserved.
"""
import random as random_module
import pandas as pd
from datetime import datetime, timedelta, date

SEED = 20260915
TODAY = date(2026, 9, 15)
rng = random_module.Random(SEED + 5002)  # bumped: dedicated stream for v2

OUT_DIR = "output"

# ---------------------------------------------------------------------------
# Load existing, already-validated tables (read-only)
# ---------------------------------------------------------------------------
leads = pd.read_csv(f"{OUT_DIR}/leads.csv")
contacts = pd.read_csv(f"{OUT_DIR}/contacts.csv")
companies = pd.read_csv(f"{OUT_DIR}/companies.csv")
opportunities = pd.read_csv(f"{OUT_DIR}/opportunities.csv")
customers = pd.read_csv(f"{OUT_DIR}/customers.csv")
sales_reps = pd.read_csv(f"{OUT_DIR}/sales_reps.csv")
support_cases = pd.read_csv(f"{OUT_DIR}/customer_support_cases.csv")

contacts_by_company = contacts.groupby("company_id")["contact_id"].apply(list).to_dict()
contact_name_by_id = dict(zip(contacts.contact_id, contacts.full_name))
active_reps = sales_reps[sales_reps["is_active"] == True]["rep_id"].tolist()
all_reps = sales_reps["rep_id"].tolist()

leads_idx = leads.to_dict("records")
opps_idx = opportunities.to_dict("records")
custs_idx = customers.to_dict("records")
cases_idx = support_cases.to_dict("records")
companies_by_id = companies.set_index("company_id").to_dict("index")

# ---------------------------------------------------------------------------
# Vocabulary -- widened substantially vs. v1 to avoid template collapse
# ---------------------------------------------------------------------------
STATUS_WEIGHTS = [
    ("Completed", 55), ("Planned", 15), ("Pending", 10),
    ("In Progress", 8), ("Rescheduled", 7), ("Cancelled", 5),
]
PRIORITY_BASE = [("Low", 20), ("Medium", 45), ("High", 27), ("Urgent", 8)]
PRIORITY_HIGH_STAKES = [("Low", 5), ("Medium", 30), ("High", 45), ("Urgent", 20)]

LEAD_TYPES = [("Call", 30), ("Email", 25), ("Meeting", 15), ("Follow-up", 22), ("Task", 8)]
OPP_TYPES = [("Meeting", 20), ("Demo", 16), ("Proposal Discussion", 14),
             ("Negotiation", 10), ("Site Visit", 8), ("Call", 20), ("Follow-up", 12)]
CUST_TYPES = [("Support Follow-up", 28), ("Call", 22), ("Email", 18),
              ("Follow-up", 18), ("Task", 14)]
GENERAL_TYPES = [("Task", 55), ("Call", 25), ("Email", 20)]

HIGH_STAKES_TYPES = {"Negotiation", "Proposal Discussion", "Demo", "Site Visit"}

TOPICS = [
    "pricing and licensing terms", "product requirements walkthrough",
    "implementation timeline", "renewal discussion", "onboarding plan",
    "budget approval status", "technical integration questions",
    "contract terms review", "feature requirements", "decision-maker introduction",
    "competitor comparison", "ROI justification", "SLA expectations",
    "custom pricing request", "rollout plan for regional offices",
    "GST invoicing requirements", "data migration plan", "user training schedule",
    "escalation on open support ticket", "quarterly business review",
    "API integration scope", "single sign-on requirements", "data residency questions",
    "multi-year discount structure", "seat-count expansion", "module add-on request",
    "security/compliance questionnaire", "procurement sign-off process",
    "legal redlines on the MSA", "invoice discrepancy", "payment terms negotiation",
    "vendor onboarding checklist", "third-party integration compatibility",
    "mobile app rollout", "regional language support", "uptime/SLA credits",
    "user adoption metrics review", "feature request prioritization",
    "account handover to new stakeholder", "budget freeze update",
    "internal champion alignment", "procurement RFP response",
    "pilot program scope", "post-implementation review", "support ticket backlog",
    "dashboard/reporting requirements", "audit trail requirements",
    "backup and disaster recovery plan", "franchise/branch rollout sequencing",
    "year-end contract renewal terms", "cross-sell opportunity discussion",
    "reference customer request",
]

# Concrete "next step / detail" clauses used to compose outcomes -- shared
# across activity types so the combinatorial space (opening x topic-detail x
# closing) stays far larger than the dataset's row count.
NEXT_STEP_CLAUSES = [
    "will send a revised proposal by end of week",
    "scheduled a technical deep-dive with the engineering team",
    "escalated pricing approval to the regional sales head",
    "confirmed the rollout timeline with the client's IT team",
    "looped in the finance team for budget sign-off",
    "agreed to a follow-up call next Tuesday",
    "requested a reference call with an existing customer",
    "will circulate the security questionnaire responses",
    "client asked for a customized ROI calculation",
    "set up a joint working session with procurement",
    "shared the updated contract redlines for legal review",
    "will loop in the CFO's office for final approval",
    "client requested a 2-week extension to evaluate internally",
    "agreed on a phased rollout starting with the Mumbai office",
    "will schedule the kickoff call once the PO is issued",
    "raised a request for additional training sessions",
    "client confirmed budget is approved for next quarter",
    "flagged a blocker with their existing ERP integration",
    "will forward the case study requested by the buying committee",
    "agreed to revisit pricing after the pilot concludes",
    "client's technical team will run a sandbox trial first",
    "requested an updated SOW reflecting the reduced scope",
    "will coordinate a joint QBR with the account team",
    "client asked for clarification on data-residency terms",
    "confirmed the go-live date with the operations team",
]

FOLLOWUP_REASONS = [
    "to confirm the proposal was received and reviewed",
    "to check on internal budget approval status",
    "to close the loop on outstanding technical questions",
    "to verify the pilot feedback before renewal",
    "to review adoption metrics with the account owner",
    "to finalize the contract redlines",
    "to confirm the go-live date",
    "to check in after the recent support escalation",
    "to discuss the upcoming renewal",
    "to share the updated pricing sheet",
]


def weighted_choice(pairs):
    total = sum(w for _, w in pairs)
    r = rng.uniform(0, total)
    upto = 0
    for val, w in pairs:
        upto += w
        if r <= upto:
            return val
    return pairs[-1][0]


def parse_dt(s):
    if pd.isna(s) or s == "":
        return None
    return pd.to_datetime(s).to_pydatetime()


def clamp_to_today(dt):
    today_end = datetime.combine(TODAY, datetime.max.time())
    return min(dt, today_end)


SUBJECT_PREFIX = {
    "Call": "Call", "Email": "Email", "Meeting": "Meeting", "Demo": "Product Demo",
    "Follow-up": "Follow-up", "Task": "Task", "Site Visit": "Site Visit",
    "Proposal Discussion": "Proposal Discussion", "Negotiation": "Negotiation",
    "Support Follow-up": "Support Follow-up",
}


def make_subject(activity_type, company_name, contact_name, topic, use_contact):
    """Every subject is context-specific: company name is always included,
    and (for a randomized ~half of contact-bearing rows) the contact's name
    is included too, so subjects for the same topic essentially never
    collide across unrelated companies -- unlike v1, where Email/Task
    subjects carried no company/contact context at all.
    """
    prefix = SUBJECT_PREFIX[activity_type]
    if activity_type in ("Demo", "Site Visit", "Proposal Discussion", "Negotiation"):
        # these already read naturally as "<Prefix> - <Company>[ - <topic>]"
        base = f"{prefix} - {company_name}"
        return f"{base} - {topic}" if activity_type == "Negotiation" else base
    if use_contact and contact_name:
        return f"{prefix} - {company_name} ({contact_name}) - {topic}"
    return f"{prefix} - {company_name} - {topic}"


DESC_TEMPLATES = {
    "Call": [
        "{rep} called {who} at {company} to discuss {topic}.",
        "{rep} placed a call to {who} ({company}) regarding {topic}.",
        "Outbound call from {rep} to {company} -- {who} -- covering {topic}.",
    ],
    "Email": [
        "{rep} sent an email to {who} at {company} regarding {topic}.",
        "{rep} emailed {company} ({who}) with details on {topic}.",
        "Email correspondence from {rep} to {who} at {company} on {topic}.",
    ],
    "Meeting": [
        "{rep} held a meeting with {company} stakeholders ({who}) to cover {topic}.",
        "{rep} met with {who} at {company} to walk through {topic}.",
        "Meeting between {rep} and {company}'s team ({who}) on {topic}.",
    ],
    "Demo": [
        "{rep} conducted a product demo for {company}'s evaluation team ({who}).",
        "{rep} walked {company} ({who}) through a live product demo.",
        "Product demo delivered by {rep} to {company}'s stakeholders, led by {who}.",
    ],
    "Follow-up": [
        "{rep} followed up with {who} at {company} on {topic}.",
        "{rep} sent a follow-up to {company} ({who}) {reason}.",
        "Follow-up touchpoint from {rep} with {who} at {company} regarding {topic}.",
    ],
    "Task": [
        "Internal task for {rep} related to {company}: {topic}.",
        "{rep} logged an internal task covering {topic} for the {company} account.",
        "Task assigned to {rep} on the {company} account: {topic}.",
    ],
    "Site Visit": [
        "{rep} visited {company}'s facility to assess on-ground requirements.",
        "On-site visit by {rep} at {company}, covering {topic}.",
        "{rep} conducted a site assessment at {company}'s office ({who}).",
    ],
    "Proposal Discussion": [
        "{rep} walked {company} through the submitted proposal, focusing on {topic}.",
        "{rep} discussed proposal specifics with {who} at {company}, on {topic}.",
        "Proposal review session between {rep} and {company} ({who}) covering {topic}.",
    ],
    "Negotiation": [
        "{rep} negotiated commercial terms with {company} on {topic}.",
        "{rep} and {who} at {company} discussed contract terms, focused on {topic}.",
        "Negotiation session led by {rep} with {company}'s procurement team on {topic}.",
    ],
    "Support Follow-up": [
        "{rep} followed up with {who} at {company} on an open/recent support case.",
        "{rep} checked in with {company} ({who}) regarding their recent support case.",
        "Post-resolution follow-up by {rep} with {company}'s {who} on case status.",
    ],
}


def make_description(activity_type, company_name, contact_name, topic, rep_name):
    who = contact_name if contact_name else "the primary contact"
    reason = rng.choice(FOLLOWUP_REASONS)
    template = rng.choice(DESC_TEMPLATES[activity_type])
    return template.format(rep=rep_name, who=who, company=company_name, topic=topic, reason=reason)


CALL_OPENINGS = ["Connected", "Reached", "Spoke with the contact", "Got through"]
CALL_MISS_OPENINGS = ["No answer, left voicemail", "Call went to voicemail", "Unable to connect, will retry"]
EMAIL_OPENINGS = ["Email sent with requested collateral", "Follow-up email delivered",
                  "Detailed response sent by email", "Email sent summarizing the discussion"]
MEETING_OPENINGS = ["Productive meeting held", "Meeting completed", "Stakeholder meeting held",
                     "Discovery meeting completed"]
DEMO_OPENINGS = ["Demo well received", "Demo completed", "Technical demo delivered successfully"]
PROPOSAL_OPENINGS = ["Proposal reviewed with the client", "Walked the client through the proposal",
                      "Proposal discussion completed"]
NEGOTIATION_OPENINGS = ["Commercial terms discussed", "Negotiation session completed",
                         "Contract terms reviewed jointly"]
SITE_VISIT_OPENINGS = ["Site visit completed", "On-site assessment completed",
                        "Facility visit wrapped up"]
FOLLOWUP_OPENINGS = ["Follow-up completed", "Checked in as planned", "Touched base as scheduled"]
TASK_OPENINGS = ["Task completed as planned", "Task closed out", "Internal task wrapped up"]
SUPPORT_OPENINGS = ["Checked in on the support case", "Followed up on case status",
                     "Confirmed with the customer on case resolution"]

OPENING_MAP = {
    "Call": CALL_OPENINGS, "Email": EMAIL_OPENINGS, "Meeting": MEETING_OPENINGS,
    "Demo": DEMO_OPENINGS, "Proposal Discussion": PROPOSAL_OPENINGS,
    "Negotiation": NEGOTIATION_OPENINGS, "Site Visit": SITE_VISIT_OPENINGS,
    "Follow-up": FOLLOWUP_OPENINGS, "Task": TASK_OPENINGS,
    "Support Follow-up": SUPPORT_OPENINGS,
}


def make_outcome(activity_type, status, topic):
    """Compose the outcome from an opening + a topic-specific result clause +
    a concrete next-step clause. openings(~3-4) x topics(50) x next-steps(25)
    gives >3,000 distinct combinations per type -- far more than any single
    type's row count -- so exact-text repeats among Completed outcomes are
    rare, unlike v1's fixed 4-7-item lists.
    """
    if status == "Completed":
        if activity_type == "Call" and rng.random() < 0.12:
            return f"{rng.choice(CALL_MISS_OPENINGS)}; will retry regarding {topic}."
        opening = rng.choice(OPENING_MAP[activity_type])
        next_step = rng.choice(NEXT_STEP_CLAUSES)
        return f"{opening} -- discussed {topic}; {next_step}."
    if status == "Cancelled" and rng.random() < 0.5:
        reason = rng.choice([
            "client requested reschedule", "internal priority change",
            "no longer relevant given account status", "duplicate activity",
            "client unavailable, will re-book", "superseded by a later touchpoint",
        ])
        return f"Cancelled -- {reason}."
    return ""


def build_row(act_counter, kind, ctx):
    activity_id = f"ACT-{act_counter:07d}"

    lead_id = contact_id = company_id = opportunity_id = customer_id = ""
    sales_rep_id = rng.choice(active_reps)
    anchor_dt = None

    if kind == "lead":
        lead_id = ctx["lead_id"]
        company_id = ctx["company_id"]
        contact_id = ctx["contact_id"]
        assigned = ctx["assigned_rep_id"]
        sales_rep_id = assigned if isinstance(assigned, str) and assigned else rng.choice(active_reps)
        anchor_dt = parse_dt(ctx["created_at"])
        activity_type = weighted_choice(LEAD_TYPES)

    elif kind == "opp":
        opportunity_id = ctx["opportunity_id"]
        company_id = ctx["company_id"]
        contact_id = ctx["primary_contact_id"]
        sales_rep_id = ctx["owner_rep_id"]
        if isinstance(ctx.get("source_lead_id"), str) and ctx["source_lead_id"]:
            if rng.random() < 0.5:
                lead_id = ctx["source_lead_id"]
        anchor_dt = parse_dt(ctx["created_at"])
        activity_type = weighted_choice(OPP_TYPES)

    elif kind == "cust":
        customer_id = ctx["customer_id"]
        company_id = ctx["company_id"]
        sales_rep_id = ctx["csm_rep_id"]
        if rng.random() < 0.7:
            opportunity_id = ctx["originating_opportunity_id"]
        cands = contacts_by_company.get(company_id, [])
        if cands and rng.random() < 0.85:
            contact_id = rng.choice(cands)
        since_dt = parse_dt(ctx["customer_since"])
        anchor_dt = since_dt if since_dt else datetime.combine(TODAY, datetime.min.time())
        activity_type = weighted_choice(CUST_TYPES)

    else:  # general
        company_id = rng.choice(companies["company_id"].tolist()) if rng.random() < 0.5 else ""
        anchor_dt = datetime.combine(TODAY - timedelta(days=rng.randint(0, 400)), datetime.min.time())
        activity_type = weighted_choice(GENERAL_TYPES)

    if anchor_dt is None:
        anchor_dt = datetime.combine(TODAY - timedelta(days=180), datetime.min.time())

    span_days = max((TODAY - anchor_dt.date()).days, 0)
    offset_days = rng.randint(0, span_days) if span_days > 0 else 0
    activity_dt = anchor_dt + timedelta(
        days=offset_days, hours=rng.randint(0, 9), minutes=rng.choice([0, 15, 30, 45])
    )
    activity_dt = clamp_to_today(activity_dt)

    status = weighted_choice(STATUS_WEIGHTS)
    priority_table = PRIORITY_HIGH_STAKES if activity_type in HIGH_STAKES_TYPES else PRIORITY_BASE
    priority = weighted_choice(priority_table)

    if status == "Completed":
        due_dt = activity_dt + timedelta(hours=rng.randint(0, 36))
    elif status == "Cancelled":
        due_dt = activity_dt + timedelta(days=rng.randint(0, 5))
    elif status == "In Progress":
        due_dt = activity_dt + timedelta(days=rng.randint(0, 7))
    else:  # Planned, Pending, Rescheduled
        due_dt = activity_dt + timedelta(days=rng.randint(1, 45))
    due_date = due_dt.date()

    topic = rng.choice(TOPICS)
    outcome = make_outcome(activity_type, status, topic)

    next_follow_up_date = ""
    wants_followup = status in ("Completed", "Pending", "Rescheduled", "In Progress")
    if wants_followup and rng.random() < 0.42:
        nf = activity_dt + timedelta(days=rng.randint(1, 30))
        next_follow_up_date = nf.date().isoformat()

    created_dt = activity_dt + timedelta(hours=rng.randint(0, 6), minutes=rng.randint(0, 59))
    created_dt = clamp_to_today(created_dt)
    if created_dt < activity_dt:
        created_dt = activity_dt
    updated_dt = created_dt + timedelta(days=rng.randint(0, 3), hours=rng.randint(0, 23))
    updated_dt = clamp_to_today(updated_dt)
    if updated_dt < created_dt:
        updated_dt = created_dt

    company_name = companies_by_id.get(company_id, {}).get("company_name", "the client") if company_id else "the prospect"
    contact_name = contact_name_by_id.get(contact_id, "") if contact_id else ""
    rep_name_row = sales_reps.loc[sales_reps["rep_id"] == sales_rep_id, "full_name"]
    rep_name = rep_name_row.iloc[0] if len(rep_name_row) else "The rep"
    use_contact = bool(contact_name) and rng.random() < 0.55

    subject = make_subject(activity_type, company_name, contact_name, topic, use_contact)
    description = make_description(activity_type, company_name, contact_name, topic, rep_name)

    return {
        "activity_id": activity_id,
        "activity_type": activity_type,
        "subject": subject,
        "description": description,
        "activity_date": activity_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "due_date": due_date.isoformat(),
        "status": status,
        "priority": priority,
        "lead_id": lead_id,
        "contact_id": contact_id,
        "company_id": company_id,
        "opportunity_id": opportunity_id,
        "customer_id": customer_id,
        "sales_rep_id": sales_rep_id,
        "outcome": outcome,
        "next_follow_up_date": next_follow_up_date,
        "created_at": created_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": updated_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "_kind": kind, "_ctx": ctx,  # kept only for the dedup-repair pass below; dropped before writing
    }


# ---------------------------------------------------------------------------
# Build the context pool (unchanged distribution strategy from v1)
# ---------------------------------------------------------------------------
n_target = 3200
context_pool = []
context_pool += [("lead", r) for r in leads_idx for _ in range(rng.randint(1, 2))]
context_pool += [("opp", r) for r in opps_idx for _ in range(rng.randint(1, 3))]
context_pool += [("cust", r) for r in custs_idx for _ in range(rng.randint(2, 4))]
context_pool += [("general", None) for _ in range(int(n_target * 0.06))]
rng.shuffle(context_pool)
context_pool = context_pool[:n_target]

rows = [build_row(i + 1, kind, ctx) for i, (kind, ctx) in enumerate(context_pool)]
original_count = len(rows)

# ---------------------------------------------------------------------------
# Business-event dedup pass. A "business-event duplicate" is a row that
# shares (activity_type, company_id, contact_id, opportunity_id,
# activity_date, subject) with an earlier row -- i.e. it looks like the
# same call/email/meeting logged twice. This does NOT flag rows merely for
# sharing an activity_type or a subject in isolation (that's expected and
# realistic -- see requirement #4/#12). Because the widened vocabulary above
# already makes true collisions rare, any duplicate found here is repaired
# in place (re-rolled subject/description/outcome and a nudged activity_date
# so it becomes a distinct business event) rather than deleted, so the
# dataset never loses a valid record to satisfy this check and the target
# row count is preserved exactly.
# ---------------------------------------------------------------------------
DEDUP_KEY = ("activity_type", "company_id", "contact_id", "opportunity_id", "activity_date", "subject")
removed_as_duplicate = 0
seen = set()
for i, row in enumerate(rows):
    key = tuple(row[k] for k in DEDUP_KEY)
    attempts = 0
    while key in seen and attempts < 10:
        removed_as_duplicate += 1
        kind, ctx = row["_kind"], row["_ctx"]
        # re-roll date/topic/subject/description/outcome for this row only,
        # keeping its entity linkage (company/contact/opportunity) intact --
        # a genuinely repaired, still-valid business event, not a deletion.
        repaired = build_row(i + 1, kind, ctx)
        rows[i] = repaired
        row = repaired
        key = tuple(row[k] for k in DEDUP_KEY)
        attempts += 1
    seen.add(key)

for row in rows:
    del row["_kind"]
    del row["_ctx"]

df = pd.DataFrame(rows)
COLS = ["activity_id", "activity_type", "subject", "description", "activity_date",
        "due_date", "status", "priority", "lead_id", "contact_id", "company_id",
        "opportunity_id", "customer_id", "sales_rep_id", "outcome",
        "next_follow_up_date", "created_at", "updated_at"]
df = df[COLS]
df.to_csv(f"{OUT_DIR}/activities.csv", index=False)

final_count = len(df)
print(f"activities: original={original_count}, business-event duplicates repaired={removed_as_duplicate}, "
      f"final={final_count} rows written to {OUT_DIR}/activities.csv")
print(df["activity_type"].value_counts())
print(df["status"].value_counts())
print("unique subjects:", df["subject"].nunique(), "/", len(df))
print("unique descriptions:", df["description"].nunique(), "/", len(df))
completed = df[df["status"] == "Completed"]
print("unique outcomes among Completed:", completed["outcome"].nunique(), "/", len(completed))
