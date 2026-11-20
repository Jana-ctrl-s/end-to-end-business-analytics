"""Fast, in-memory model inference service for churn, CLV revenue, and segmentation."""

from __future__ import annotations

import json
from typing import Any

import joblib
import numpy as np
import pandas as pd

from src.config import get_logger, settings
from src.ml.features import (
    CLASSIFICATION_CAT_FEATURES,
    CLASSIFICATION_NUM_FEATURES,
    CLUSTERING_FEATURES,
    REGRESSION_CAT_FEATURES,
    REGRESSION_NUM_FEATURES,
)

logger = get_logger(__name__)


class AnalyticsPredictor:
    """Loads serialized ML champions once and serves real-time & batch predictions."""

    def __init__(self) -> None:
        """Load champion models and registry metadata into memory."""
        models_dir = settings.models_dir
        self.churn_model = joblib.load(models_dir / "churn_champion.joblib")
        self.revenue_model = joblib.load(models_dir / "revenue_champion.joblib")
        self.seg_bundle: dict[str, Any] = joblib.load(models_dir / "segmentation_champion.joblib")
        registry_path = models_dir / "model_registry.json"
        self.registry: dict[str, Any] = (
            json.loads(registry_path.read_text(encoding="utf-8"))
            if registry_path.exists()
            else {}
        )
        self.residual_std = float(
            self.registry.get("regression", {}).get("residual_std", 450.0)
        )
        logger.info("AnalyticsPredictor initialized with serialized champion pipelines.")

    @staticmethod
    def _prepare_frame(records: list[dict[str, Any]]) -> pd.DataFrame:
        """Convert input dictionaries into a feature DataFrame with derived log revenue."""
        df = pd.DataFrame(records).copy()
        if "log_hist_revenue" not in df.columns:
            df["log_hist_revenue"] = np.log1p(df["hist_total_revenue_usd"].astype(float))
        return df

    @staticmethod
    def _risk_tier(prob: float) -> str:
        """Map churn probability to operational risk tier."""
        if prob >= 0.65:
            return "High Risk"
        if prob >= 0.35:
            return "Medium Risk"
        return "Low Risk"

    @staticmethod
    def _derive_drivers_and_action(
        row: dict[str, Any], prob: float, persona: str
    ) -> tuple[list[str], str]:
        """Generate explainable risk flags and prescriptive retention recommendations."""
        flags: list[str] = []
        if float(row.get("avg_csat", 5.0)) < 3.2:
            flags.append("Low CSAT (< 3.2/5.0)")
        if float(row.get("recency_days", 0.0)) > 75.0:
            flags.append("Elevated Inactivity (> 75 days)")
        if float(row.get("escalation_rate", 0.0)) > 0.25:
            flags.append("High Support Escalation Rate")
        if str(row.get("contract_type", "")) == "Monthly":
            flags.append("Flexible Monthly Contract Exposure")
        if float(row.get("spend_momentum_ratio", 1.0)) < 0.65:
            flags.append("Declining 90-Day Spend Momentum")
        if not flags:
            flags.append("Healthy Engagement Profile")

        if prob >= 0.65:
            action = (
                "Immediate Executive Outreach: Assign dedicated CSM, resolve open tickets, "
                "and propose a 15% Annual Contract lock-in incentive."
            )
        elif prob >= 0.35:
            action = (
                "Proactive Retention Campaign: Schedule Quarterly Business Review (QBR) and "
                "offer bundle loyalty discount."
            )
        elif persona == "Enterprise Champions":
            action = (
                "Expansion & Upsell Playbook: Pitch Security Suites / Analytics Modules "
                "cross-sell and executive advisory board invite."
            )
        else:
            action = "Maintain Automated Lifecycle Nurturing & Usage Milestones."
        return flags[:3], action

    def predict_churn(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Predict customer churn probability and risk tier."""
        df = self._prepare_frame([payload])[
            CLASSIFICATION_NUM_FEATURES + CLASSIFICATION_CAT_FEATURES
        ]
        prob = float(self.churn_model.predict_proba(df)[0, 1])
        pred = int(prob >= 0.5)
        return {
            "churn_probability": round(prob, 4),
            "churn_prediction": pred,
            "risk_tier": self._risk_tier(prob),
            "model_name": self.registry.get("classification", {}).get("champion_name", "Champion"),
        }

    def predict_revenue(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Predict next-12-month customer revenue with 80% empirical prediction band."""
        df = self._prepare_frame([payload])[REGRESSION_NUM_FEATURES + REGRESSION_CAT_FEATURES]
        pred = max(0.0, float(self.revenue_model.predict(df)[0]))
        margin = 1.28 * self.residual_std
        return {
            "predicted_next_12m_revenue_usd": round(pred, 2),
            "prediction_interval_low_usd": round(max(0.0, pred - margin), 2),
            "prediction_interval_high_usd": round(pred + margin, 2),
            "model_name": self.registry.get("regression", {}).get("champion_name", "Champion"),
        }

    def predict_segment(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Assign customer behavioral cluster and persona label."""
        df = self._prepare_frame([payload])[CLUSTERING_FEATURES]
        X_scaled = self.seg_bundle["scaler"].transform(df)
        centroids = self.seg_bundle["centroids_scaled"]
        dists = np.linalg.norm(centroids - X_scaled[0], axis=1)
        cluster_id = int(np.argmin(dists))
        persona = self.seg_bundle["persona_map"].get(cluster_id, f"Cluster {cluster_id}")
        return {
            "cluster_id": cluster_id,
            "cluster_label": persona,
            "model_name": self.seg_bundle.get("model_name", "ClusteringChampion"),
        }

    def predict_customer_360(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Run unified churn, CLV revenue, and segmentation inference with recommendations."""
        churn_res = self.predict_churn(payload)
        rev_res = self.predict_revenue(payload)
        seg_res = self.predict_segment(payload)
        flags, action = self._derive_drivers_and_action(
            payload, churn_res["churn_probability"], seg_res["cluster_label"]
        )
        return {
            **churn_res,
            **rev_res,
            **seg_res,
            "top_risk_drivers": flags,
            "recommended_action": action,
        }

    def predict_batch(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Score a batch of customer records vectorized across all three models."""
        if not records:
            return []
        df_all = self._prepare_frame(records)
        probs = self.churn_model.predict_proba(
            df_all[CLASSIFICATION_NUM_FEATURES + CLASSIFICATION_CAT_FEATURES]
        )[:, 1]
        revs = np.clip(
            self.revenue_model.predict(df_all[REGRESSION_NUM_FEATURES + REGRESSION_CAT_FEATURES]),
            0.0,
            None,
        )
        X_scaled = self.seg_bundle["scaler"].transform(df_all[CLUSTERING_FEATURES])
        centroids = self.seg_bundle["centroids_scaled"]
        dists = np.linalg.norm(X_scaled[:, None, :] - centroids[None, :, :], axis=2)
        cluster_ids = np.argmin(dists, axis=1)

        margin = 1.28 * self.residual_std
        outputs: list[dict[str, Any]] = []
        for idx, row in enumerate(records):
            prob = float(probs[idx])
            rev = float(revs[idx])
            cid = int(cluster_ids[idx])
            persona = self.seg_bundle["persona_map"].get(cid, f"Cluster {cid}")
            flags, action = self._derive_drivers_and_action(row, prob, persona)
            outputs.append(
                {
                    "churn_probability": round(prob, 4),
                    "churn_prediction": int(prob >= 0.5),
                    "risk_tier": self._risk_tier(prob),
                    "predicted_next_12m_revenue_usd": round(rev, 2),
                    "prediction_interval_low_usd": round(max(0.0, rev - margin), 2),
                    "prediction_interval_high_usd": round(rev + margin, 2),
                    "cluster_id": cid,
                    "cluster_label": persona,
                    "top_risk_drivers": flags,
                    "recommended_action": action,
                }
            )
        return outputs
