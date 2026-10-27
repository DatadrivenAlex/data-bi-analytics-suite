"""Orchestrate extract, transform, KPI SQL, and warehouse export."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from bi_analytics.config import Settings
from bi_analytics.export import write_outputs
from bi_analytics.extract import load_raw
from bi_analytics.kpis import align_kpi_frame, canonical_records, compute_kpis
from bi_analytics.schema import KPI_VIEWS
from bi_analytics.postgres_loader import load_postgres
from bi_analytics.quality import build_quality_report
from bi_analytics.sql_runner import execute_kpi_sql
from bi_analytics.transform import StarSchema, build_star_schema

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    schema: StarSchema
    kpis: dict[str, pd.DataFrame]
    quality: dict[str, object]
    output_dir: Path


def run_pipeline(
    settings: Settings,
    *,
    execute_sql: bool = True,
    load_database: bool = False,
) -> PipelineResult:
    """Run the analytics build and write ``warehouse/`` outputs."""
    logger.info("input_dir=%s", settings.input_dir)
    raw = load_raw(settings.input_dir)
    for name, frame in raw.items():
        logger.info("loaded %s rows=%s", name, len(frame))

    schema = build_star_schema(raw)
    logger.info("fact_sales rows=%s rejects=%s", len(schema.fact_sales), len(schema.rejects))

    reference = {name: align_kpi_frame(name, frame) for name, frame in compute_kpis(schema).items()}
    if execute_sql:
        sql_frames = execute_kpi_sql(schema, settings.sql_dir)
        kpis = {name: align_kpi_frame(name, frame) for name, frame in sql_frames.items()}
        drifted = [
            name
            for name in KPI_VIEWS
            if canonical_records(name, kpis[name]) != canonical_records(name, reference[name])
        ]
        if drifted:
            raise RuntimeError(
                "SQL KPI views do not match the Pandas reference: " + ", ".join(drifted)
            )
    else:
        kpis = reference

    quality = build_quality_report(raw, schema, kpis["executive_summary"])
    if not all(quality["fk_checks"].values()):  # type: ignore[union-attr]
        logger.error("referential integrity failed: %s", quality["fk_checks"])
        raise RuntimeError("Star schema failed foreign-key checks")

    write_outputs(settings.output_dir, schema, kpis, quality)
    logger.info("wrote outputs to %s", settings.output_dir)
    logger.info(
        "as_of=%s net_revenue=%s",
        quality["as_of_date"],
        quality["net_revenue"],
    )

    if load_database:
        if not settings.database_url:
            raise ValueError("DATABASE_URL is required when --postgres is set")
        logger.info("loading PostgreSQL")
        load_postgres(settings.database_url, schema, settings.sql_dir)
        logger.info("PostgreSQL load finished")

    return PipelineResult(
        schema=schema,
        kpis=kpis,
        quality=quality,
        output_dir=settings.output_dir,
    )
