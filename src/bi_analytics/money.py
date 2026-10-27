"""Exact money helpers.

Amounts are quantized to cents with half-up rounding so Pandas KPIs and
PostgreSQL ``ROUND(numeric, scale)`` stay aligned.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

MONEY_PLACES = Decimal("0.01")
RATE_PLACES = Decimal("0.0001")
ZERO = Decimal("0.00")


def to_decimal(value: object) -> Decimal | None:
    """Parse a scalar into Decimal. Blank and unparseable values return None."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    text = str(value).strip()
    if text == "" or text.lower() in {"nan", "none", "null", "<na>"}:
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def quantize(value: Decimal, places: Decimal) -> Decimal:
    return value.quantize(places, rounding=ROUND_HALF_UP)


def money(value: Decimal) -> Decimal:
    return quantize(value, MONEY_PLACES)


def ratio(numerator: Decimal, denominator: Decimal, places: Decimal) -> Decimal | None:
    """Divide and quantize. A zero denominator matches SQL NULLIF."""
    if denominator == 0:
        return None
    return quantize(numerator / denominator, places)


def sum_money(values: list[Decimal]) -> Decimal:
    total = Decimal("0")
    for value in values:
        total += value
    return money(total)
