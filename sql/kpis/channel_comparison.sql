-- PostgreSQL 14+ KPI view. Also executed locally by DuckDB.
-- Channel is a degenerate dimension stored on the fact (Web or Store).

CREATE OR REPLACE VIEW vw_kpi_channel_comparison AS
SELECT
    f.channel,
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
GROUP BY f.channel
ORDER BY f.channel;
