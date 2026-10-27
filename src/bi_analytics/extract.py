"""Load raw CSV extracts."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from bi_analytics.schema import RAW_COLUMNS, RAW_FILES


def load_raw(input_dir: Path) -> dict[str, pd.DataFrame]:
    """Read every required source file as text.

    Identifiers stay strings (no silent integer conversion). Empty cells stay
    empty strings so business rules, not the CSV parser, decide what is missing.
    """
    if not input_dir.is_dir():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")

    frames: dict[str, pd.DataFrame] = {}
    for name, filename in RAW_FILES.items():
        path = input_dir / filename
        if not path.is_file():
            raise FileNotFoundError(f"Missing source file: {path}")
        frame = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
        missing = [column for column in RAW_COLUMNS[name] if column not in frame.columns]
        if missing:
            raise ValueError(f"{filename} is missing columns: {', '.join(missing)}")
        frames[name] = frame.loc[:, RAW_COLUMNS[name]].copy()
    return frames
