"""Business rules for the star-schema transform."""

from __future__ import annotations

import pandas as pd

from bi_analytics.transform import build_star_schema
from tests.conftest import sample_raw


def test_customer_and_store_are_conformed() -> None:
    schema = build_star_schema(sample_raw())
    customer = schema.dim_customer.iloc[0]
    assert customer["full_name"] == "Ada Lovelace"
    assert customer["email"] == "ada@example.com"
    assert customer["segment"] == "Consumer"
    assert customer["country"] == "Germany"
    assert customer["city"] == "Berlin"
    store = schema.dim_store.iloc[0]
    assert store["store_id"] == "S01"
    assert store["region"] == "DACH"
    assert store["store_format"] == "Flagship"
    assert schema.dim_promotion.iloc[0]["promo_code"] == "NONE"
    assert int(schema.dim_promotion.iloc[0]["promotion_key"]) == 1


def test_amounts_returns_and_cancellations() -> None:
    schema = build_star_schema(sample_raw())
    fact = schema.fact_sales.set_index("order_line_id")
    assert set(fact.index) == {"L1", "L2", "L3"}
    assert set(schema.rejects.loc[schema.rejects["order_id"] == "C", "reason"]) == {"cancelled_order"}

    completed = fact.loc["L1"]
    assert completed["gross_amount"] == "20.00"
    assert completed["discount_amount"] == "0.00"
    assert completed["net_amount"] == "20.00"
    assert completed["cost_amount"] == "8.00"
    assert completed["margin_amount"] == "12.00"
    assert completed["return_amount"] == "0.00"
    assert bool(completed["is_returned"]) is False

    discounted = fact.loc["L2"]
    assert discounted["gross_amount"] == "10.00"
    assert discounted["discount_amount"] == "1.00"
    assert discounted["net_amount"] == "9.00"
    assert discounted["cost_amount"] == "5.00"
    assert discounted["margin_amount"] == "4.00"

    returned = fact.loc["L3"]
    assert returned["gross_amount"] == "10.00"
    assert returned["net_amount"] == "0.00"
    assert returned["cost_amount"] == "0.00"
    assert returned["margin_amount"] == "0.00"
    assert returned["return_amount"] == "10.00"
    assert bool(returned["is_returned"]) is True


def test_line_quarantine_keeps_the_valid_sibling() -> None:
    raw = sample_raw()
    extra = {
        "order_line_id": "BAD",
        "order_id": "A",
        "sku": "missing",
        "quantity": "-1",
        "unit_price": "10.00",
        "discount_pct": "0",
    }
    raw["order_lines"] = _append(raw["order_lines"], extra)
    schema = build_star_schema(raw)
    assert "L1" in set(schema.fact_sales["order_line_id"])
    assert "BAD" not in set(schema.fact_sales["order_line_id"])
    reasons = set(schema.rejects["reason"])
    assert "unknown_sku" in reasons


def test_duplicate_line_and_unknown_header_rules() -> None:
    raw = sample_raw()
    raw["orders"] = _append(
        raw["orders"],
        {
            "order_id": "D",
            "order_datetime": "2024-03-01T00:00:00",
            "customer_id": "missing",
            "store_id": "S01",
            "channel": "Web",
            "status": "completed",
            "promo_code": "NOPE",
        },
    )
    raw["order_lines"] = _append(
        raw["order_lines"],
        {
            "order_line_id": "L1",
            "order_id": "A",
            "sku": "P1",
            "quantity": "1",
            "unit_price": "10.00",
            "discount_pct": "0",
        },
    )
    raw["order_lines"] = _append(
        raw["order_lines"],
        {
            "order_line_id": "LD",
            "order_id": "D",
            "sku": "P1",
            "quantity": "1",
            "unit_price": "10.00",
            "discount_pct": "2",
        },
    )
    schema = build_star_schema(raw)
    reasons = set(schema.rejects["reason"])
    assert "duplicate_line" in reasons
    assert "unknown_customer" in reasons
    assert schema.fact_sales["order_line_id"].tolist().count("L1") == 1
    assert set(schema.fact_sales["customer_key"]).issubset(set(schema.dim_customer["customer_key"]))


def test_duplicate_customer_keeps_the_first_row() -> None:
    raw = sample_raw()
    raw["customers"] = _append(
        raw["customers"],
        {
            "customer_id": "C1",
            "full_name": "Other Person",
            "email": "other@example.com",
            "segment": "Trade",
            "city": "Hamburg",
            "country": "Germany",
            "signup_date": "2024-01-01",
        },
    )
    schema = build_star_schema(raw)
    assert list(schema.dim_customer["email"]) == ["ada@example.com"]
    assert "duplicate_customer" in set(schema.rejects["reason"])


def test_calendar_covers_every_day_in_the_order_span() -> None:
    schema = build_star_schema(sample_raw())
    assert schema.dim_date["full_date"].iloc[0] == "2024-01-15"
    assert schema.dim_date["full_date"].iloc[-1] == "2024-02-02"
    assert len(schema.dim_date) == 19
    assert int(schema.dim_date.iloc[-1]["day_index"]) - int(schema.dim_date.iloc[0]["day_index"]) == 18


def _append(frame: pd.DataFrame, row: dict[str, str]) -> pd.DataFrame:
    return pd.concat([frame, pd.DataFrame([row])], ignore_index=True)
