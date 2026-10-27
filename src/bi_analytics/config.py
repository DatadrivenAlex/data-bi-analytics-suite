"""Runtime settings loaded from the environment and optional ``.env`` file."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Paths and logging for one pipeline run.

    Environment variables use the same names (``INPUT_DIR``, ``OUTPUT_DIR``,
    ``SQL_DIR``, ``DATABASE_URL``, ``LOG_LEVEL``). A local ``.env`` file is
    read when present and is never required.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    input_dir: Path = Path("data/raw")
    output_dir: Path = Path("warehouse")
    sql_dir: Path = Path("sql")
    database_url: str | None = None
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    @field_validator("log_level", mode="before")
    @classmethod
    def _upper_level(cls, value: object) -> object:
        if isinstance(value, str):
            return value.upper()
        return value

    @field_validator("database_url", mode="before")
    @classmethod
    def _blank_url_is_none(cls, value: object) -> object:
        if isinstance(value, str) and value.strip() == "":
            return None
        return value
