"""The SQL files stay aligned with the Pandas model and parse as PostgreSQL."""

from __future__ import annotations

import re

import sqlglot

from bi_analytics.postgres_loader import split_sql
from bi_analytics.schema import KPI_VIEWS, TABLE_COLUMNS
from tests.conftest import ROOT

SQL_DIR = ROOT / "sql"


def test_ddl_lists_every_model_column() -> None:
    script = (SQL_DIR / "ddl" / "01_star_schema.sql").read_text(encoding="utf-8")
    for table, columns in TABLE_COLUMNS.items():
        match = re.search(rf"CREATE TABLE {table} \((.*?)\);", script, flags=re.S)
        assert match is not None, table
        body = match.group(1)
        for column in columns:
            assert re.search(rf"\b{column}\b", body), f"{table}.{column}"
    statements = split_sql(script)
    assert len(statements) >= 6
    assert all(statement.endswith(";") for statement in statements)


def test_kpi_scripts_are_postgres_views() -> None:
    for name in KPI_VIEWS:
        script = (SQL_DIR / "kpis" / f"{name}.sql").read_text(encoding="utf-8")
        assert f"CREATE OR REPLACE VIEW vw_kpi_{name}" in script
        parsed = sqlglot.parse(script, read="postgres")
        assert parsed
        assert any(expression is not None for expression in parsed)
