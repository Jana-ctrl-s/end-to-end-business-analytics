"""Central configuration and logging utilities for the analytics platform."""

from __future__ import annotations

import logging
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables or defaults.

    Attributes:
        project_root: Root directory of the repository.
        database_url: SQLAlchemy connection URL for the operational database.
        warehouse_database_url: SQLAlchemy URL for the cleaned analytical warehouse.
        mlflow_tracking_uri: Tracking URI for MLflow experiment runs.
        api_base_url: Base URL for the FastAPI inference service.
        log_level: Application logging verbosity level.
        random_state: Global deterministic seed for reproducibility.
        feature_cutoff_date: End date (inclusive) for historical ML feature window.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    project_root: Path = PROJECT_ROOT
    database_url: str = Field(
        default=f"sqlite:///{(PROJECT_ROOT / 'data' / 'raw' / 'enterprise_ops.db').as_posix()}"
    )
    warehouse_database_url: str = Field(
        default=(
            "sqlite:///"
            f"{(PROJECT_ROOT / 'data' / 'processed' / 'analytics_warehouse.db').as_posix()}"
        )
    )
    mlflow_tracking_uri: str = Field(
        default=f"sqlite:///{(PROJECT_ROOT / 'mlflow.db').as_posix()}"
    )
    api_base_url: str = "http://localhost:8000"
    log_level: str = "INFO"
    random_state: int = 42
    feature_cutoff_date: str = "2025-12-31"

    fx_api_url: str = "https://open.er-api.com/v6/latest/USD"
    worldbank_gdp_url: str = (
        "https://api.worldbank.org/v2/country/{countries}/indicator/NY.GDP.MKTP.KD.ZG"
        "?format=json&per_page=100&mrv=1"
    )
    scraper_target_url: str = "https://books.toscrape.com/"

    @property
    def data_dir(self) -> Path:
        """Return base data directory path."""
        return self.project_root / "data"

    @property
    def raw_dir(self) -> Path:
        """Return raw data directory path."""
        return self.data_dir / "raw"

    @property
    def processed_dir(self) -> Path:
        """Return processed data directory path."""
        return self.data_dir / "processed"

    @property
    def fallback_dir(self) -> Path:
        """Return offline fallback fixtures directory path."""
        return self.data_dir / "fallback"

    @property
    def cache_dir(self) -> Path:
        """Return local cache directory path."""
        return self.data_dir / "cache"

    @property
    def models_dir(self) -> Path:
        """Return serialized models directory path."""
        return self.project_root / "models"

    @property
    def reports_dir(self) -> Path:
        """Return analytical reports directory path."""
        return self.project_root / "reports"

    @property
    def figures_dir(self) -> Path:
        """Return generated plots directory path."""
        return self.reports_dir / "figures"

    @property
    def sql_dir(self) -> Path:
        """Return SQL scripts directory path."""
        return self.project_root / "sql"

    def ensure_directories(self) -> None:
        """Create required runtime directories if they do not exist."""
        for directory in (
            self.raw_dir,
            self.processed_dir,
            self.fallback_dir,
            self.cache_dir,
            self.models_dir,
            self.reports_dir,
            self.figures_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)


settings = Settings()


def get_logger(name: str) -> logging.Logger:
    """Create or retrieve a formatted module logger.

    Args:
        name: Module or component name for the logger.

    Returns:
        Configured ``logging.Logger`` instance.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    return logger
