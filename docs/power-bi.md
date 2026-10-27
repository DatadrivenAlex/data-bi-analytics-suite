# Power BI handoff

The published model is the star schema in `warehouse/` or the same tables in PostgreSQL. Build visuals on top of the KPI definitions in `sql/kpis/`. Do not re-aggregate returned lines as if their `net_amount` were still the original ticket. That amount is already in `return_amount`, and `net_amount` is 0.

## Connect

### CSV warehouse

1. Run `bi-analytics run` from the repository root.
2. In Power BI Desktop, use **Get data > Text/CSV** for each `warehouse/dim_*.csv`, `warehouse/fact_sales.csv`, or **Get data > Folder** if you prefer a parameterised path.
3. Set types:
   - dates (`full_date`, `signup_date`, `start_date`, `end_date`) as Date
   - money columns as Decimal number
   - `discount_pct`, and any rate you import from `warehouse/kpis/`, as Decimal number
   - `is_returned`, `is_weekend`, `is_active` as True/False. The files use `true` and `false`. Power Query logical conversion accepts those strings
   - keys and `quantity` as Whole number
4. Do not load `rejects.csv` into the star. Keep it on a data-quality page, or leave it out of the report.

### PostgreSQL

1. `docker compose up --build`, or `bi-analytics run --postgres` against your own `DATABASE_URL`.
2. **Get data > PostgreSQL database**. Server `localhost`, database `bi_analytics`.
3. The local demo login is user `bi`, password `bi`. Use it only on your machine.
4. Import `dim_date`, `dim_customer`, `dim_product`, `dim_store`, `dim_promotion`, and `fact_sales`.
5. The views `vw_kpi_*` are optional. Prefer DAX on the star so slicers work. Use a view when you want a number that is guaranteed to match the SQL file, with no extra filters.

Import, rather than DirectQuery, is the right default for this volume (hundreds of fact rows in the sample, and the same model at a few million rows).

## Relationships

Cardinality is many fact rows to one dimension row. Filter direction is single, from the dimension to the fact.

| From | To |
| :--- | :--- |
| `fact_sales.date_key` | `dim_date.date_key` |
| `fact_sales.customer_key` | `dim_customer.customer_key` |
| `fact_sales.product_key` | `dim_product.product_key` |
| `fact_sales.store_key` | `dim_store.store_key` |
| `fact_sales.promotion_key` | `dim_promotion.promotion_key` |

`channel` stays on the fact. Put it on a slicer directly. Hide the surrogate keys from the report view and browse by `full_date`, `customer_id`, `sku`, `store_name`, and `promo_code`.

Mark `dim_date.full_date` as the date table's date column.

## Measures

These match `sql/kpis/`. Returned lines stay in the fact, so a visual does not need a page filter to "exclude returns" before summing `net_amount`.

```dax
Net Revenue = SUM ( fact_sales[net_amount] )

Margin Amount = SUM ( fact_sales[margin_amount] )

Margin % =
DIVIDE ( [Margin Amount], [Net Revenue] )

Units Sold =
CALCULATE (
    SUM ( fact_sales[quantity] ),
    fact_sales[is_returned] = FALSE
)

Completed Orders =
CALCULATE (
    DISTINCTCOUNT ( fact_sales[order_id] ),
    fact_sales[is_returned] = FALSE
)

Returned Orders =
CALCULATE (
    DISTINCTCOUNT ( fact_sales[order_id] ),
    fact_sales[is_returned] = TRUE
)

Return Rate =
DIVIDE ( [Returned Orders], [Completed Orders] + [Returned Orders] )

Average Order Value =
DIVIDE ( [Net Revenue], [Completed Orders] )

Active Customers =
CALCULATE (
    DISTINCTCOUNT ( fact_sales[customer_key] ),
    fact_sales[is_returned] = FALSE
)
```

Product rank, in a table that is already at product grain:

```dax
Revenue Rank =
RANKX (
    ALL ( dim_product[sku] ),
    [Net Revenue],
    ,
    DESC,
    Skip
)
```

`Skip` is the DAX equivalent of SQL `RANK()`.

Category share:

```dax
Revenue Share =
DIVIDE ( [Net Revenue], CALCULATE ( [Net Revenue], ALL ( dim_product[category] ) ) )
```

Customer recency against the latest order date in the model, not `TODAY()`. The SQL view uses the same as-of date, which is the maximum `full_date` in `dim_date`.

```dax
As Of Date = MAX ( dim_date[full_date] )

Last Completed Order =
CALCULATE (
    MAX ( dim_date[full_date] ),
    fact_sales[is_returned] = FALSE
)

Recency Days =
DATEDIFF ( [Last Completed Order], [As Of Date], DAY )
```

## Suggested pages

1. **Executive.** Cards for net revenue, margin %, AOV, return rate, and active customers. A column chart of `Net Revenue` by `dim_date[month_name]` and `year`. A donut of revenue by `dim_product[category]`.
2. **Product.** Matrix of SKU, category, net revenue, margin %, units, and revenue rank. Slicers for category and brand.
3. **Store and channel.** Clustered bar of net revenue by store, a small table of region and format, and Web versus Store.
4. **Customer.** Table of customer, segment, country, completed orders, net revenue, and recency. A slicer on segment.

Format EUR with two decimals. Format rates as percentages. `margin_pct` in the SQL extracts is a ratio (`0.4238` means 42.38%). DAX `DIVIDE` returns the same ratio. Use a percentage format. Do not divide by 100 again.

## Refresh

Re-run `bi-analytics run` (and `--postgres` if the report uses the database), then refresh the semantic model. The CSV folder path should be a parameter if more than one person opens the report.

The sample's as-of date is 2025-06-30. A relative date filter such as "last 30 days" from the wall clock will hide the sample. Filter on `dim_date` instead.
