"""Column contracts shared by the model, SQL DDL, and exports."""

DIM_DATE_COLUMNS = [
    "date_key",
    "full_date",
    "year",
    "quarter",
    "month",
    "month_name",
    "day_of_month",
    "day_name",
    "iso_week",
    "is_weekend",
    "day_index",
]

DIM_CUSTOMER_COLUMNS = [
    "customer_key",
    "customer_id",
    "full_name",
    "email",
    "segment",
    "city",
    "country",
    "signup_date",
]

DIM_PRODUCT_COLUMNS = [
    "product_key",
    "sku",
    "product_name",
    "category",
    "subcategory",
    "brand",
    "unit_cost",
    "is_active",
]

DIM_STORE_COLUMNS = [
    "store_key",
    "store_id",
    "store_name",
    "city",
    "country",
    "region",
    "store_format",
]

DIM_PROMOTION_COLUMNS = [
    "promotion_key",
    "promo_code",
    "promo_name",
    "start_date",
    "end_date",
]

FACT_SALES_COLUMNS = [
    "sales_key",
    "order_line_id",
    "order_id",
    "date_key",
    "customer_key",
    "product_key",
    "store_key",
    "promotion_key",
    "channel",
    "quantity",
    "unit_price",
    "discount_pct",
    "gross_amount",
    "discount_amount",
    "net_amount",
    "cost_amount",
    "margin_amount",
    "return_amount",
    "is_returned",
]

REJECT_COLUMNS = [
    "reason",
    "entity",
    "order_id",
    "order_line_id",
    "detail",
]

TABLE_COLUMNS = {
    "dim_date": DIM_DATE_COLUMNS,
    "dim_customer": DIM_CUSTOMER_COLUMNS,
    "dim_product": DIM_PRODUCT_COLUMNS,
    "dim_store": DIM_STORE_COLUMNS,
    "dim_promotion": DIM_PROMOTION_COLUMNS,
    "fact_sales": FACT_SALES_COLUMNS,
}

LOAD_ORDER = [
    "dim_date",
    "dim_customer",
    "dim_product",
    "dim_store",
    "dim_promotion",
    "fact_sales",
]

KPI_VIEWS = [
    "monthly_sales",
    "product_performance",
    "store_performance",
    "customer_value",
    "category_mix",
    "channel_comparison",
    "executive_summary",
]

MONTHLY_COLUMNS = [
    "year",
    "month",
    "month_name",
    "net_revenue",
    "margin_amount",
    "margin_pct",
    "units_sold",
    "completed_orders",
    "returned_orders",
    "return_rate",
    "average_order_value",
]

PRODUCT_COLUMNS = [
    "product_key",
    "sku",
    "product_name",
    "category",
    "net_revenue",
    "margin_amount",
    "margin_pct",
    "units_sold",
    "revenue_rank",
]

STORE_COLUMNS = [
    "store_key",
    "store_id",
    "store_name",
    "region",
    "country",
    "store_format",
    "net_revenue",
    "margin_amount",
    "completed_orders",
    "average_order_value",
]

CUSTOMER_COLUMNS = [
    "customer_key",
    "customer_id",
    "full_name",
    "segment",
    "country",
    "completed_orders",
    "net_revenue",
    "first_order_date",
    "last_order_date",
    "recency_days",
]

CATEGORY_COLUMNS = [
    "category",
    "net_revenue",
    "revenue_share",
]

CHANNEL_COLUMNS = [
    "channel",
    "net_revenue",
    "margin_amount",
    "completed_orders",
    "average_order_value",
]

EXECUTIVE_COLUMNS = [
    "as_of_date",
    "net_revenue",
    "margin_amount",
    "margin_pct",
    "units_sold",
    "completed_orders",
    "returned_orders",
    "return_rate",
    "average_order_value",
    "active_customers",
]

KPI_COLUMNS = {
    "monthly_sales": MONTHLY_COLUMNS,
    "product_performance": PRODUCT_COLUMNS,
    "store_performance": STORE_COLUMNS,
    "customer_value": CUSTOMER_COLUMNS,
    "category_mix": CATEGORY_COLUMNS,
    "channel_comparison": CHANNEL_COLUMNS,
    "executive_summary": EXECUTIVE_COLUMNS,
}

MONEY_COLUMNS = {
    "unit_cost",
    "unit_price",
    "gross_amount",
    "discount_amount",
    "net_amount",
    "cost_amount",
    "margin_amount",
    "return_amount",
    "net_revenue",
    "average_order_value",
}

RATE_COLUMNS = {
    "discount_pct",
    "margin_pct",
    "return_rate",
    "revenue_share",
}

DATE_COLUMNS = {
    "full_date",
    "signup_date",
    "start_date",
    "end_date",
    "first_order_date",
    "last_order_date",
    "as_of_date",
}

BOOL_COLUMNS = {"is_weekend", "is_active", "is_returned"}

RAW_FILES = {
    "customers": "customers.csv",
    "products": "products.csv",
    "stores": "stores.csv",
    "promotions": "promotions.csv",
    "orders": "orders.csv",
    "order_lines": "order_lines.csv",
}

RAW_COLUMNS = {
    "customers": [
        "customer_id",
        "full_name",
        "email",
        "segment",
        "city",
        "country",
        "signup_date",
    ],
    "products": [
        "sku",
        "product_name",
        "category",
        "subcategory",
        "brand",
        "unit_cost",
        "is_active",
    ],
    "stores": [
        "store_id",
        "store_name",
        "city",
        "country",
        "region",
        "store_format",
    ],
    "promotions": ["promo_code", "promo_name", "start_date", "end_date"],
    "orders": [
        "order_id",
        "order_datetime",
        "customer_id",
        "store_id",
        "channel",
        "status",
        "promo_code",
    ],
    "order_lines": [
        "order_line_id",
        "order_id",
        "sku",
        "quantity",
        "unit_price",
        "discount_pct",
    ],
}
