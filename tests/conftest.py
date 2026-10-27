"""Shared raw-data builders for transform and KPI tests."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from bi_analytics.schema import RAW_COLUMNS

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def repo_root() -> Path:
    return ROOT


def _frame(name: str, rows: list[dict[str, str]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=RAW_COLUMNS[name])


def sample_raw() -> dict[str, pd.DataFrame]:
    """Two accepted orders plus one cancelled order, with round money."""
    return {
        "customers": _frame(
            "customers",
            [
                {
                    "customer_id": "C1",
                    "full_name": " ada lovelace ",
                    "email": "Ada@Example.com",
                    "segment": "consumer",
                    "city": "berlin",
                    "country": "de",
                    "signup_date": "2023-01-04",
                }
            ],
        ),
        "products": _frame(
            "products",
            [
                {
                    "sku": "P1",
                    "product_name": "Arc Pendant",
                    "category": "lighting",
                    "subcategory": "pendants",
                    "brand": "Nordlicht",
                    "unit_cost": "4.00",
                    "is_active": "true",
                },
                {
                    "sku": "P2",
                    "product_name": "Oak Throw",
                    "category": "textiles",
                    "subcategory": "throws",
                    "brand": "Sable",
                    "unit_cost": "5.00",
                    "is_active": "yes",
                },
            ],
        ),
        "stores": _frame(
            "stores",
            [
                {
                    "store_id": "s01",
                    "store_name": "Berlin Flagship",
                    "city": "berlin",
                    "country": "Germany",
                    "region": "dach",
                    "store_format": "flagship",
                }
            ],
        ),
        "promotions": _frame(
            "promotions",
            [
                {
                    "promo_code": "welcome10",
                    "promo_name": "Welcome 10 Percent",
                    "start_date": "2024-01-01",
                    "end_date": "2024-12-31",
                }
            ],
        ),
        "orders": _frame(
            "orders",
            [
                {
                    "order_id": "A",
                    "order_datetime": "2024-01-15T10:00:00",
                    "customer_id": "C1",
                    "store_id": "S01",
                    "channel": "store",
                    "status": "completed",
                    "promo_code": "",
                },
                {
                    "order_id": "B",
                    "order_datetime": "2024-02-02 12:30:00",
                    "customer_id": "C1",
                    "store_id": "S01",
                    "channel": "online",
                    "status": "returned",
                    "promo_code": "",
                },
                {
                    "order_id": "C",
                    "order_datetime": "2024-01-20T09:00:00",
                    "customer_id": "C1",
                    "store_id": "S01",
                    "channel": "Store",
                    "status": "canceled",
                    "promo_code": "",
                },
            ],
        ),
        "order_lines": _frame(
            "order_lines",
            [
                {
                    "order_line_id": "L1",
                    "order_id": "A",
                    "sku": "p1",
                    "quantity": "2",
                    "unit_price": "10.00",
                    "discount_pct": "0",
                },
                {
                    "order_line_id": "L2",
                    "order_id": "A",
                    "sku": "P2",
                    "quantity": "1",
                    "unit_price": "10.00",
                    "discount_pct": "0.10",
                },
                {
                    "order_line_id": "L3",
                    "order_id": "B",
                    "sku": "P1",
                    "quantity": "1",
                    "unit_price": "10.00",
                    "discount_pct": "0",
                },
                {
                    "order_line_id": "L4",
                    "order_id": "C",
                    "sku": "P1",
                    "quantity": "1",
                    "unit_price": "10.00",
                    "discount_pct": "0",
                },
            ],
        ),
    }
