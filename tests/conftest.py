"""Shared pytest fixtures for ingestion, ETL, ML, and API test suites."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from src.config import settings
from src.etl.pipeline import ETLPipeline
from src.ingestion.seed_database import seed_enterprise_database
from src.ml.evaluate import generate_all_evaluations
from src.ml.train import train_all_models


@pytest.fixture(scope="session", autouse=True)
def ensure_artifacts() -> None:
    """Ensure seeded database, processed CSVs, and trained models exist once per session."""
    db_path = settings.raw_dir / "enterprise_ops.db"
    if not db_path.exists():
        seed_enterprise_database(force=True)
    if not (settings.processed_dir / "customer_360.csv").exists():
        ETLPipeline().run()
    if not (settings.models_dir / "churn_champion.joblib").exists():
        train_all_models()
    if not (settings.figures_dir / "ml_confusion_matrix.png").exists():
        generate_all_evaluations()


@pytest.fixture()
def sample_customer_payload() -> dict[str, Any]:
    """Return a valid customer feature payload for prediction tests."""
    return {
        "account_tenure_days": 450,
        "recency_days": 20.0,
        "order_frequency": 10,
        "hist_total_revenue_usd": 16200.0,
        "hist_total_profit_usd": 7100.0,
        "avg_order_value_usd": 1620.0,
        "recent_90d_revenue_usd": 4200.0,
        "spend_momentum_ratio": 1.01,
        "avg_discount_pct": 0.07,
        "avg_delivery_days": 3.2,
        "return_rate": 0.01,
        "support_tickets_count": 2,
        "avg_resolution_hours": 8.5,
        "avg_csat": 4.55,
        "avg_nps": 8.8,
        "escalation_rate": 0.0,
        "gdp_growth_pct": 2.8,
        "fx_rate_to_usd": 1.0,
        "competitor_price_index": 0.98,
        "segment": "Enterprise",
        "contract_type": "2-Year",
        "acquisition_channel": "Direct Sales",
        "macro_region": "North America",
        "primary_category": "Cloud Software",
    }


@pytest.fixture()
def processed_dir() -> Path:
    """Return path to processed datasets directory."""
    return settings.processed_dir


@pytest.fixture()
def c360_df(processed_dir: Path) -> pd.DataFrame:
    """Load processed Customer 360 DataFrame."""
    return pd.read_csv(processed_dir / "customer_360.csv")
