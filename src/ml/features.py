"""Feature definitions, preprocessing pipelines, and cluster persona mapping."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler

CLASSIFICATION_NUM_FEATURES: list[str] = [
    "account_tenure_days",
    "recency_days",
    "order_frequency",
    "hist_total_revenue_usd",
    "hist_total_profit_usd",
    "avg_order_value_usd",
    "recent_90d_revenue_usd",
    "spend_momentum_ratio",
    "avg_discount_pct",
    "avg_delivery_days",
    "return_rate",
    "support_tickets_count",
    "avg_resolution_hours",
    "avg_csat",
    "avg_nps",
    "escalation_rate",
    "gdp_growth_pct",
    "fx_rate_to_usd",
    "competitor_price_index",
]

CLASSIFICATION_CAT_FEATURES: list[str] = [
    "segment",
    "contract_type",
    "acquisition_channel",
    "macro_region",
    "primary_category",
]

REGRESSION_NUM_FEATURES: list[str] = list(CLASSIFICATION_NUM_FEATURES) + ["log_hist_revenue"]
REGRESSION_CAT_FEATURES: list[str] = list(CLASSIFICATION_CAT_FEATURES)

CLUSTERING_FEATURES: list[str] = [
    "recency_days",
    "order_frequency",
    "log_hist_revenue",
    "avg_csat",
    "support_tickets_count",
]


def build_tabular_preprocessor(
    num_features: list[str],
    cat_features: list[str],
) -> ColumnTransformer:
    """Create a scikit-learn ColumnTransformer for numeric scaling and one-hot encoding.

    Args:
        num_features: Numeric column names.
        cat_features: Categorical column names.

    Returns:
        Configured ``ColumnTransformer``.
    """
    return ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), num_features),
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                cat_features,
            ),
        ],
        remainder="drop",
    )


def build_clustering_scaler() -> StandardScaler:
    """Create a StandardScaler for RFM + engagement clustering features."""
    return StandardScaler()


def derive_persona_map(df: pd.DataFrame, labels: np.ndarray) -> dict[int, str]:
    """Deterministically assign semantic business persona labels to cluster IDs.

    Args:
        df: Customer 360 DataFrame containing clustering features.
        labels: Integer cluster assignments matching rows of ``df``.

    Returns:
        Mapping from integer cluster ID to business persona name.
    """
    temp = df[CLUSTERING_FEATURES].copy()
    temp["cluster_id"] = labels
    centroids = temp.groupby("cluster_id").mean()

    remaining = set(centroids.index.tolist())
    persona_map: dict[int, str] = {}

    # 1. At-Risk High-Friction: lowest CSAT & highest support friction
    friction_score = centroids["support_tickets_count"] - (centroids["avg_csat"] * 2.0)
    at_risk_id = int(friction_score.loc[list(remaining)].idxmax())
    persona_map[at_risk_id] = "At-Risk High-Friction"
    remaining.remove(at_risk_id)

    # 2. Enterprise Champions: highest revenue + frequency & low recency
    champ_score = (
        centroids["log_hist_revenue"]
        + centroids["order_frequency"] * 0.25
        - centroids["recency_days"] * 0.02
    )
    champ_id = int(champ_score.loc[list(remaining)].idxmax())
    persona_map[champ_id] = "Enterprise Champions"
    remaining.remove(champ_id)

    # 3. Dormant Price-Sensitive: highest recency among remaining
    dormant_id = int(centroids["recency_days"].loc[list(remaining)].idxmax())
    persona_map[dormant_id] = "Dormant Price-Sensitive"
    remaining.remove(dormant_id)

    # 4. Loyal Growth Mid-Market: remaining active mid-tier cluster
    for rem_id in remaining:
        persona_map[int(rem_id)] = "Loyal Growth Mid-Market"

    return persona_map
