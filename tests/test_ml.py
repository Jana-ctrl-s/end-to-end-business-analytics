"""Tests for ML features, model KPIs, evaluations, and inference service."""

from __future__ import annotations

import json
from typing import Any

import numpy as np
import pandas as pd

from src.config import settings
from src.ml.evaluate import generate_all_evaluations
from src.ml.features import (
    CLASSIFICATION_CAT_FEATURES,
    CLASSIFICATION_NUM_FEATURES,
    build_clustering_scaler,
    build_tabular_preprocessor,
    derive_persona_map,
)
from src.ml.predict import AnalyticsPredictor


def test_features_and_persona_mapping(c360_df: pd.DataFrame) -> None:
    """Feature transformers and persona map helpers work cleanly on Customer 360."""
    pre = build_tabular_preprocessor(CLASSIFICATION_NUM_FEATURES, CLASSIFICATION_CAT_FEATURES)
    transformed = pre.fit_transform(
        c360_df[CLASSIFICATION_NUM_FEATURES + CLASSIFICATION_CAT_FEATURES].head(40)
    )
    assert transformed.shape[0] == 40

    scaler = build_clustering_scaler()
    assert scaler is not None

    labels = np.array([i % 4 for i in range(40)])
    pmap = derive_persona_map(c360_df.head(40), labels)
    assert set(pmap.values()) == {
        "At-Risk High-Friction",
        "Enterprise Champions",
        "Dormant Price-Sensitive",
        "Loyal Growth Mid-Market",
    }


def test_model_registry_meets_all_kpis() -> None:
    """Ensure registered champions satisfy F1 >= 0.82, R2 >= 0.80, and Silhouette >= 0.50."""
    registry = json.loads((settings.models_dir / "model_registry.json").read_text(encoding="utf-8"))

    cls_f1 = registry["classification"]["champion_metrics"]["test_f1"]
    rev_r2 = registry["regression"]["champion_metrics"]["test_r2"]
    rev_rmse = registry["regression"]["champion_metrics"]["test_rmse"]
    base_rmse = registry["regression"]["baseline_metrics"]["test_rmse"]
    clust_sil = registry["clustering"]["champion_metrics"]["silhouette_score"]

    assert cls_f1 >= 0.82
    assert rev_r2 >= 0.80
    assert rev_rmse < base_rmse
    assert clust_sil >= 0.50


def test_predictor_single_and_batch_inference(sample_customer_payload: dict[str, Any]) -> None:
    """AnalyticsPredictor produces valid churn, revenue, segment, and batch predictions."""
    predictor = AnalyticsPredictor()

    c360_res = predictor.predict_customer_360(sample_customer_payload)
    assert 0.0 <= c360_res["churn_probability"] <= 1.0
    assert c360_res["risk_tier"] in {"Low Risk", "Medium Risk", "High Risk"}
    assert c360_res["predicted_next_12m_revenue_usd"] >= 0.0
    assert c360_res["prediction_interval_low_usd"] <= c360_res["predicted_next_12m_revenue_usd"]
    assert len(c360_res["top_risk_drivers"]) >= 1

    med_payload = dict(sample_customer_payload)
    med_payload.update({"recency_days": 85.0, "avg_csat": 3.0, "contract_type": "Monthly"})
    med_res = predictor.predict_customer_360(med_payload)
    assert med_res["risk_tier"] in {"Medium Risk", "High Risk", "Low Risk"}

    risky_payload = dict(sample_customer_payload)
    risky_payload.update(
        {
            "recency_days": 140.0,
            "avg_csat": 1.9,
            "escalation_rate": 0.65,
            "contract_type": "Monthly",
            "spend_momentum_ratio": 0.25,
        }
    )
    risky_res = predictor.predict_customer_360(risky_payload)
    assert risky_res["churn_probability"] > c360_res["churn_probability"]

    batch_out = predictor.predict_batch([sample_customer_payload, risky_payload])
    assert len(batch_out) == 2
    assert predictor.predict_batch([]) == []


def test_evaluation_pipeline_and_figures() -> None:
    """Verify generate_all_evaluations outputs all 9 figures and error analysis JSON."""
    error_report = generate_all_evaluations()
    assert error_report["classification_error_summary"]["total_test_samples"] == 800

    expected = [
        "eda_revenue_trend.png",
        "eda_regional_performance.png",
        "eda_correlation_heatmap.png",
        "eda_churn_drivers.png",
        "ml_classification_comparison.png",
        "ml_confusion_matrix.png",
        "ml_feature_importance.png",
        "ml_regression_diagnostics.png",
        "ml_clustering_analysis.png",
    ]
    for fname in expected:
        fpath = settings.figures_dir / fname
        assert fpath.exists(), f"Missing expected figure: {fname}"
        assert fpath.stat().st_size > 10_000
