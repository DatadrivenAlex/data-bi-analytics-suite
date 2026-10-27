"""Pandas KPI calculations.

These definitions are the reference implementation. The SQL views in ``sql/kpis``
must return the same figures; tests compare the two on the sample warehouse.
"""

from __future__ import annotations

from decimal import Decimal

import pandas as pd

from bi_analytics.dates import as_date
from bi_analytics.money import MONEY_PLACES, RATE_PLACES, ZERO, ratio, sum_money, to_decimal
from bi_analytics.schema import KPI_COLUMNS
from bi_analytics.transform import StarSchema


def compute_kpis(schema: StarSchema) -> dict[str, pd.DataFrame]:
    """Return every KPI view as a typed frame sorted for stable exports."""
    frames = {
        "monthly_sales": _monthly_sales(schema),
        "product_performance": _product_performance(schema),
        "store_performance": _store_performance(schema),
        "customer_value": _customer_value(schema),
        "category_mix": _category_mix(schema),
        "channel_comparison": _channel_comparison(schema),
        "executive_summary": _executive_summary(schema),
    }
    return {name: _finalize(name, frame) for name, frame in frames.items()}


def sort_records(name: str, records: list[dict[str, object]]) -> list[dict[str, object]]:
    """Apply the same ordering the SQL views declare."""
    if name == "monthly_sales":
        return sorted(records, key=lambda row: (int(row["year"]), int(row["month"])))
    if name == "product_performance":
        return sorted(records, key=lambda row: (int(row["revenue_rank"]), str(row["sku"])))
    if name == "store_performance":
        return sorted(records, key=lambda row: (-Decimal(row["net_revenue"]), str(row["store_id"])))
    if name == "customer_value":
        return sorted(
            records,
            key=lambda row: (-Decimal(row["net_revenue"]), str(row["customer_id"])),
        )
    if name == "category_mix":
        return sorted(records, key=lambda row: (-Decimal(row["net_revenue"]), str(row["category"])))
    if name == "channel_comparison":
        return sorted(records, key=lambda row: str(row["channel"]))
    return records


def _monthly_sales(schema: StarSchema) -> pd.DataFrame:
    if schema.dim_date.empty:
        return pd.DataFrame(columns=KPI_COLUMNS["monthly_sales"])
    fact = _fact_with_calendar(schema)
    months = (
        schema.dim_date.loc[:, ["year", "month", "month_name"]]
        .drop_duplicates()
        .to_dict(orient="records")
    )
    rows: list[dict[str, object]] = []
    for month in months:
        part = fact[(fact["year"] == month["year"]) & (fact["month"] == month["month"])]
        rows.append(
            {
                "year": int(month["year"]),
                "month": int(month["month"]),
                "month_name": str(month["month_name"]),
                **_commercial_metrics(part),
            }
        )
    return pd.DataFrame(rows)


def _product_performance(schema: StarSchema) -> pd.DataFrame:
    if schema.fact_sales.empty:
        return pd.DataFrame(columns=KPI_COLUMNS["product_performance"])
    fact = schema.fact_sales.merge(
        schema.dim_product.loc[:, ["product_key", "sku", "product_name", "category"]],
        on="product_key",
        how="inner",
    )
    grouped: list[dict[str, object]] = []
    for key, part in fact.groupby(["product_key", "sku", "product_name", "category"], sort=False):
        product_key, sku, product_name, category = key
        metrics = _commercial_metrics(part)
        grouped.append(
            {
                "product_key": int(product_key),
                "sku": str(sku),
                "product_name": str(product_name),
                "category": str(category),
                "net_revenue": metrics["net_revenue"],
                "margin_amount": metrics["margin_amount"],
                "margin_pct": metrics["margin_pct"],
                "units_sold": metrics["units_sold"],
            }
        )
    ranks = _competition_rank([row["net_revenue"] for row in grouped])  # type: ignore[arg-type]
    for row, rank in zip(grouped, ranks):
        row["revenue_rank"] = rank
    return pd.DataFrame(grouped)


