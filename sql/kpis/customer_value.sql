-- PostgreSQL 14+ KPI view. Also executed locally by DuckDB.
-- Completed orders only. recency_days uses day_index so the query does not
-- depend on engine-specific DATE subtraction.

CREATE OR REPLACE VIEW vw_kpi_customer_value AS
WITH bounds AS (
    SELECT MAX(day_index) AS as_of_index
    FROM dim_date
)
SELECT
    c.customer_key,
    c.customer_id,
    c.full_name,
    c.segment,
    c.country,
    COUNT(DISTINCT f.order_id) AS completed_orders,
    COALESCE(SUM(f.net_amount), 0) AS net_revenue,
    MIN(d.full_date) AS first_order_date,
    MAX(d.full_date) AS last_order_date,
    (SELECT as_of_index FROM bounds) - MAX(d.day_index) AS recency_days
FROM fact_sales AS f
JOIN dim_customer AS c
    ON c.customer_key = f.customer_key
JOIN dim_date AS d
    ON d.date_key = f.date_key
WHERE NOT f.is_returned
GROUP BY c.customer_key, c.customer_id, c.full_name, c.segment, c.country
ORDER BY net_revenue DESC, c.customer_id;
