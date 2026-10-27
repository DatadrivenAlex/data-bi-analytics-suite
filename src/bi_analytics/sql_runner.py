"""Execute the PostgreSQL KPI scripts on DuckDB for offline runs.

DuckDB is the local engine so ``bi-analytics run`` and pytest do not need a
database server. The scripts themselves avoid engine-specific syntax; Docker
Compose loads the same files into PostgreSQL.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from bi_analytics.schema import DATE_COLUMNS, KPI_VIEWS, LOAD_ORDER
from bi_analytics.transform import StarSchema

_TABLE_SELECT = {
    "dim_date": """
        CREATE TABLE dim_date AS
        SELECT
            CAST(date_key AS INTEGER) AS date_key,
            CAST(NULLIF(full_date, '') AS DATE) AS full_date,
            CAST(year AS INTEGER) AS year,
            CAST(quarter AS INTEGER) AS quarter,
            CAST(month AS INTEGER) AS month,
            CAST(month_name AS VARCHAR) AS month_name,
            CAST(day_of_month AS INTEGER) AS day_of_month,
            CAST(day_name AS VARCHAR) AS day_name,
            CAST(iso_week AS INTEGER) AS iso_week,
            CAST(is_weekend AS BOOLEAN) AS is_weekend,
            CAST(day_index AS INTEGER) AS day_index
        FROM dim_date_src
    """,
    "dim_customer": """
        CREATE TABLE dim_customer AS
        SELECT
            CAST(customer_key AS INTEGER) AS customer_key,
            CAST(customer_id AS VARCHAR) AS customer_id,
            CAST(full_name AS VARCHAR) AS full_name,
            CAST(email AS VARCHAR) AS email,
            CAST(segment AS VARCHAR) AS segment,
            CAST(city AS VARCHAR) AS city,
            CAST(country AS VARCHAR) AS country,
            CAST(NULLIF(signup_date, '') AS DATE) AS signup_date
        FROM dim_customer_src
    """,
    "dim_product": """
        CREATE TABLE dim_product AS
        SELECT
            CAST(product_key AS INTEGER) AS product_key,
            CAST(sku AS VARCHAR) AS sku,
            CAST(product_name AS VARCHAR) AS product_name,
            CAST(category AS VARCHAR) AS category,
            CAST(subcategory AS VARCHAR) AS subcategory,
            CAST(brand AS VARCHAR) AS brand,
            CAST(unit_cost AS DECIMAL(18, 2)) AS unit_cost,
            CAST(is_active AS BOOLEAN) AS is_active
        FROM dim_product_src
    """,
    "dim_store": """
        CREATE TABLE dim_store AS
        SELECT
            CAST(store_key AS INTEGER) AS store_key,
            CAST(store_id AS VARCHAR) AS store_id,
            CAST(store_name AS VARCHAR) AS store_name,
            CAST(city AS VARCHAR) AS city,
            CAST(country AS VARCHAR) AS country,
            CAST(region AS VARCHAR) AS region,
            CAST(store_format AS VARCHAR) AS store_format
        FROM dim_store_src
    """,
    "dim_promotion": """
        CREATE TABLE dim_promotion AS
        SELECT
            CAST(promotion_key AS INTEGER) AS promotion_key,
            CAST(promo_code AS VARCHAR) AS promo_code,
            CAST(promo_name AS VARCHAR) AS promo_name,
            CAST(NULLIF(start_date, '') AS DATE) AS start_date,
            CAST(NULLIF(end_date, '') AS DATE) AS end_date
        FROM dim_promotion_src
    """,
    "fact_sales": """
        CREATE TABLE fact_sales AS
        SELECT
            CAST(sales_key AS INTEGER) AS sales_key,
            CAST(order_line_id AS VARCHAR) AS order_line_id,
            CAST(order_id AS VARCHAR) AS order_id,
            CAST(date_key AS INTEGER) AS date_key,
            CAST(customer_key AS INTEGER) AS customer_key,
            CAST(product_key AS INTEGER) AS product_key,
            CAST(store_key AS INTEGER) AS store_key,
            CAST(promotion_key AS INTEGER) AS promotion_key,
            CAST(channel AS VARCHAR) AS channel,
            CAST(quantity AS INTEGER) AS quantity,
            CAST(unit_price AS DECIMAL(18, 2)) AS unit_price,
            CAST(discount_pct AS DECIMAL(8, 4)) AS discount_pct,
            CAST(gross_amount AS DECIMAL(18, 2)) AS gross_amount,
            CAST(discount_amount AS DECIMAL(18, 2)) AS discount_amount,
            CAST(net_amount AS DECIMAL(18, 2)) AS net_amount,
            CAST(cost_amount AS DECIMAL(18, 2)) AS cost_amount,
            CAST(margin_amount AS DECIMAL(18, 2)) AS margin_amount,
            CAST(return_amount AS DECIMAL(18, 2)) AS return_amount,
            CAST(is_returned AS BOOLEAN) AS is_returned
        FROM fact_sales_src
    """,
}

_EMPTY_DDL = {
    "dim_date": """
        CREATE TABLE dim_date (
            date_key INTEGER,
            full_date DATE,
            year INTEGER,
            quarter INTEGER,
            month INTEGER,
            month_name VARCHAR,
            day_of_month INTEGER,
            day_name VARCHAR,
            iso_week INTEGER,
            is_weekend BOOLEAN,
            day_index INTEGER
        )
    """,
    "dim_customer": """
        CREATE TABLE dim_customer (
            customer_key INTEGER,
            customer_id VARCHAR,
            full_name VARCHAR,
            email VARCHAR,
            segment VARCHAR,
            city VARCHAR,
            country VARCHAR,
            signup_date DATE
        )
    """,
    "dim_product": """
        CREATE TABLE dim_product (
            product_key INTEGER,
            sku VARCHAR,
            product_name VARCHAR,
            category VARCHAR,
            subcategory VARCHAR,
            brand VARCHAR,
            unit_cost DECIMAL(18, 2),
            is_active BOOLEAN
        )
    """,
    "dim_store": """
        CREATE TABLE dim_store (
            store_key INTEGER,
            store_id VARCHAR,
            store_name VARCHAR,
            city VARCHAR,
            country VARCHAR,
            region VARCHAR,
            store_format VARCHAR
        )
    """,
    "dim_promotion": """
        CREATE TABLE dim_promotion (
            promotion_key INTEGER,
            promo_code VARCHAR,
            promo_name VARCHAR,
            start_date DATE,
            end_date DATE
        )
    """,
    "fact_sales": """
        CREATE TABLE fact_sales (
            sales_key INTEGER,
            order_line_id VARCHAR,
            order_id VARCHAR,
            date_key INTEGER,
            customer_key INTEGER,
            product_key INTEGER,
            store_key INTEGER,
            promotion_key INTEGER,
            channel VARCHAR,
            quantity INTEGER,
            unit_price DECIMAL(18, 2),
            discount_pct DECIMAL(8, 4),
            gross_amount DECIMAL(18, 2),
            discount_amount DECIMAL(18, 2),
            net_amount DECIMAL(18, 2),
            cost_amount DECIMAL(18, 2),
            margin_amount DECIMAL(18, 2),
            return_amount DECIMAL(18, 2),
            is_returned BOOLEAN
        )
    """,
}


def execute_kpi_sql(schema: StarSchema, sql_dir: Path) -> dict[str, pd.DataFrame]:
    """Materialize the star schema and return one frame per KPI view."""
    kpi_dir = sql_dir / "kpis"
    missing = [name for name in KPI_VIEWS if not (kpi_dir / f"{name}.sql").is_file()]
    if missing:
        raise FileNotFoundError(f"Missing KPI SQL scripts: {', '.join(missing)}")

    connection = duckdb.connect(database=":memory:")
    try:
        tables = schema.tables()
        for name in LOAD_ORDER:
            _load_table(connection, name, tables[name])
        frames: dict[str, pd.DataFrame] = {}
        for name in KPI_VIEWS:
            script = (kpi_dir / f"{name}.sql").read_text(encoding="utf-8")
            connection.execute(script)
            view = f"vw_kpi_{name}"
            columns = [row[0] for row in connection.execute(f"DESCRIBE {view}").fetchall()]
            select_list = ", ".join(f'CAST("{column}" AS VARCHAR) AS "{column}"' for column in columns)
            frames[name] = connection.execute(f"SELECT {select_list} FROM {view}").fetchdf()
        return frames
    finally:
        connection.close()


def _load_table(connection: duckdb.DuckDBPyConnection, name: str, frame: pd.DataFrame) -> None:
    if name not in _TABLE_SELECT:
        raise ValueError(f"Unexpected warehouse table: {name}")
    if frame.empty:
        connection.execute(_EMPTY_DDL[name])
        return
    prepared = frame.copy()
    for column in DATE_COLUMNS.intersection(prepared.columns):
        prepared[column] = [
            "" if value is None or (isinstance(value, float) and pd.isna(value)) else str(value)[:10]
            for value in prepared[column]
        ]
    connection.register(f"{name}_src", prepared)
    connection.execute(_TABLE_SELECT[name])