def _store_performance(schema: StarSchema) -> pd.DataFrame:
    if schema.fact_sales.empty:
        return pd.DataFrame(columns=KPI_COLUMNS["store_performance"])
    fact = schema.fact_sales.merge(
        schema.dim_store.loc[:, ["store_key", "store_id", "store_name", "region", "country", "store_format"]],
        on="store_key",
        how="inner",
    )
    rows: list[dict[str, object]] = []
    group_columns = ["store_key", "store_id", "store_name", "region", "country", "store_format"]
    for key, part in fact.groupby(group_columns, sort=False):
        store_key, store_id, store_name, region, country, store_format = key
        metrics = _commercial_metrics(part)
        rows.append(
            {
                "store_key": int(store_key),
                "store_id": str(store_id),
                "store_name": str(store_name),
                "region": str(region),
                "country": str(country),
                "store_format": str(store_format),
                "net_revenue": metrics["net_revenue"],
                "margin_amount": metrics["margin_amount"],
                "completed_orders": metrics["completed_orders"],
                "average_order_value": metrics["average_order_value"],
            }
        )
    return pd.DataFrame(rows)


def _customer_value(schema: StarSchema) -> pd.DataFrame:
    if schema.fact_sales.empty:
        return pd.DataFrame(columns=KPI_COLUMNS["customer_value"])
    completed = schema.fact_sales.loc[~schema.fact_sales["is_returned"].map(bool)].copy()
    if completed.empty:
        return pd.DataFrame(columns=KPI_COLUMNS["customer_value"])
    as_of_index = max(int(value) for value in schema.dim_date["day_index"])
    date_lookup = {
        int(row.date_key): (str(row.full_date)[:10], int(row.day_index))
        for row in schema.dim_date.itertuples(index=False)
    }
    fact = completed.merge(
        schema.dim_customer.loc[:, ["customer_key", "customer_id", "full_name", "segment", "country"]],
        on="customer_key",
        how="inner",
    )
    rows: list[dict[str, object]] = []
    group_columns = ["customer_key", "customer_id", "full_name", "segment", "country"]
    for key, part in fact.groupby(group_columns, sort=False):
        customer_key, customer_id, full_name, segment, country = key
        order_dates = [date_lookup[int(value)] for value in part["date_key"]]
        first = min(order_dates, key=lambda item: item[0])
        last = max(order_dates, key=lambda item: item[0])
        net = sum_money([to_decimal(value) or ZERO for value in part["net_amount"]])
        rows.append(
            {
                "customer_key": int(customer_key),
                "customer_id": str(customer_id),
                "full_name": str(full_name),
                "segment": str(segment),
                "country": str(country),
                "completed_orders": int(part["order_id"].nunique()),
                "net_revenue": net,
                "first_order_date": first[0],
                "last_order_date": last[0],
                "recency_days": as_of_index - last[1],
            }
        )
    return pd.DataFrame(rows)


def _category_mix(schema: StarSchema) -> pd.DataFrame:
    if schema.fact_sales.empty:
        return pd.DataFrame(columns=KPI_COLUMNS["category_mix"])
    total = sum_money([to_decimal(value) or ZERO for value in schema.fact_sales["net_amount"]])
    fact = schema.fact_sales.merge(
        schema.dim_product.loc[:, ["product_key", "category"]],
        on="product_key",
        how="inner",
    )
    rows: list[dict[str, object]] = []
    for category, part in fact.groupby("category", sort=False):
        net = sum_money([to_decimal(value) or ZERO for value in part["net_amount"]])
        rows.append(
            {
                "category": str(category),
                "net_revenue": net,
                "revenue_share": ratio(net, total, RATE_PLACES),
            }
        )
    return pd.DataFrame(rows)


def _channel_comparison(schema: StarSchema) -> pd.DataFrame:
    if schema.fact_sales.empty:
        return pd.DataFrame(columns=KPI_COLUMNS["channel_comparison"])
    rows: list[dict[str, object]] = []
    for channel, part in schema.fact_sales.groupby("channel", sort=False):
        metrics = _commercial_metrics(part)
        rows.append(
            {
                "channel": str(channel),
                "net_revenue": metrics["net_revenue"],
                "margin_amount": metrics["margin_amount"],
                "completed_orders": metrics["completed_orders"],
                "average_order_value": metrics["average_order_value"],
            }
        )
    return pd.DataFrame(rows)


def _executive_summary(schema: StarSchema) -> pd.DataFrame:
    metrics = _commercial_metrics(schema.fact_sales)
    if schema.dim_date.empty:
        as_of = None
    else:
        as_of = max(str(value)[:10] for value in schema.dim_date["full_date"])
    if schema.fact_sales.empty:
        active = 0
    else:
        completed = schema.fact_sales.loc[~schema.fact_sales["is_returned"].map(bool)]
        active = 0 if completed.empty else int(completed["customer_key"].nunique())
    return pd.DataFrame(
        [
            {
                "as_of_date": as_of,
                "net_revenue": metrics["net_revenue"],
                "margin_amount": metrics["margin_amount"],
                "margin_pct": metrics["margin_pct"],
                "units_sold": metrics["units_sold"],
                "completed_orders": metrics["completed_orders"],
                "returned_orders": metrics["returned_orders"],
                "return_rate": metrics["return_rate"],
                "average_order_value": metrics["average_order_value"],
                "active_customers": active,
            }
        ]
    )


