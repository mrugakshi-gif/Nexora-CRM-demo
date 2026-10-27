import sqlite3

def run_audit():
    conn = sqlite3.connect('backend/crm.db')
    c = conn.cursor()

    # Total activities
    c.execute("SELECT COUNT(*) FROM activities;")
    total = c.fetchone()[0]

    # Orphan checks
    queries = {
        "Orphan Companies": "SELECT COUNT(*) FROM activities WHERE company_id IS NOT NULL AND company_id NOT IN (SELECT company_id FROM companies);",
        "Orphan Contacts": "SELECT COUNT(*) FROM activities WHERE contact_id IS NOT NULL AND contact_id NOT IN (SELECT contact_id FROM contacts);",
        "Orphan Leads": "SELECT COUNT(*) FROM activities WHERE lead_id IS NOT NULL AND lead_id NOT IN (SELECT lead_id FROM leads);",
        "Orphan Opportunities": "SELECT COUNT(*) FROM activities WHERE opportunity_id IS NOT NULL AND opportunity_id NOT IN (SELECT opportunity_id FROM opportunities);",
        "Orphan Customers": "SELECT COUNT(*) FROM activities WHERE customer_id IS NOT NULL AND customer_id NOT IN (SELECT customer_id FROM customers);",
        "Orphan Users/Reps": "SELECT COUNT(*) FROM activities WHERE sales_rep_id IS NOT NULL AND sales_rep_id NOT IN (SELECT rep_id FROM sales_reps);"
    }

    print(f"Total Activities: {total}")
    for name, query in queries.items():
        c.execute(query)
        count = c.fetchone()[0]
        print(f"{name}: {count}")

    conn.close()

if __name__ == "__main__":
    run_audit()
