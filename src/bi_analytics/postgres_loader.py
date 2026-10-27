"""Optional load of the star schema and KPI views into PostgreSQL."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd

from bi_analytics.dates import as_date
from bi_analytics.money import to_decimal
from bi_analytics.schema import BOOL_COLUMNS, DATE_COLUMNS, KPI_VIEWS, LOAD_ORDER, MONEY_COLUMNS, RATE_COLUMNS
from bi_analytics.transform import StarSchema

_RATE_COLUMNS = RATE_COLUMNS
_MONEY_COLUMNS = MONEY_COLUMNS


def split_sql(script: str) -> list[str]:
    """Split a local SQL file into statements. Comments are line comments only."""
    statements: list[str] = []
    buffer: list[str] = []
    for line in script.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        buffer.append(line)
        if stripped.endswith(";"):
            statement = "\n".join(buffer).strip()
            if statement:
                statements.append(statement)
            buffer = []
    tail = "\n".join(buffer).strip()
    if tail:
        statements.append(tail)
    return statements


def load_postgres(database_url: str, schema: StarSchema, sql_dir: Path) -> None:
    """Replace warehouse tables and recreate KPI views.

    Requires the optional ``postgres`` extra (SQLAlchemy and psycopg).
    """
    if not database_url.startswith("postgresql"):
        raise ValueError("DATABASE_URL must start with postgresql")
    try:
        from sqlalchemy import create_engine, text
    except ImportError as exc:
        raise RuntimeError(
            "PostgreSQL loading needs the postgres extra: "
            "pip install 'data-bi-analytics-suite[postgres]'"
        ) from exc

    engine = create_engine(database_url)
    view_names = [f"vw_kpi_{name}" for name in KPI_VIEWS]
    ddl_path = sql_dir / "ddl" / "01_star_schema.sql"
    if not ddl_path.is_file():
        raise FileNotFoundError(f"Missing DDL script: {ddl_path}")

    with engine.begin() as connection:
        for view in view_names:
            connection.execute(text(f"DROP VIEW IF EXISTS {view} CASCADE"))
        for table in reversed(LOAD_ORDER):
            connection.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
        for statement in split_sql(ddl_path.read_text(encoding="utf-8")):
            connection.execute(text(statement))
        for name in LOAD_ORDER:
            prepared = _prepare_frame(schema.tables()[name])
            if prepared.empty:
                continue
            prepared.to_sql(name, connection, if_exists="append", index=False, method="multi", chunksize=200)
        for name in KPI_VIEWS:
            script = (sql_dir / "kpis" / f"{name}.sql").read_text(encoding="utf-8")
            for statement in split_sql(script):
                connection.execute(text(statement))


def _prepare_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    prepared = frame.copy()
    for column in prepared.columns:
        if column in DATE_COLUMNS:
            prepared[column] = [_date_value(value) for value in prepared[column]]
        elif column in BOOL_COLUMNS:
            prepared[column] = [bool(value) for value in prepared[column]]
        elif column in _MONEY_COLUMNS or column in _RATE_COLUMNS:
            prepared[column] = [_decimal_value(value) for value in prepared[column]]
        else:
            prepared[column] = [_plain(value) for value in prepared[column]]
    return prepared


def _date_value(value: object) -> date | None:
    return as_date(value)


def _decimal_value(value: object) -> Decimal | None:
    if value is None or value == "":
        return None
    return to_decimal(value)


def _plain(value: object) -> object:
    try:
        if value is None or bool(pd.isna(value)):
            return None
    except TypeError:
        if value is None:
            return None
    return value
