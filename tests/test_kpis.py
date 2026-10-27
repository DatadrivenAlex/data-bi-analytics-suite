"""KPI parity between the Pandas reference and the SQL views."""

from __future__ import annotations

from decimal import Decimal

from bi_analytics.extract import load_raw
from bi_analytics.kpis import canonical_records, compute_kpis
from bi_analytics.sql_runner import execute_kpi_sql
from bi_analytics.transform import build_star_schema
from tests.conftest import ROOT, sample_raw


def test_hand_calculated_kpis() -> None:
    schema = build_star_schema(sample_raw())
    kpis = compute_kpis(schema)
    monthly = {int(row.month): row for row in kpis["monthly_sales"].itertuples(index=False)}

    january = monthly[1]
    assert january.net_revenue == Decimal("29.00")
    assert january.margin_amount == Decimal("16.00")
    assert january.margin_pct == Decimal("0.5517")
    assert january.units_sold == 3
    assert january.completed_orders == 1
    assert january.returned_orders == 0
    assert january.return_rate == Decimal("0.0000")
    assert january.average_order_value == Decimal("29.00")

    february = monthly[2]
    assert february.net_revenue == Decimal("0.00")
    assert february.margin_pct is None
    assert february.units_sold == 0
    assert february.completed_orders == 0
    assert february.returned_orders == 1
    assert february.return_rate == Decimal("1.0000")
    assert february.average_order_value is None

    executive = kpis["executive_summary"].iloc[0]
    assert executive["as_of_date"] == "2024-02-02"
    assert executive["net_revenue"] == Decimal("29.00")
    assert executive["margin_amount"] == Decimal("16.00")
    assert executive["completed_orders"] == 1
    assert executive["returned_orders"] == 1
    assert executive["return_rate"] == Decimal("0.5000")
    assert executive["average_order_value"] == Decimal("29.00")
    assert executive["active_customers"] == 1
    assert executive["units_sold"] == 3

    customer = kpis["customer_value"].iloc[0]
    assert customer["completed_orders"] == 1
    assert customer["net_revenue"] == Decimal("29.00")
    assert customer["first_order_date"] == "2024-01-15"
    assert customer["last_order_date"] == "2024-01-15"
    assert customer["recency_days"] == 18


def test_sql_matches_pandas_on_the_hand_scenario() -> None:
    schema = build_star_schema(sample_raw())
    _assert_parity(schema)


def test_sql_matches_pandas_on_the_sample_extract() -> None:
    raw = load_raw(ROOT / "data" / "raw")
    schema = build_star_schema(raw)
    reasons = set(schema.rejects["reason"])
    for expected in {
        "duplicate_customer",
        "cancelled_order",
        "unknown_customer",
        "unknown_store",
        "unknown_promotion",
        "invalid_channel",
        "missing_order",
        "unknown_sku",
        "invalid_quantity",
        "invalid_discount",
        "invalid_price",
        "duplicate_line",
    }:
        assert expected in reasons
    assert "BAD-CANCEL" not in set(schema.fact_sales["order_id"])
    assert schema.fact_sales["order_line_id"].is_unique
    customer = schema.dim_customer.set_index("customer_id").loc["C001"]
    assert customer["full_name"] == "Mia Schmidt"
    assert customer["email"] == "mia.schmidt@example.com"
    assert customer["country"] == "Germany"
    assert list(schema.dim_customer["customer_id"]).count("C001") == 1
    _assert_parity(schema)


def test_sql_runs_when_every_order_is_rejected() -> None:
    raw = sample_raw()
    raw["orders"]["status"] = "cancelled"
    schema = build_star_schema(raw)
    assert schema.fact_sales.empty
    _assert_parity(schema)


def _assert_parity(schema) -> None:
    reference = compute_kpis(schema)
    sql = execute_kpi_sql(schema, ROOT / "sql")
    for name in reference:
        assert canonical_records(name, sql[name]) == canonical_records(name, reference[name]), name
