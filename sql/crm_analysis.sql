-- ==============================================================================
-- INDIAN B2B CRM DATASET - PROFESSIONAL SQL ANALYSIS SUITE
-- ==============================================================================
-- Note: This file relies on the exact schema provided in `data_dictionary.md`.
-- Ensure all CSVs are imported into your database before running these queries.
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. Total Revenue
-- ------------------------------------------------------------------------------
-- Calculates the total net revenue from all valid customer transactions.
-- Excludes 'Refund' transactions to get the true net revenue.
SELECT 
    SUM(amount_inr) AS total_net_revenue_inr
FROM customer_transactions
WHERE transaction_type != 'Refund';

-- ------------------------------------------------------------------------------
-- 2. Monthly Revenue
-- ------------------------------------------------------------------------------
-- Aggregates transaction volume by month to track revenue growth over time.
SELECT 
    DATE_TRUNC('month', transaction_date) AS revenue_month,
    SUM(amount_inr) AS monthly_revenue_inr,
    COUNT(transaction_id) AS transaction_count
FROM customer_transactions
WHERE transaction_type != 'Refund'
GROUP BY 1
ORDER BY 1;

-- ------------------------------------------------------------------------------
-- 3. Revenue by Industry
-- ------------------------------------------------------------------------------
-- Identifies which industries generate the most closed-won revenue.
-- Joins opportunities with companies and industries.
SELECT 
    i.industry_name,
    COUNT(o.opportunity_id) AS won_deals_count,
    SUM(o.deal_value_inr) AS total_industry_revenue_inr
FROM opportunities o
JOIN companies c ON o.company_id = c.company_id
JOIN industries i ON c.industry_id = i.industry_id
WHERE o.close_outcome = 'Won'
GROUP BY 1
ORDER BY 3 DESC;

-- ------------------------------------------------------------------------------
-- 4. Revenue by Customer
-- ------------------------------------------------------------------------------
-- Calculates total lifetime value (LTV) or revenue per customer.
SELECT 
    c.company_name,
    SUM(t.amount_inr) AS total_customer_revenue_inr,
    MAX(t.transaction_date) AS last_purchase_date
FROM customer_transactions t
JOIN customers cust ON t.customer_id = cust.customer_id
JOIN companies c ON cust.company_id = c.company_id
WHERE t.transaction_type != 'Refund'
GROUP BY 1
ORDER BY 2 DESC;

-- ------------------------------------------------------------------------------
-- 5. Top Customers
-- ------------------------------------------------------------------------------
-- Retrieves the top 10 most valuable customers based on transaction history.
SELECT 
    c.company_name,
    cust.customer_status,
    SUM(t.amount_inr) AS total_revenue_inr
FROM customer_transactions t
JOIN customers cust ON t.customer_id = cust.customer_id
JOIN companies c ON cust.company_id = c.company_id
WHERE t.transaction_type != 'Refund'
GROUP BY 1, 2
ORDER BY 3 DESC
LIMIT 10;

-- ------------------------------------------------------------------------------
-- 6. Lead Conversion Rate
-- ------------------------------------------------------------------------------
-- Calculates the percentage of leads that successfully converted.
SELECT 
    COUNT(CASE WHEN lead_status = 'Converted' THEN 1 END) AS converted_leads,
    COUNT(lead_id) AS total_leads,
    ROUND(
        COUNT(CASE WHEN lead_status = 'Converted' THEN 1 END) * 100.0 / COUNT(lead_id), 
        2
    ) AS conversion_rate_percentage
FROM leads;

-- ------------------------------------------------------------------------------
-- 7. Conversion Rate by Lead Source
-- ------------------------------------------------------------------------------
-- Evaluates which marketing channels (lead sources) have the best conversion rates.
SELECT 
    ls.source_name,
    COUNT(l.lead_id) AS total_leads,
    COUNT(CASE WHEN l.lead_status = 'Converted' THEN 1 END) AS converted_leads,
    ROUND(
        COUNT(CASE WHEN l.lead_status = 'Converted' THEN 1 END) * 100.0 / NULLIF(COUNT(l.lead_id), 0), 
        2
    ) AS conversion_rate_percentage
FROM leads l
JOIN lead_sources ls ON l.lead_source_id = ls.lead_source_id
GROUP BY 1
ORDER BY 4 DESC;

