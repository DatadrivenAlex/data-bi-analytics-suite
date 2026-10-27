"""Command line entry point for ``bi-analytics``."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from pydantic import ValidationError

from bi_analytics import __version__
from bi_analytics.config import Settings
from bi_analytics.logging_config import configure_logging
from bi_analytics.pipeline import PipelineResult, run_pipeline

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="bi-analytics",
        description="Build a retail star schema and KPI extracts from sample sales data.",
    )
    parser.add_argument("--version", action="version", version=f"bi-analytics {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Transform raw CSVs, build the star schema, and write KPIs")
    run_parser.add_argument("--input", type=Path, help="Directory of raw CSV extracts (default: data/raw)")
    run_parser.add_argument("--output", type=Path, help="Warehouse output directory (default: warehouse)")
    run_parser.add_argument("--sql-dir", type=Path, help="Directory containing ddl/ and kpis/ (default: sql)")
    run_parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    run_parser.add_argument(
        "--skip-sql",
        action="store_true",
        help="Write Pandas KPI extracts instead of executing the SQL views",
    )
    run_parser.add_argument(
        "--postgres",
        action="store_true",
        help="Also load tables and views into DATABASE_URL (optional PostgreSQL extra)",
    )

    args = parser.parse_args(argv)
    try:
        settings = Settings(_env_file=".env" if Path(".env").is_file() else None)
    except ValidationError as exc:
        print(exc, file=sys.stderr)
        return 2

    updates: dict[str, object] = {}
    if args.input is not None:
        updates["input_dir"] = args.input
    elif not settings.input_dir.exists():
        fallback = _package_root() / "data" / "raw"
        if fallback.exists():
            updates["input_dir"] = fallback
    if args.output is not None:
        updates["output_dir"] = args.output
    if args.sql_dir is not None:
        updates["sql_dir"] = args.sql_dir
    elif not settings.sql_dir.exists():
        fallback_sql = _package_root() / "sql"
        if fallback_sql.exists():
            updates["sql_dir"] = fallback_sql
    if args.log_level is not None:
        updates["log_level"] = args.log_level
    if updates:
        settings = settings.model_copy(update=updates)

    configure_logging(settings.log_level)
    try:
        result = run_pipeline(
            settings,
            execute_sql=not args.skip_sql,
            load_database=args.postgres,
        )
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        logger.error("%s", exc)
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except Exception:
        logger.exception("pipeline failed")
        print("error: pipeline failed", file=sys.stderr)
        return 1

    _print_summary(result)
    return 0


def _print_summary(result: PipelineResult) -> None:
    executive = result.kpis["executive_summary"].iloc[0]
    quality = result.quality
    print("bi-analytics run")
    print(f"fact_sales: {quality['output_rows']['fact_sales']}")  # type: ignore[index]
    print(f"rejected_rows: {quality['rejected_rows']}")
    print(f"as_of_date: {quality['as_of_date']}")
    print(f"net_revenue: {executive['net_revenue']}")
    print(f"margin_amount: {executive['margin_amount']}")
    print(f"margin_pct: {executive['margin_pct']}")
    print(f"completed_orders: {executive['completed_orders']}")
    print(f"return_rate: {executive['return_rate']}")
    print(f"output: {result.output_dir}")


def _package_root() -> Path:
    return Path(__file__).resolve().parents[2]
