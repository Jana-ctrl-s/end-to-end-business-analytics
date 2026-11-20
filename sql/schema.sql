-- =============================================================================
-- End-to-End Business Analytics Decision Platform (NovaMetrics Commerce)
-- PostgreSQL-compatible 3NF Operational & Analytical Warehouse DDL
-- =============================================================================

-- Dimension: Regions & Markets
CREATE TABLE IF NOT EXISTS dim_regions (
    region_id       INTEGER PRIMARY KEY,
    macro_region    VARCHAR(64) NOT NULL,
    country_code    CHAR(3) NOT NULL UNIQUE,
    country_name    VARCHAR(100) NOT NULL,
    currency_code   CHAR(3) NOT NULL,
    primary_city    VARCHAR(100) NOT NULL,
    latitude        DOUBLE PRECISION NOT NULL,
    longitude       DOUBLE PRECISION NOT NULL,
    market_tier     VARCHAR(32) NOT NULL
);

-- Dimension: Product Catalog & Inventory
CREATE TABLE IF NOT EXISTS dim_products (
    product_id      INTEGER PRIMARY KEY,
    sku             VARCHAR(32) NOT NULL UNIQUE,
    product_name    VARCHAR(150) NOT NULL,
    category        VARCHAR(64) NOT NULL,
    unit_cost_usd   NUMERIC(12, 2) NOT NULL CHECK (unit_cost_usd >= 0),
    list_price_usd  NUMERIC(12, 2) NOT NULL CHECK (list_price_usd >= 0),
    reorder_level   INTEGER NOT NULL DEFAULT 25,
    stock_quantity  INTEGER NOT NULL DEFAULT 100
);

-- Dimension: Enterprise & Commercial Customers
CREATE TABLE IF NOT EXISTS dim_customers (
    customer_id         INTEGER PRIMARY KEY,
    customer_code       VARCHAR(32) NOT NULL UNIQUE,
    company_name        VARCHAR(150) NOT NULL,
    segment             VARCHAR(64) NOT NULL,
    contract_type       VARCHAR(32) NOT NULL,
    acquisition_channel VARCHAR(64),
    region_id           INTEGER NOT NULL REFERENCES dim_regions(region_id),
    signup_date         DATE NOT NULL,
    account_tenure_days INTEGER NOT NULL DEFAULT 0,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE
);

-- Fact: Sales Orders & Transactions
CREATE TABLE IF NOT EXISTS fact_orders (
    order_id        INTEGER PRIMARY KEY,
    order_code      VARCHAR(32) NOT NULL,
    customer_id     INTEGER NOT NULL REFERENCES dim_customers(customer_id),
    product_id      INTEGER NOT NULL REFERENCES dim_products(product_id),
    region_id       INTEGER NOT NULL REFERENCES dim_regions(region_id),
    order_date      DATE NOT NULL,
    quantity        INTEGER NOT NULL CHECK (quantity > 0),
    unit_price_usd  NUMERIC(12, 2) NOT NULL,
    discount_pct    NUMERIC(5, 4) DEFAULT 0.0,
    shipping_cost_usd NUMERIC(10, 2) DEFAULT 0.0,
    gross_revenue_usd NUMERIC(14, 2) NOT NULL,
    net_profit_usd  NUMERIC(14, 2) NOT NULL,
    delivery_days   DOUBLE PRECISION,
    payment_method  VARCHAR(40) NOT NULL,
    order_status    VARCHAR(32) NOT NULL
);

-- Fact: Customer Support & Engagement Interactions
CREATE TABLE IF NOT EXISTS fact_customer_interactions (
    interaction_id   INTEGER PRIMARY KEY,
    ticket_code      VARCHAR(32) NOT NULL,
    customer_id      INTEGER NOT NULL REFERENCES dim_customers(customer_id),
    interaction_date DATE NOT NULL,
    channel          VARCHAR(32) NOT NULL,
    issue_category   VARCHAR(64) NOT NULL,
    resolution_hours DOUBLE PRECISION,
    csat_score       DOUBLE PRECISION,
    nps_score        INTEGER,
    escalated        INTEGER NOT NULL DEFAULT 0 CHECK (escalated IN (0, 1))
);

-- Ground-Truth Forward Target Outcomes (Forward Window: 2026-01-01 to 2026-06-30)
CREATE TABLE IF NOT EXISTS customer_future_outcomes (
    customer_id         INTEGER PRIMARY KEY REFERENCES dim_customers(customer_id),
    observation_cutoff  DATE NOT NULL,
    is_churned          INTEGER NOT NULL CHECK (is_churned IN (0, 1)),
    next_12m_revenue_usd NUMERIC(14, 2) NOT NULL CHECK (next_12m_revenue_usd >= 0)
);

