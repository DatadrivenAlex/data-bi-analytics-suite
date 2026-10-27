-- PostgreSQL 14+ KPI view. Also executed locally by DuckDB.

CREATE OR REPLACE VIEW vw_kpi_store_performance AS
SELECT
    s.store_key,
    s.store_id,
    s.store_name,
    s.region,
    s.country,
    s.store_format,
    COALESCE(SUM(f.net_amount), 0) AS net_revenue,
    COALESCE(SUM(f.margin_amount), 0) AS margin_amount,
    COUNT(DISTINCT CASE WHEN NOT f.is_returned THEN f.order_id END) AS completed_orders,
    ROUND(
        CAST(COALESCE(SUM(f.net_amount), 0) AS DECIMAL(18, 6))
        / NULLIF(
            CAST(COUNT(DISTINCT CASE WHEN NOT f.is_returned THEN f.order_id END) AS DECIMAL(18, 6)),
            0
        ),
        2
    ) AS average_order_value
FROM fact_sales AS f
JOIN dim_store AS s
    ON s.store_key = f.store_key
GROUP BY s.store_key, s.store_id, s.store_name, s.region, s.country, s.store_format
ORDER BY net_revenue DESC, s.store_id;
