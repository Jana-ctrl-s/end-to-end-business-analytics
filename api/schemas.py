"""Pydantic v2 request and response contracts for the FastAPI inference service."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CustomerFeaturesInput(BaseModel):
    """Input feature payload representing a customer profile up to observation cutoff."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "account_tenure_days": 420,
                "recency_days": 22.0,
                "order_frequency": 9,
                "hist_total_revenue_usd": 14800.0,
                "hist_total_profit_usd": 6200.0,
                "avg_order_value_usd": 1644.44,
                "recent_90d_revenue_usd": 3850.0,
                "spend_momentum_ratio": 1.01,
                "avg_discount_pct": 0.08,
                "avg_delivery_days": 3.4,
                "return_rate": 0.02,
                "support_tickets_count": 2,
                "avg_resolution_hours": 9.5,
                "avg_csat": 4.45,
                "avg_nps": 8.5,
                "escalation_rate": 0.0,
                "gdp_growth_pct": 2.8,
                "fx_rate_to_usd": 1.0,
                "competitor_price_index": 0.98,
                "segment": "Enterprise",
                "contract_type": "Annual",
                "acquisition_channel": "Direct Sales",
                "macro_region": "North America",
                "primary_category": "Cloud Software",
            }
        }
    )

    account_tenure_days: int = Field(ge=1, le=5000)
    recency_days: float = Field(ge=0.0, le=2000.0)
    order_frequency: int = Field(ge=1, le=500)
    hist_total_revenue_usd: float = Field(ge=0.0)
    hist_total_profit_usd: float
    avg_order_value_usd: float = Field(ge=0.0)
    recent_90d_revenue_usd: float = Field(ge=0.0)
    spend_momentum_ratio: float = Field(ge=0.0, le=20.0)
    avg_discount_pct: float = Field(ge=0.0, le=0.5)
    avg_delivery_days: float = Field(ge=0.5, le=45.0)
    return_rate: float = Field(ge=0.0, le=1.0)
    support_tickets_count: int = Field(ge=0, le=500)
    avg_resolution_hours: float = Field(ge=0.0, le=168.0)
    avg_csat: float = Field(ge=1.0, le=5.0)
    avg_nps: float = Field(ge=0.0, le=10.0)
    escalation_rate: float = Field(ge=0.0, le=1.0)
    gdp_growth_pct: float = Field(ge=-25.0, le=30.0)
    fx_rate_to_usd: float = Field(gt=0.0)
    competitor_price_index: float = Field(ge=0.5, le=2.0)
    segment: Literal["Enterprise", "Mid-Market", "SMB"]
    contract_type: Literal["Monthly", "Annual", "2-Year"]
    acquisition_channel: str = Field(min_length=2)
    macro_region: str = Field(min_length=2)
    primary_category: str = Field(min_length=2)


class ChurnPredictionResponse(BaseModel):
    """Response for churn probability scoring."""

    churn_probability: float
    churn_prediction: int
    risk_tier: str
    model_name: str


class RevenuePredictionResponse(BaseModel):
    """Response for forward 12-month revenue / CLV estimation."""

    predicted_next_12m_revenue_usd: float
    prediction_interval_low_usd: float
    prediction_interval_high_usd: float
    model_name: str


class SegmentPredictionResponse(BaseModel):
    """Response for customer behavioral cluster assignment."""

    cluster_id: int
    cluster_label: str
    model_name: str


class Customer360Response(BaseModel):
    """Unified multi-model inference response with prescriptive recommendations."""

    churn_probability: float
    churn_prediction: int
    risk_tier: str
    predicted_next_12m_revenue_usd: float
    prediction_interval_low_usd: float
    prediction_interval_high_usd: float
    cluster_id: int
    cluster_label: str
    top_risk_drivers: list[str]
    recommended_action: str


class BatchPredictionRequest(BaseModel):
    """Batch request wrapping up to 500 customer feature payloads."""

    records: list[CustomerFeaturesInput] = Field(min_length=1, max_length=500)


class BatchPredictionResponse(BaseModel):
    """Batch scoring output list."""

    count: int
    predictions: list[Customer360Response]


class HealthResponse(BaseModel):
    """Service liveness and readiness status."""

    status: str
    models_loaded: bool
    version: str


class ModelMetadataResponse(BaseModel):
    """Registered champion model benchmark metrics."""

    classification_champion: str
    classification_test_f1: float
    classification_roc_auc: float
    regression_champion: str
    regression_test_r2: float
    regression_test_rmse: float
    clustering_champion: str
    clustering_silhouette: float
