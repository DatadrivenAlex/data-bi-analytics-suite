-- PostgreSQL 14+ KPI view. Also executed locally by DuckDB.
-- revenue_share is category net revenue divided by total fact net revenue.

CREATE OR REPLACE VIEW vw_kpi_category_mix AS
SELECT
    p.category,
    COALESCE(SUM(f.net_amount), 0) AS net_revenue,
    ROUND(
        CAST(COALESCE(SUM(f.net_amount), 0) AS DECIMAL(18, 6))
        / NULLIF(
            (
                SELECT CAST(COALESCE(SUM(net_amount), 0) AS DECIMAL(18, 6))
                FROM fact_sales
            ),
            0
        ),
        4
    ) AS revenue_share
FROM fact_sales AS f
JOIN dim_product AS p
    ON p.product_key = f.product_key
GROUP BY p.category
ORDER BY net_revenue DESC, p.category;
