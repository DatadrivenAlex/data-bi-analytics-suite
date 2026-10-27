-- Lumen & Field retail star schema.
-- Target: PostgreSQL 14+. Loaded by `bi-analytics run --postgres`.
-- Local KPI execution uses the same column names through DuckDB.

CREATE TABLE dim_date (
    date_key INTEGER PRIMARY KEY,
    full_date DATE NOT NULL UNIQUE,
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    month INTEGER NOT NULL,
    month_name VARCHAR(16) NOT NULL,
    day_of_month INTEGER NOT NULL,
    day_name VARCHAR(16) NOT NULL,
    iso_week INTEGER NOT NULL,
    is_weekend BOOLEAN NOT NULL,
    day_index INTEGER NOT NULL
);

CREATE TABLE dim_customer (
    customer_key INTEGER PRIMARY KEY,
    customer_id VARCHAR(32) NOT NULL UNIQUE,
    full_name VARCHAR(200) NOT NULL,
    email VARCHAR(320) NOT NULL,
    segment VARCHAR(32) NOT NULL,
    city VARCHAR(120) NOT NULL,
    country VARCHAR(80) NOT NULL,
    signup_date DATE
);

CREATE TABLE dim_product (
    product_key INTEGER PRIMARY KEY,
    sku VARCHAR(32) NOT NULL UNIQUE,
    product_name VARCHAR(200) NOT NULL,
    category VARCHAR(80) NOT NULL,
    subcategory VARCHAR(80) NOT NULL,
    brand VARCHAR(80) NOT NULL,
    unit_cost NUMERIC(18, 2) NOT NULL,
    is_active BOOLEAN NOT NULL
);

CREATE TABLE dim_store (
    store_key INTEGER PRIMARY KEY,
    store_id VARCHAR(32) NOT NULL UNIQUE,
    store_name VARCHAR(200) NOT NULL,
    city VARCHAR(120) NOT NULL,
    country VARCHAR(80) NOT NULL,
    region VARCHAR(32) NOT NULL,
    store_format VARCHAR(32) NOT NULL
);

CREATE TABLE dim_promotion (
    promotion_key INTEGER PRIMARY KEY,
    promo_code VARCHAR(32) NOT NULL UNIQUE,
    promo_name VARCHAR(200) NOT NULL,
    start_date DATE,
    end_date DATE
);

CREATE TABLE fact_sales (
    sales_key INTEGER PRIMARY KEY,
    order_line_id VARCHAR(32) NOT NULL UNIQUE,
    order_id VARCHAR(32) NOT NULL,
    date_key INTEGER NOT NULL REFERENCES dim_date (date_key),
    customer_key INTEGER NOT NULL REFERENCES dim_customer (customer_key),
    product_key INTEGER NOT NULL REFERENCES dim_product (product_key),
    store_key INTEGER NOT NULL REFERENCES dim_store (store_key),
    promotion_key INTEGER NOT NULL REFERENCES dim_promotion (promotion_key),
    channel VARCHAR(16) NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price NUMERIC(18, 2) NOT NULL,
    discount_pct NUMERIC(8, 4) NOT NULL,
    gross_amount NUMERIC(18, 2) NOT NULL,
    discount_amount NUMERIC(18, 2) NOT NULL,
    net_amount NUMERIC(18, 2) NOT NULL,
    cost_amount NUMERIC(18, 2) NOT NULL,
    margin_amount NUMERIC(18, 2) NOT NULL,
    return_amount NUMERIC(18, 2) NOT NULL,
    is_returned BOOLEAN NOT NULL,
    CONSTRAINT fact_sales_quantity_positive CHECK (quantity > 0),
    CONSTRAINT fact_sales_channel CHECK (channel IN ('Web', 'Store'))
);

CREATE INDEX idx_fact_sales_date ON fact_sales (date_key);
CREATE INDEX idx_fact_sales_customer ON fact_sales (customer_key);
CREATE INDEX idx_fact_sales_product ON fact_sales (product_key);
CREATE INDEX idx_fact_sales_store ON fact_sales (store_key);
CREATE INDEX idx_fact_sales_promotion ON fact_sales (promotion_key);
CREATE INDEX idx_fact_sales_order ON fact_sales (order_id);
