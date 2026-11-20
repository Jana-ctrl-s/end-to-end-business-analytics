"""Production FastAPI application exposing ML inference endpoints."""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from api.schemas import (
    BatchPredictionRequest,
    BatchPredictionResponse,
    ChurnPredictionResponse,
    Customer360Response,
    CustomerFeaturesInput,
    HealthResponse,
    ModelMetadataResponse,
    RevenuePredictionResponse,
    SegmentPredictionResponse,
)
from src.config import get_logger
from src.ml.predict import AnalyticsPredictor

logger = get_logger(__name__)

_predictor_holder: dict[str, AnalyticsPredictor] = {}


def get_predictor() -> AnalyticsPredictor:
    """Retrieve initialized ``AnalyticsPredictor`` or instantiate lazily."""
    if "instance" not in _predictor_holder:
        _predictor_holder["instance"] = AnalyticsPredictor()
    return _predictor_holder["instance"]


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Load serialized champion models once at server startup."""
    try:
        get_predictor()
        logger.info("FastAPI predictor warmed up successfully.")
    except Exception as exc:
        logger.warning("Models could not be preloaded on startup: %s", exc)
    yield
    _predictor_holder.clear()


app = FastAPI(
    title="NovaMetrics End-to-End Business Analytics API",
    description=(
        "Production REST microservice serving Churn Classification, "
        "12-Month Revenue Forecasting, and Behavioral Customer Segmentation."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_timing_header(request: Request, call_next) -> Response:
    """Attach request processing duration in milliseconds to every response."""
    t0 = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.2f}"
    return response


@app.get("/", tags=["System"])
def root() -> dict[str, str]:
    """Return service overview and interactive documentation links."""
    return {
        "service": "NovaMetrics Business Analytics Decision API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", response_model=HealthResponse, tags=["System"])
def health() -> HealthResponse:
    """Verify service health and confirm ML champion models are loaded."""
    try:
        get_predictor()
        return HealthResponse(status="ok", models_loaded=True, version="1.0.0")
    except Exception:
        return HealthResponse(status="degraded", models_loaded=False, version="1.0.0")


@app.get("/api/v1/models/metadata", response_model=ModelMetadataResponse, tags=["Governance"])
def models_metadata() -> ModelMetadataResponse:
    """Expose champion model identifiers and cross-validated KPI benchmarks."""
    predictor = get_predictor()
    reg = predictor.registry
    if not reg:
        raise HTTPException(status_code=503, detail="Model registry metadata unavailable")
    cls_m = reg["classification"]["champion_metrics"]
    rev_m = reg["regression"]["champion_metrics"]
    clu_m = reg["clustering"]["champion_metrics"]
    return ModelMetadataResponse(
        classification_champion=reg["classification"]["champion_name"],
        classification_test_f1=float(cls_m["test_f1"]),
        classification_roc_auc=float(cls_m["test_roc_auc"]),
        regression_champion=reg["regression"]["champion_name"],
        regression_test_r2=float(rev_m["test_r2"]),
        regression_test_rmse=float(rev_m["test_rmse"]),
        clustering_champion=reg["clustering"]["champion_name"],
        clustering_silhouette=float(clu_m["silhouette_score"]),
    )


@app.post("/api/v1/predict/churn", response_model=ChurnPredictionResponse, tags=["Inference"])
def predict_churn(payload: CustomerFeaturesInput) -> ChurnPredictionResponse:
    """Predict probability and risk tier of customer churn."""
    predictor = get_predictor()
    return ChurnPredictionResponse(**predictor.predict_churn(payload.model_dump()))


@app.post("/api/v1/predict/revenue", response_model=RevenuePredictionResponse, tags=["Inference"])
def predict_revenue(payload: CustomerFeaturesInput) -> RevenuePredictionResponse:
    """Forecast next-12-month customer revenue (CLV) with prediction interval."""
    predictor = get_predictor()
    return RevenuePredictionResponse(**predictor.predict_revenue(payload.model_dump()))


@app.post("/api/v1/predict/segment", response_model=SegmentPredictionResponse, tags=["Inference"])
def predict_segment(payload: CustomerFeaturesInput) -> SegmentPredictionResponse:
    """Assign customer to a behavioral RFM+engagement cluster persona."""
    predictor = get_predictor()
    return SegmentPredictionResponse(**predictor.predict_segment(payload.model_dump()))


@app.post(
    "/api/v1/predict/customer-360",
    response_model=Customer360Response,
    tags=["Inference"],
)
def predict_customer_360(payload: CustomerFeaturesInput) -> Customer360Response:
    """Run unified churn, revenue, and segmentation scoring with retention actions."""
    predictor = get_predictor()
    return Customer360Response(**predictor.predict_customer_360(payload.model_dump()))


@app.post("/api/v1/predict/batch", response_model=BatchPredictionResponse, tags=["Inference"])
def predict_batch(payload: BatchPredictionRequest) -> BatchPredictionResponse:
    """Score up to 500 customer records in a single vectorized request."""
    predictor = get_predictor()
    records = [item.model_dump() for item in payload.records]
    results = predictor.predict_batch(records)
    return BatchPredictionResponse(
        count=len(results),
        predictions=[Customer360Response(**r) for r in results],
    )