-- ------------------------------------------------------------------------------
-- 8. Campaign Performance
-- ------------------------------------------------------------------------------
-- Measures the ROI of marketing campaigns by tracking the total value of won deals
-- originating from leads attached to each campaign.
SELECT 
    camp.campaign_name,
    camp.budget_inr,
    COUNT(l.lead_id) AS leads_generated,
    SUM(CASE WHEN o.close_outcome = 'Won' THEN o.deal_value_inr ELSE 0 END) AS pipeline_revenue_generated_inr
FROM campaigns camp
LEFT JOIN leads l ON camp.campaign_id = l.campaign_id
LEFT JOIN opportunities o ON l.lead_id = o.lead_id
GROUP BY 1, 2
ORDER BY 4 DESC;

-- ------------------------------------------------------------------------------
-- 9. Opportunity Win Rate
-- ------------------------------------------------------------------------------
-- Calculates the percentage of closed opportunities that were successfully won.
SELECT 
    COUNT(CASE WHEN close_outcome = 'Won' THEN 1 END) AS won_deals,
    COUNT(CASE WHEN close_outcome IN ('Won', 'Lost') THEN 1 END) AS total_closed_deals,
    ROUND(
        COUNT(CASE WHEN close_outcome = 'Won' THEN 1 END) * 100.0 / NULLIF(COUNT(CASE WHEN close_outcome IN ('Won', 'Lost') THEN 1 END), 0), 
        2
    ) AS win_rate_percentage
FROM opportunities;

-- ------------------------------------------------------------------------------
-- 10. Average Deal Size
-- ------------------------------------------------------------------------------
-- Calculates the average monetary value of a won deal.
SELECT 
    ROUND(AVG(deal_value_inr), 2) AS average_won_deal_size_inr
FROM opportunities
WHERE close_outcome = 'Won';

-- ------------------------------------------------------------------------------
-- 11. Average Sales-Cycle Duration
-- ------------------------------------------------------------------------------
-- Calculates the average number of days it takes to close a won opportunity.
SELECT 
    ROUND(AVG(DATE_PART('day', actual_close_date - created_at)), 1) AS average_days_to_close
FROM opportunities
WHERE close_outcome = 'Won' AND actual_close_date IS NOT NULL;

-- ------------------------------------------------------------------------------
-- 12. Sales Representative Performance
-- ------------------------------------------------------------------------------
-- Ranks sales representatives by the total revenue they have closed.
SELECT 
    sr.full_name,
    COUNT(o.opportunity_id) AS deals_won,
    SUM(o.deal_value_inr) AS total_revenue_generated_inr
FROM opportunities o
JOIN sales_reps sr ON o.owner_rep_id = sr.rep_id
WHERE o.close_outcome = 'Won'
GROUP BY 1
ORDER BY 3 DESC;

-- ------------------------------------------------------------------------------
-- 13. Product Revenue
-- ------------------------------------------------------------------------------
-- Determines which products are generating the most revenue based on opportunity line items.
SELECT 
    p.product_name,
    SUM(op.quantity) AS total_units_sold,
    SUM(op.line_total_inr) AS total_product_revenue_inr
FROM opportunity_products op
JOIN products p ON op.product_id = p.product_id
GROUP BY 1
ORDER BY 3 DESC;

-- ------------------------------------------------------------------------------
-- 14. Open Opportunities
-- ------------------------------------------------------------------------------
-- Lists all currently active opportunities (not Won or Lost) ordered by expected close date.
SELECT 
    o.opportunity_id,
    c.company_name,
    o.pipeline_stage,
    o.deal_value_inr,
    o.expected_close_date
FROM opportunities o
JOIN companies c ON o.company_id = c.company_id
WHERE o.close_outcome IS NULL
ORDER BY o.expected_close_date ASC;

-- ------------------------------------------------------------------------------
-- 15. Customer Support Performance
-- ------------------------------------------------------------------------------
-- Aggregates customer support cases by their status to monitor support backlog.
SELECT 
    status,
    priority,
    COUNT(case_id) AS case_count
FROM customer_support_cases
GROUP BY 1, 2
ORDER BY 1, 3 DESC;

-- ------------------------------------------------------------------------------
-- 16. Customers with Possible Churn Risk
-- ------------------------------------------------------------------------------
-- Identifies customers explicitly flagged as 'At Risk' to prioritize retention efforts.
SELECT 
    cust.customer_id,
    c.company_name,
    cust.renewal_date,
    SUM(t.amount_inr) AS lifetime_value_inr
FROM customers cust
JOIN companies c ON cust.company_id = c.company_id
LEFT JOIN customer_transactions t ON cust.customer_id = t.customer_id
WHERE cust.customer_status = 'At Risk'
GROUP BY 1, 2, 3
ORDER BY 4 DESC;