def _fact_with_calendar(schema: StarSchema) -> pd.DataFrame:
    calendar_cols = schema.dim_date.loc[:, ["date_key", "year", "month"]]
    if schema.fact_sales.empty:
        columns = list(schema.fact_sales.columns) + ["year", "month"]
        return pd.DataFrame(columns=columns)
    return schema.fact_sales.merge(calendar_cols, on="date_key", how="left")


def _commercial_metrics(fact: pd.DataFrame) -> dict[str, object]:
    if fact.empty:
        net = ZERO
        margin = ZERO
        units = 0
        completed = 0
        returned = 0
    else:
        flags = [bool(value) for value in fact["is_returned"]]
        net = sum_money([to_decimal(value) or ZERO for value in fact["net_amount"]])
        margin = sum_money([to_decimal(value) or ZERO for value in fact["margin_amount"]])
        units = sum(int(qty) for qty, returned in zip(fact["quantity"], flags) if not returned)
        completed = len({order_id for order_id, returned in zip(fact["order_id"], flags) if not returned})
        returned = len({order_id for order_id, returned in zip(fact["order_id"], flags) if returned})
    return {
        "net_revenue": net,
        "margin_amount": margin,
        "margin_pct": ratio(margin, net, RATE_PLACES),
        "units_sold": int(units),
        "completed_orders": int(completed),
        "returned_orders": int(returned),
        "return_rate": ratio(Decimal(returned), Decimal(completed + returned), RATE_PLACES),
        "average_order_value": ratio(net, Decimal(completed), MONEY_PLACES),
    }


def _competition_rank(values: list[Decimal]) -> list[int]:
    """SQL ``RANK()``: ties share the first position and the next rank skips."""
    ordered = sorted(values, reverse=True)
    first_position: dict[Decimal, int] = {}
    for position, value in enumerate(ordered, start=1):
        first_position.setdefault(value, position)
    return [first_position[value] for value in values]


def _finalize(name: str, frame: pd.DataFrame) -> pd.DataFrame:
    columns = KPI_COLUMNS[name]
    if frame.empty:
        return pd.DataFrame(columns=columns)
    records = sort_records(name, frame.to_dict(orient="records"))
    return pd.DataFrame(records, columns=columns)


def align_kpi_frame(name: str, frame: pd.DataFrame) -> pd.DataFrame:
    """Coerce a KPI frame (SQL or Pandas) onto the published column contract."""
    records = canonical_records(name, frame)
    columns = KPI_COLUMNS[name]
    if not records:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(records, columns=columns)


def canonical_records(name: str, frame: pd.DataFrame) -> list[dict[str, object]]:
    """Normalize a SQL or Pandas KPI frame to comparable Python values."""
    columns = KPI_COLUMNS[name]
    records: list[dict[str, object]] = []
    source = frame.to_dict(orient="records") if not frame.empty else []
    for record in source:
        normalized: dict[str, object] = {}
        for column in columns:
            normalized[column] = _canonical_value(column, record.get(column))
        records.append(normalized)
    return sort_records(name, records)


def _canonical_value(column: str, value: object) -> object:
    if _missing(value):
        if column in {"net_revenue", "margin_amount"}:
            return ZERO
        return None
    if column in {"net_revenue", "margin_amount", "average_order_value"}:
        parsed = to_decimal(value)
        return None if parsed is None else parsed.quantize(MONEY_PLACES)
    if column in {"margin_pct", "return_rate", "revenue_share"}:
        parsed = to_decimal(value)
        return None if parsed is None else parsed.quantize(RATE_PLACES)
    if column in {
        "year",
        "month",
        "units_sold",
        "completed_orders",
        "returned_orders",
        "revenue_rank",
        "product_key",
        "store_key",
        "customer_key",
        "recency_days",
        "active_customers",
    }:
        return int(Decimal(str(value)))
    if column in {"as_of_date", "first_order_date", "last_order_date"}:
        parsed_date = as_date(value)
        return None if parsed_date is None else parsed_date.isoformat()
    return str(value)


def _missing(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    try:
        return bool(pd.isna(value))
    except TypeError:
        return False
