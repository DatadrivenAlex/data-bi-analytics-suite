# Tableau handoff

Use the same star schema as Power BI: the CSV files in `warehouse/` or the PostgreSQL tables loaded by `bi-analytics run --postgres`. Tableau calculations below match `sql/kpis/`.

## Connect

### CSV

1. Run `bi-analytics run`.
2. **Connect > Text file** and open `warehouse/fact_sales.csv`.
3. On the data source canvas, add each `dim_*.csv` as a relationship, not a join. Relationships keep the fact grain and avoid duplicating line amounts.
4. Set `full_date`, `signup_date`, `start_date`, and `end_date` to Date.
5. Set `is_returned`, `is_weekend`, and `is_active` to Boolean. The text values are `true` and `false`.
6. Leave `rejects.csv` out of this data source. It is a quarantine list, not a dimension.

### PostgreSQL

1. Start the optional stack with `docker compose up --build`.
2. **Connect > PostgreSQL**. Server `localhost`, port `5432`, database `bi_analytics`, user `bi`, password `bi`.
3. Drag `fact_sales` onto the canvas and relate the dimension tables.
4. The local password is a demo credential. Do not point this workbook at a shared server that uses it.

## Relationships

| Fact field | Dimension field | Cardinality |
| :--- | :--- | :--- |
| `date_key` | `dim_date.date_key` | Many to one |
| `customer_key` | `dim_customer.customer_key` | Many to one |
| `product_key` | `dim_product.product_key` | Many to one |
| `store_key` | `dim_store.store_key` | Many to one |
| `promotion_key` | `dim_promotion.promotion_key` | Many to one |

`channel` is a field on `fact_sales`. Use it as a dimension. Do not create a separate channel table unless you need a conformed channel across other facts.

## Calculated fields

Create these on `fact_sales` unless noted.

```tableau
// Net Revenue
SUM([net_amount])

// Margin Amount
SUM([margin_amount])

// Margin %
SUM([margin_amount]) / NULLIF(SUM([net_amount]), 0)

// Units Sold
SUM(IF NOT [is_returned] THEN [quantity] END)

// Completed Orders
COUNTD(IF NOT [is_returned] THEN [order_id] END)

// Returned Orders
COUNTD(IF [is_returned] THEN [order_id] END)

// Return Rate
[Returned Orders] / NULLIF([Completed Orders] + [Returned Orders], 0)

// Average Order Value
SUM([net_amount]) / NULLIF([Completed Orders], 0)

// Active Customers
COUNTD(IF NOT [is_returned] THEN [customer_key] END)
```

Revenue rank at product level. Tableau's default rank mode is Competition, which matches SQL `RANK()`: ties share a place and the next place skips.

```tableau
RANK(SUM([net_amount]), 'desc')
```

Dense rank does not match the SQL view. Unique rank breaks ties and does not match it either.

Category share:

```tableau
SUM([net_amount]) / TOTAL(SUM([net_amount]))
```

Compute the table calculation along `category`.

Recency, using the model's as-of date rather than today:

```tableau
// As Of Date, on dim_date
MAX([full_date])

// Last Completed Order
MAX(IF NOT [is_returned] THEN [full_date] END)

// Recency Days
DATEDIFF('day', [Last Completed Order], [As Of Date])
```

`dim_date.day_index` is the integer the SQL view subtracts. A `DATEDIFF` between the two dates is the same number.

## Workbook outline

1. **Executive.** Four BANs: net revenue, margin %, average order value, return rate. A line or bar of net revenue by month, with year as colour or small multiple. A treemap of category.
2. **Product.** A text table of product name, category, net revenue, margin %, units sold, and rank. Filters for category and brand.
3. **Store.** A bar of net revenue by store name, with region and format as filters, plus Web versus Store.
4. **Customer.** A table of full name, segment, country, completed orders, net revenue, and recency. Sort by net revenue descending.

Format currency as EUR with two decimals. Format `Margin %`, `Return Rate`, and the category share as percentages. The ratio `0.4238` is 42.38% once the default number format is percentage. The SQL CSV extracts store the ratio, not the percent.

## Extracts and refresh

Create a Tableau extract after the relationships are in place. Refresh it after the next `bi-analytics run`. If the workbook uses PostgreSQL, refresh after `bi-analytics run --postgres`.

The sample calendar ends on 2025-06-30. A relative date filter anchored on today's date will return no rows. Filter `full_date` inside the sample span, or drop the relative filter while reviewing the demo.
