"""Date parsing that survives Pandas timestamp inference."""

from __future__ import annotations

from datetime import date, datetime

import pandas as pd

EPOCH = date(2000, 1, 1)


def as_date(value: object) -> date | None:
    """Return a ``datetime.date`` or None for blank values."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        text = value.strip()
        if text == "":
            return None
        return date.fromisoformat(text[:10])
    if hasattr(value, "to_pydatetime"):
        converted = value.to_pydatetime()
        return converted.date()
    try:
        missing = bool(pd.isna(value))
    except TypeError:
        missing = False
    if missing:
        return None
    raise TypeError(f"Cannot parse date from {value!r}")


def iso_or_none(value: object) -> str | None:
    parsed = as_date(value)
    if parsed is None:
        return None
    return parsed.isoformat()


def day_index(value: date) -> int:
    """Days since 2000-01-01. Used so KPI SQL never subtracts DATE values."""
    return (value - EPOCH).days
