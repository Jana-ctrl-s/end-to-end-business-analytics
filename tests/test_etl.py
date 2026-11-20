"""Tests for automated ETL cleaning, imputation, outlier clamping, and validation."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.config import Settings, settings
from src.etl.pipeline import ETLPipeline
from src.etl.run_pipeline import main as run_etl_cli
from src.etl.schemas import DataQualityReport


def test_clean_customers_and_interactions() -> None:
    """clean_customers and clean_interactions deduplicate, standardize, and impute cleanly."""
    raw_cust = pd.DataFrame(
        [
            {
                "customer_id": 1,
                "customer_code": "CUST-00001",
                "company_name": "Acme Corp",
                "segment": " enterprise ",
                "contract_type": " Annual ",
                "acquisition_channel": None,
                "region_id": 1,
                "signup_date": "2024-03-01",
                "account_tenure_days": 670,
            },
            {
                "customer_id": 2,
                "customer_code": "CUST-00002",
                "company_name": "Beta LLC",
                "segment": "SMB",
                "contract_type": "Monthly",
                "acquisition_channel": "Direct Sales",
                "region_id": 2,
                "signup_date": "2024-06-15",
                "account_tenure_days": 564,
            },
        ]
    )
    cust_clean, cust_m = ETLPipeline.clean_customers(raw_cust)
    assert cust_clean.loc[0, "segment"] == "Enterprise"
    assert cust_clean.loc[0, "acquisition_channel"] == "Direct Sales"
    assert cust_m["missing_imputed"] == 1

    raw_int = pd.DataFrame(
        [
            {
                "interaction_id": 1,
                "ticket_code": "TKT-000001",
                "customer_id": 1,
                "interaction_date": "2025-07-01",
                "channel": " Email ",
                "issue_category": "Billing",
                "resolution_hours": 750.0,
                "csat_score": np.nan,
                "nps_score": 8,
                "escalated": 0,
            },
            {
                "interaction_id": 2,
                "ticket_code": "TKT-000001",
                "customer_id": 1,
                "interaction_date": "2025-07-01",
                "channel": "Email",
                "issue_category": "Billing",
                "resolution_hours": 8.0,
                "csat_score": 4.5,
                "nps_score": 8,
                "escalated": 0,
            },
            {
                "interaction_id": 3,
                "ticket_code": "TKT-000002",
                "customer_id": 2,
                "interaction_date": "2025-07-02",
                "channel": "Email",
                "issue_category": "Billing",
                "resolution_hours": 8.0,
                "csat_score": 4.5,
                "nps_score": 8,
                "escalated": 0,
            },
        ]
    )
    int_clean, int_m = ETLPipeline.clean_interactions(raw_int)
    assert len(int_clean) == 2
    assert int_m["duplicates_removed"] == 1
    assert int_m["outliers_clamped"] == 1
    assert int_clean.loc[0, "csat_score"] == 4.5


def test_clean_orders_deduplicates_and_clamps_outliers() -> None:
    """clean_orders removes duplicate order codes, standardizes casing, and clamps extremes."""
    raw = pd.DataFrame(
        [
            {
                "order_id": 1,
                "order_code": "ORD-000001",
                "customer_id": 1,
                "product_id": 1,
                "region_id": 1,
                "order_date": "2025-05-10",
                "quantity": 2,
                "unit_price_usd": 400.0,
                "discount_pct": 0.10,
                "shipping_cost_usd": -45.0,
                "gross_revenue_usd": 720.0,
                "net_profit_usd": 310.0,
                "delivery_days": 999.0,
                "payment_method": "  credit_card ",
                "order_status": " completed ",
            },
            {
                "order_id": 2,
                "order_code": "ORD-000001",
                "customer_id": 1,
                "product_id": 1,
                "region_id": 1,
                "order_date": "2025-05-10",
                "quantity": 2,
                "unit_price_usd": 400.0,
                "discount_pct": 0.10,
                "shipping_cost_usd": 20.0,
                "gross_revenue_usd": 720.0,
                "net_profit_usd": 310.0,
                "delivery_days": 4.0,
                "payment_method": "Credit Card",
                "order_status": "Completed",
            },
            {
                "order_id": 3,
                "order_code": "ORD-000002",
                "customer_id": 2,
                "product_id": 2,
                "region_id": 1,
                "order_date": "2025-05-12",
                "quantity": 1,
                "unit_price_usd": 300.0,
                "discount_pct": np.nan,
                "shipping_cost_usd": 15.0,
                "gross_revenue_usd": 300.0,
                "net_profit_usd": 120.0,
                "delivery_days": 4.0,
                "payment_method": "Wire Transfer",
                "order_status": "Completed",
            },
        ]
    )
    cleaned, metrics = ETLPipeline.clean_orders(raw)
    assert len(cleaned) == 2
    assert metrics["duplicates_removed"] == 1
    assert metrics["outliers_clamped"] >= 2
    assert cleaned.loc[0, "payment_method"] == "Credit Card"
    assert cleaned.loc[0, "order_status"] == "Completed"
    assert cleaned.loc[0, "shipping_cost_usd"] >= 8.0
    assert cleaned["delivery_days"].isna().sum() == 0
    assert cleaned["discount_pct"].isna().sum() == 0


def test_full_etl_execution_and_sla(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, processed_dir: Path
) -> None:
    """Execute ETL pipeline end-to-end in isolated output dir and verify SLA."""
    wh_url = f"sqlite:///{(tmp_path / 'wh.db').as_posix()}"
    monkeypatch.setattr(Settings, "processed_dir", property(lambda self: tmp_path))
    monkeypatch.setattr(settings, "warehouse_database_url", wh_url)
    run_etl_cli(force_reseed=False)

    dq_data = json.loads((tmp_path / "data_quality_report.json").read_text(encoding="utf-8"))
    report = DataQualityReport(**dq_data)
    c360_tmp = pd.read_csv(tmp_path / "customer_360.csv")

    assert report.post_cleaning_error_rate_pct < 0.1
    assert report.duplicate_orders_removed > 0
    assert report.missing_values_imputed > 0
    assert report.outliers_clamped > 0
    assert report.pipeline_duration_seconds < 900.0
    assert len(c360_tmp) == 4000
    assert int(c360_tmp.isna().sum().sum()) == 0

    # Also verify production enriched Customer 360 has PCA & cluster columns
    c360_prod = pd.read_csv(processed_dir / "customer_360.csv")
    assert set(["cluster_id", "cluster_label", "pca_1", "pca_2"]).issubset(c360_prod.columns)
