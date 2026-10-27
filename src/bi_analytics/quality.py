"""Referential checks and a JSON-friendly run report."""

from __future__ import annotations

from decimal import Decimal

import pandas as pd

from bi_analytics.money import MONEY_PLACES, to_decimal
from bi_analytics.transform import StarSchema


def build_quality_report(
    raw: dict[str, pd.DataFrame],
    schema: StarSchema,
    executive: pd.DataFrame,
) -> dict[str, object]:
    fact = schema.fact_sales
    report: dict[str, object] = {
        "input_rows": {name: int(len(frame)) for name, frame in raw.items()},
        "output_rows": {name: int(len(frame)) for name, frame in schema.tables().items()},
        "rejected_rows": int(len(schema.rejects)),
        "reject_reasons": _reason_counts(schema.rejects),
        "fk_checks": _foreign_keys(schema),
        "unique_order_line": _unique(fact, "order_line_id"),
        "unique_sales_key": _unique(fact, "sales_key"),
        "as_of_date": None,
        "net_revenue": "0.00",
    }
    if not executive.empty:
        as_of = executive.iloc[0]["as_of_date"]
        report["as_of_date"] = None if as_of is None or str(as_of) == "" else str(as_of)[:10]
        net = to_decimal(executive.iloc[0]["net_revenue"]) or Decimal("0")
        report["net_revenue"] = f"{net.quantize(MONEY_PLACES):.2f}"
    return report


def _reason_counts(rejects: pd.DataFrame) -> dict[str, int]:
    if rejects.empty:
        return {}
    counts = rejects.groupby("reason").size().sort_index()
    return {str(reason): int(count) for reason, count in counts.items()}


def _foreign_keys(schema: StarSchema) -> dict[str, bool]:
    fact = schema.fact_sales
    pairs = {
        "date": (fact, "date_key", schema.dim_date, "date_key"),
        "customer": (fact, "customer_key", schema.dim_customer, "customer_key"),
        "product": (fact, "product_key", schema.dim_product, "product_key"),
        "store": (fact, "store_key", schema.dim_store, "store_key"),
        "promotion": (fact, "promotion_key", schema.dim_promotion, "promotion_key"),
    }
    return {
        name: _subset(child, child_column, parent, parent_column)
        for name, (child, child_column, parent, parent_column) in pairs.items()
    }


def _subset(child: pd.DataFrame, child_column: str, parent: pd.DataFrame, parent_column: str) -> bool:
    if child.empty:
        return True
    parent_keys = set(parent[parent_column])
    return set(child[child_column]).issubset(parent_keys)


def _unique(frame: pd.DataFrame, column: str) -> bool:
    if frame.empty:
        return True
    return not bool(frame[column].duplicated().any())
