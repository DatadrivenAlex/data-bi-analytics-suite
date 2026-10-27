-- PostgreSQL 14+ KPI view. Also executed locally by DuckDB.
-- One row per product that appears on at least one fact line, including
-- return-only products (their net revenue is zero). revenue_rank is RANK().

CREATE OR REPLACE VIEW vw_kpi_product_performance AS
SELECT
    p.product_key,
    p.sku,
    p.product_name,
    p.category,
    COALESCE(SUM(f.net_amount), 0) AS net_revenue,
    COALESCE(SUM(f.margin_amount), 0) AS margin_amount,
    ROUND(
        CAST(COALESCE(SUM(f.margin_amount), 0) AS DECIMAL(18, 6))
        / NULLIF(CAST(COALESCE(SUM(f.net_amount), 0) AS DECIMAL(18, 6)), 0),
        4
    ) AS margin_pct,
    COALESCE(SUM(CASE WHEN NOT f.is_returned THEN f.quantity END), 0) AS units_sold,
    RANK() OVER (ORDER BY COALESCE(SUM(f.net_amount), 0) DESC) AS revenue_rank
FROM fact_sales AS f
JOIN dim_product AS p
    ON p.product_key = f.product_key
GROUP BY p.product_key, p.sku, p.product_name, p.category
ORDER BY revenue_rank, p.sku;
