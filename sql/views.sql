-- =============================================================================
-- Analytical Views for BI Reporting & SQL Consumers
-- Compatible with both PostgreSQL and SQLite
-- =============================================================================

-- 1. Executive KPIs Summary View
DROP VIEW IF EXISTS vw_executive_kpis;
CREATE VIEW vw_executive_kpis AS
SELECT
    COUNT(DISTINCT o.order_id) AS total_orders,
    COUNT(DISTINCT o.customer_id) AS ordering_customers,
    ROUND(SUM(o.gross_revenue_usd), 2) AS total_revenue_usd,
    ROUND(SUM(o.net_profit_usd), 2) AS total_profit_usd,
    ROUND(AVG(o.gross_revenue_usd), 2) AS avg_order_value_usd,
    ROUND(100.0 * SUM(o.net_profit_usd) / NULLIF(SUM(o.gross_revenue_usd), 0), 2) AS gross_margin_pct,
    ROUND(AVG(o.delivery_days), 2) AS avg_delivery_days,
    ROUND(100.0 * AVG(CASE WHEN o.order_status = 'Returned' THEN 1.0 ELSE 0.0 END), 2) AS return_rate_pct
FROM stg_orders_clean o;

-- 2. Monthly Revenue & Profit Trends
DROP VIEW IF EXISTS vw_monthly_revenue_trends;
CREATE VIEW vw_monthly_revenue_trends AS
SELECT
    o.order_month,
    COUNT(DISTINCT o.order_id) AS order_count,
    COUNT(DISTINCT o.customer_id) AS active_customers,
    ROUND(SUM(o.gross_revenue_usd), 2) AS monthly_revenue_usd,
    ROUND(SUM(o.net_profit_usd), 2) AS monthly_profit_usd,
    ROUND(AVG(o.gross_revenue_usd), 2) AS avg_order_value_usd,
    ROUND(AVG(o.discount_pct) * 100.0, 2) AS avg_discount_pct
FROM stg_orders_clean o
GROUP BY o.order_month
ORDER BY o.order_month;

-- 3. Regional Performance & Macro Context
DROP VIEW IF EXISTS vw_regional_performance;
CREATE VIEW vw_regional_performance AS
SELECT
    c.macro_region,
    c.country_code,
    c.country_name,
    COUNT(DISTINCT c.customer_id) AS total_customers,
    ROUND(SUM(c.hist_total_revenue_usd), 2) AS total_revenue_usd,
    ROUND(SUM(c.hist_total_profit_usd), 2) AS total_profit_usd,
    ROUND(AVG(c.avg_csat), 2) AS avg_csat_score,
    ROUND(100.0 * AVG(c.is_churned), 2) AS churn_rate_pct,
    ROUND(AVG(c.gdp_growth_pct), 2) AS gdp_growth_pct,
    ROUND(AVG(c.fx_rate_to_usd), 4) AS fx_rate_to_usd
FROM stg_customer_360 c
GROUP BY c.macro_region, c.country_code, c.country_name
ORDER BY total_revenue_usd DESC;

-- 4. Product Category Profitability & Competitive Benchmark
DROP VIEW IF EXISTS vw_product_profitability;
CREATE VIEW vw_product_profitability AS
SELECT
    p.category,
    COUNT(DISTINCT p.product_id) AS sku_count,
    SUM(o.quantity) AS units_sold,
    ROUND(SUM(o.gross_revenue_usd), 2) AS category_revenue_usd,
    ROUND(SUM(o.net_profit_usd), 2) AS category_profit_usd,
    ROUND(100.0 * SUM(o.net_profit_usd) / NULLIF(SUM(o.gross_revenue_usd), 0), 2) AS profit_margin_pct,
    ROUND(AVG(p.list_price_usd), 2) AS internal_avg_price_usd,
    ROUND(AVG(cb.competitor_avg_price), 2) AS competitor_avg_price_usd,
    ROUND(AVG(cb.competitor_price_index), 3) AS competitor_price_index
FROM stg_orders_clean o
JOIN dim_products p ON o.product_id = p.product_id
LEFT JOIN ext_competitor_benchmarks cb ON p.category = cb.category
GROUP BY p.category
ORDER BY category_revenue_usd DESC;

-- 5. High-Risk Customer Churn Watchlist View
DROP VIEW IF EXISTS vw_customer_churn_risk;
CREATE VIEW vw_customer_churn_risk AS
SELECT
    customer_id,
    customer_code,
    segment,
    contract_type,
    macro_region,
    country_code,
    recency_days,
    order_frequency,
    ROUND(hist_total_revenue_usd, 2) AS hist_total_revenue_usd,
    ROUND(avg_csat, 2) AS avg_csat,
    ROUND(escalation_rate, 3) AS escalation_rate,
    ROUND(spend_momentum_ratio, 3) AS spend_momentum_ratio,
    is_churned,
    ROUND(next_12m_revenue_usd, 2) AS next_12m_revenue_usd,
    cluster_label
FROM stg_customer_360
WHERE recency_days > 90 OR avg_csat < 3.4 OR escalation_rate > 0.25
ORDER BY hist_total_revenue_usd DESC;
