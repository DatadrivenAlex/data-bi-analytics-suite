-- PostgreSQL 14+ KPI view. Also executed locally by DuckDB.
-- Single row covering the whole fact. as_of_date is the latest calendar day
-- in dim_date, which is the latest accepted order date.

CREATE OR REPLACE VIEW vw_kpi_executive_summary AS
SELECT
    (SELECT MAX(full_date) FROM dim_date) AS as_of_date,
    COALESCE(SUM(f.net_amount), 0) AS net_revenue,
    COALESCE(SUM(f.margin_amount), 0) AS margin_amount,
    ROUND(
        CAST(COALESCE(SUM(f.margin_amount), 0) AS DECIMAL(18, 6))
        / NULLIF(CAST(COALESCE(SUM(f.net_amount), 0) AS DECIMAL(18, 6)), 0),
        4
    ) AS margin_pct,
    COALESCE(SUM(CASE WHEN NOT f.is_returned THEN f.quantity END), 0) AS units_sold,
    COUNT(DISTINCT CASE WHEN NOT f.is_returned THEN f.order_id END) AS completed_orders,
    COUNT(DISTINCT CASE WHEN f.is_returned THEN f.order_id END) AS returned_orders,
    ROUND(
        CAST(COUNT(DISTINCT CASE WHEN f.is_returned THEN f.order_id END) AS DECIMAL(18, 6))
        / NULLIF(
            CAST(
                (
                    COUNT(DISTINCT CASE WHEN NOT f.is_returned THEN f.order_id END)
                    + COUNT(DISTINCT CASE WHEN f.is_returned THEN f.order_id END)
                ) AS DECIMAL(18, 6)
            ),
            0
        ),
        4
    ) AS return_rate,
    ROUND(
        CAST(COALESCE(SUM(f.net_amount), 0) AS DECIMAL(18, 6))
        / NULLIF(
            CAST(COUNT(DISTINCT CASE WHEN NOT f.is_returned THEN f.order_id END) AS DECIMAL(18, 6)),
            0
        ),
        2
    ) AS average_order_value,
    COUNT(DISTINCT CASE WHEN NOT f.is_returned THEN f.customer_key END) AS active_customers
FROM fact_sales AS f;
