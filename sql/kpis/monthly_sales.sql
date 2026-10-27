-- PostgreSQL 14+ KPI view. Also executed locally by DuckDB.
-- Dense calendar months between the first and last order date.
-- Net revenue excludes returned tickets (those rows keep net_amount = 0).
-- Average order value uses completed orders only.

CREATE OR REPLACE VIEW vw_kpi_monthly_sales AS
WITH months AS (
    SELECT DISTINCT year, month, month_name
    FROM dim_date
)
SELECT
    m.year,
    m.month,
    m.month_name,
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
    ) AS average_order_value
FROM months AS m
JOIN dim_date AS d
    ON d.year = m.year
    AND d.month = m.month
LEFT JOIN fact_sales AS f
    ON f.date_key = d.date_key
GROUP BY m.year, m.month, m.month_name
ORDER BY m.year, m.month;
