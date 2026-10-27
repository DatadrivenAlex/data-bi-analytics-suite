"""Write the warehouse CSV extracts and the quality report."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pandas as pd

from bi_analytics.money import MONEY_PLACES, RATE_PLACES, to_decimal
from bi_analytics.schema import BOOL_COLUMNS, DATE_COLUMNS, MONEY_COLUMNS, RATE_COLUMNS
from bi_analytics.transform import StarSchema


def write_outputs(
    output_dir: Path,
    schema: StarSchema,
    kpis: dict[str, pd.DataFrame],
    quality: dict[str, object],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, frame in schema.tables().items():
        _write_csv(_present(frame), output_dir / f"{name}.csv")
    _write_csv(_present(schema.rejects), output_dir / "rejects.csv")
    kpi_dir = output_dir / "kpis"
    kpi_dir.mkdir(parents=True, exist_ok=True)
    for name, frame in kpis.items():
        _write_csv(_present(frame), kpi_dir / f"{name}.csv")
    (output_dir / "quality_report.json").write_text(
        json.dumps(quality, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _present(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    presented = frame.copy()
    for column in presented.columns:
        if column in BOOL_COLUMNS:
            presented[column] = [_bool_text(value) for value in presented[column]]
        elif column in MONEY_COLUMNS:
            presented[column] = [_money_text(value) for value in presented[column]]
        elif column in RATE_COLUMNS:
            presented[column] = [_rate_text(value) for value in presented[column]]
        elif column in DATE_COLUMNS:
            presented[column] = [_date_text(value) for value in presented[column]]
        else:
            presented[column] = [_plain(value) for value in presented[column]]
    return presented


def _write_csv(frame: pd.DataFrame, path: Path) -> None:
    frame.to_csv(path, index=False)


def _missing(value: object) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except TypeError:
        return False


def _plain(value: object) -> object:
    if _missing(value):
        return ""
    return value


def _bool_text(value: object) -> str:
    if _missing(value) or value == "":
        return ""
    return str(bool(value)).lower()


def _money_text(value: object) -> str:
    if _missing(value) or value == "":
        return ""
    parsed = to_decimal(value)
    if parsed is None:
        return ""
    return f"{parsed.quantize(MONEY_PLACES):.2f}"


def _rate_text(value: object) -> str:
    if _missing(value) or value == "":
        return ""
    parsed = to_decimal(value)
    if parsed is None:
        return ""
    return f"{parsed.quantize(RATE_PLACES):.4f}"


def _date_text(value: object) -> str:
    if _missing(value) or value == "":
        return ""
    return str(value)[:10]
