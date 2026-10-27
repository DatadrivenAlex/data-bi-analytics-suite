"""CLI and warehouse export."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from bi_analytics.cli import main
from bi_analytics.config import Settings
from tests.conftest import ROOT


def test_run_writes_the_warehouse(tmp_path: Path) -> None:
    code = main(
        [
            "run",
            "--input",
            str(ROOT / "data" / "raw"),
            "--output",
            str(tmp_path),
            "--sql-dir",
            str(ROOT / "sql"),
        ]
    )
    assert code == 0
    fact = tmp_path / "fact_sales.csv"
    assert fact.is_file()
    executive = (tmp_path / "kpis" / "executive_summary.csv").read_text(encoding="utf-8")
    assert "net_revenue" in executive
    quality = json.loads((tmp_path / "quality_report.json").read_text(encoding="utf-8"))
    assert quality["fk_checks"]["customer"] is True
    assert quality["fk_checks"]["product"] is True
    assert quality["rejected_rows"] > 0
    assert quality["net_revenue"] != ""


def test_missing_input_returns_2(tmp_path: Path) -> None:
    code = main(
        [
            "run",
            "--input",
            str(tmp_path / "missing"),
            "--output",
            str(tmp_path / "out"),
            "--sql-dir",
            str(ROOT / "sql"),
        ]
    )
    assert code == 2


def test_module_entrypoint(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "bi_analytics",
            "run",
            "--input",
            str(ROOT / "data" / "raw"),
            "--output",
            str(tmp_path),
            "--sql-dir",
            str(ROOT / "sql"),
            "--log-level",
            "ERROR",
        ],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert "net_revenue:" in completed.stdout
    assert (tmp_path / "dim_product.csv").is_file()


def test_postgres_flag_requires_a_url(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    code = main(
        [
            "run",
            "--input",
            str(ROOT / "data" / "raw"),
            "--output",
            str(tmp_path),
            "--sql-dir",
            str(ROOT / "sql"),
            "--postgres",
        ]
    )
    assert code == 2


def test_settings_reject_unknown_log_level() -> None:
    with pytest.raises(ValidationError):
        Settings(log_level="verbose", _env_file=None)  # type: ignore[arg-type]
