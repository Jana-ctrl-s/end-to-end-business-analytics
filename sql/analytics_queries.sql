-- =============================================================================
-- Analytical SQL Queries Answering Core Business Questions (CRISP-DM Phase 4)
-- =============================================================================

-- Q1: Month-over-Month (MoM) Revenue & Profit Growth Trajectory
WITH monthly AS (
    SELECT
        order_month,
        SUM(gross_revenue_usd) AS revenue_usd,
        SUM(net_profit_usd) AS profit_usd,
        COUNT(DISTINCT order_id) AS orders
    FROM stg_orders_clean
    GROUP BY order_month
)
SELECT
    order_month,
    ROUND(revenue_usd, 2) AS revenue_usd,
    ROUND(profit_usd, 2) AS profit_usd,
    orders,
    ROUND(
        100.0 * (revenue_usd - LAG(revenue_usd) OVER (ORDER BY order_month))
        / NULLIF(LAG(revenue_usd) OVER (ORDER BY order_month), 0),
        2
    ) AS mom_revenue_growth_pct
FROM monthly
ORDER BY order_month;

-- Q2: Regional Revenue, Margin, and Churn Rate Leaderboard
SELECT
    macro_region,
    country_name,
    total_customers,
    total_revenue_usd,
    total_profit_usd,
    avg_csat_score,
    churn_rate_pct,
    gdp_growth_pct
FROM vw_regional_performance
ORDER BY total_revenue_usd DESC;

-- Q3: Customer Cohort Retention & Revenue by Signup Quarter
SELECT
    SUBSTR(signup_date, 1, 4) || '-Q' ||
        CAST(((CAST(SUBSTR(signup_date, 6, 2) AS INTEGER) - 1) / 3) + 1 AS TEXT) AS signup_quarter,
    COUNT(*) AS cohort_customers,
    ROUND(100.0 * (1.0 - AVG(c360.is_churned)), 2) AS retention_rate_pct,
    ROUND(AVG(c360.hist_total_revenue_usd), 2) AS avg_hist_revenue_usd,
    ROUND(AVG(c360.next_12m_revenue_usd), 2) AS avg_forward_revenue_usd
FROM dim_customers dc
JOIN stg_customer_360 c360 ON dc.customer_id = c360.customer_id
GROUP BY signup_quarter
ORDER BY signup_quarter;

-- Q4: Churn Drivers by Contract Type & CSAT Satisfaction Band
SELECT
    contract_type,
    CASE
        WHEN avg_csat < 3.0 THEN 'Low (<3.0)'
        WHEN avg_csat < 4.0 THEN 'Moderate (3.0-3.9)'
        ELSE 'High (4.0-5.0)'
    END AS csat_band,
    COUNT(*) AS customers,
    ROUND(100.0 * AVG(is_churned), 2) AS churn_rate_pct,
    ROUND(AVG(recency_days), 1) AS avg_recency_days,
    ROUND(AVG(escalation_rate) * 100.0, 2) AS avg_escalation_pct
FROM stg_customer_360
GROUP BY contract_type, csat_band
ORDER BY contract_type, churn_rate_pct DESC;

-- Q5: Product Category Profitability & Margin Comparison
SELECT
    category,
    sku_count,
    units_sold,
    category_revenue_usd,
    category_profit_usd,
    profit_margin_pct,
    competitor_price_index
FROM vw_product_profitability
ORDER BY profit_margin_pct DESC;

-- Q6: Inventory Reorder Alert Report (Low Stock SKUs)
SELECT
    product_id,
    sku,
    product_name,
    category,
    stock_quantity,
    reorder_level,
    (reorder_level - stock_quantity) AS units_below_threshold
FROM dim_products
WHERE stock_quantity <= reorder_level
ORDER BY units_below_threshold DESC;

-- Q7: Discount Tier Impact on Order Margin & Return Rate
SELECT
    CASE
        WHEN discount_pct = 0 THEN '0% (No Discount)'
        WHEN discount_pct <= 0.10 THEN '1%-10%'
        WHEN discount_pct <= 0.20 THEN '11%-20%'
        ELSE '>20%'
    END AS discount_tier,
    COUNT(*) AS order_count,
    ROUND(AVG(gross_revenue_usd), 2) AS avg_order_revenue,
    ROUND(100.0 * SUM(net_profit_usd) / NULLIF(SUM(gross_revenue_usd), 0), 2) AS net_margin_pct,
    ROUND(100.0 * AVG(CASE WHEN order_status = 'Returned' THEN 1.0 ELSE 0.0 END), 2) AS return_rate_pct
FROM stg_orders_clean
GROUP BY discount_tier
ORDER BY net_margin_pct DESC;

-- Q8: External Competitive Price Pressure vs Customer Churn by Primary Category
SELECT
    c.primary_category,
    COUNT(*) AS customers,
    ROUND(AVG(c.competitor_price_index), 3) AS avg_price_index,
    ROUND(100.0 * AVG(c.is_churned), 2) AS churn_rate_pct,
    ROUND(AVG(c.next_12m_revenue_usd), 2) AS avg_next_12m_rev_usd
FROM stg_customer_360 c
GROUP BY c.primary_category
ORDER BY avg_price_index DESC;