-- External Source 1: Macro Economic & FX Indicators (REST API)
CREATE TABLE IF NOT EXISTS ext_macro_indicators (
    country_code        CHAR(3) PRIMARY KEY,
    currency_code       CHAR(3) NOT NULL,
    fx_rate_to_usd      DOUBLE PRECISION NOT NULL,
    gdp_growth_pct      DOUBLE PRECISION NOT NULL,
    indicator_year      INTEGER NOT NULL,
    source_provider     VARCHAR(100) NOT NULL,
    ingested_at_utc     VARCHAR(40) NOT NULL
);

-- External Source 2: Competitive Category Price Benchmarks (Web Scraper)
CREATE TABLE IF NOT EXISTS ext_competitor_benchmarks (
    category                VARCHAR(64) PRIMARY KEY,
    competitor_avg_price    DOUBLE PRECISION NOT NULL,
    competitor_price_index  DOUBLE PRECISION NOT NULL,
    market_rating_avg       DOUBLE PRECISION NOT NULL,
    in_stock_rate           DOUBLE PRECISION NOT NULL,
    scraped_sample_count    INTEGER NOT NULL,
    source_url              VARCHAR(255) NOT NULL,
    ingested_at_utc         VARCHAR(40) NOT NULL
);

-- Analytical Staging Table: Cleaned Orders
CREATE TABLE IF NOT EXISTS stg_orders_clean (
    order_id          INTEGER PRIMARY KEY,
    order_code        VARCHAR(32) NOT NULL,
    customer_id       INTEGER NOT NULL,
    product_id        INTEGER NOT NULL,
    region_id         INTEGER NOT NULL,
    order_date        DATE NOT NULL,
    order_month       VARCHAR(7) NOT NULL,
    quantity          INTEGER NOT NULL,
    unit_price_usd    DOUBLE PRECISION NOT NULL,
    discount_pct      DOUBLE PRECISION NOT NULL,
    shipping_cost_usd DOUBLE PRECISION NOT NULL,
    gross_revenue_usd DOUBLE PRECISION NOT NULL,
    net_profit_usd    DOUBLE PRECISION NOT NULL,
    delivery_days     DOUBLE PRECISION NOT NULL,
    payment_method    VARCHAR(40) NOT NULL,
    order_status      VARCHAR(32) NOT NULL
);

-- Analytical Staging Table: Unified Customer 360 Feature Store
CREATE TABLE IF NOT EXISTS stg_customer_360 (
    customer_id             INTEGER PRIMARY KEY,
    customer_code           VARCHAR(32) NOT NULL,
    segment                 VARCHAR(64) NOT NULL,
    contract_type           VARCHAR(32) NOT NULL,
    acquisition_channel     VARCHAR(64) NOT NULL,
    macro_region            VARCHAR(64) NOT NULL,
    country_code            CHAR(3) NOT NULL,
    country_name            VARCHAR(100) NOT NULL,
    primary_category        VARCHAR(64) NOT NULL,
    account_tenure_days     INTEGER NOT NULL,
    recency_days            DOUBLE PRECISION NOT NULL,
    order_frequency         INTEGER NOT NULL,
    hist_total_revenue_usd  DOUBLE PRECISION NOT NULL,
    hist_total_profit_usd   DOUBLE PRECISION NOT NULL,
    avg_order_value_usd     DOUBLE PRECISION NOT NULL,
    recent_90d_revenue_usd  DOUBLE PRECISION NOT NULL,
    spend_momentum_ratio    DOUBLE PRECISION NOT NULL,
    avg_discount_pct        DOUBLE PRECISION NOT NULL,
    avg_delivery_days       DOUBLE PRECISION NOT NULL,
    return_rate             DOUBLE PRECISION NOT NULL,
    support_tickets_count   INTEGER NOT NULL,
    avg_resolution_hours    DOUBLE PRECISION NOT NULL,
    avg_csat                DOUBLE PRECISION NOT NULL,
    avg_nps                 DOUBLE PRECISION NOT NULL,
    escalation_rate         DOUBLE PRECISION NOT NULL,
    gdp_growth_pct          DOUBLE PRECISION NOT NULL,
    fx_rate_to_usd          DOUBLE PRECISION NOT NULL,
    competitor_price_index  DOUBLE PRECISION NOT NULL,
    is_churned              INTEGER NOT NULL,
    next_12m_revenue_usd    DOUBLE PRECISION NOT NULL,
    cluster_id              INTEGER,
    cluster_label           VARCHAR(64)
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_orders_customer ON fact_orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_date ON fact_orders(order_date);
CREATE INDEX IF NOT EXISTS idx_orders_region ON fact_orders(region_id);
CREATE INDEX IF NOT EXISTS idx_interactions_customer ON fact_customer_interactions(customer_id);
CREATE INDEX IF NOT EXISTS idx_customers_region ON dim_customers(region_id);
