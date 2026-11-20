"""Integration and latency tests for the FastAPI inference microservice."""

from __future__ import annotations

import time
from typing import Any

import numpy as np
from fastapi.testclient import TestClient

from api.main import app


def test_api_root_health_and_metadata() -> None:
    """Verify system endpoints and champion metadata endpoint."""
    with TestClient(app) as client:
        root_resp = client.get("/")
        assert root_resp.status_code == 200
        assert "NovaMetrics" in root_resp.json()["service"]

        health_resp = client.get("/health")
        assert health_resp.status_code == 200
        assert health_resp.json()["status"] == "ok"
        assert health_resp.json()["models_loaded"] is True

        meta_resp = client.get("/api/v1/models/metadata")
        assert meta_resp.status_code == 200
        meta = meta_resp.json()
        assert meta["classification_test_f1"] >= 0.82
        assert meta["regression_test_r2"] >= 0.80
        assert meta["clustering_silhouette"] >= 0.50


def test_api_prediction_endpoints_and_validation(sample_customer_payload: dict[str, Any]) -> None:
    """Verify all 5 inference endpoints and Pydantic 422 rejection on invalid inputs."""
    with TestClient(app) as client:
        r_churn = client.post("/api/v1/predict/churn", json=sample_customer_payload)
        assert r_churn.status_code == 200
        assert "X-Process-Time-Ms" in r_churn.headers

        r_rev = client.post("/api/v1/predict/revenue", json=sample_customer_payload)
        assert r_rev.status_code == 200
        assert r_rev.json()["predicted_next_12m_revenue_usd"] >= 0.0

        r_seg = client.post("/api/v1/predict/segment", json=sample_customer_payload)
        assert r_seg.status_code == 200
        assert r_seg.json()["cluster_id"] in {0, 1, 2, 3}

        r_360 = client.post("/api/v1/predict/customer-360", json=sample_customer_payload)
        assert r_360.status_code == 200
        assert "recommended_action" in r_360.json()

        r_batch = client.post(
            "/api/v1/predict/batch",
            json={"records": [sample_customer_payload, sample_customer_payload]},
        )
        assert r_batch.status_code == 200
        assert r_batch.json()["count"] == 2

        bad_payload = dict(sample_customer_payload)
        bad_payload["avg_csat"] = 99.0
        r_bad = client.post("/api/v1/predict/churn", json=bad_payload)
        assert r_bad.status_code == 422


def test_api_p95_latency_under_200ms(sample_customer_payload: dict[str, Any]) -> None:
    """Benchmark Customer 360 endpoint over 30 sequential calls to enforce <200ms P95."""
    latencies: list[float] = []
    with TestClient(app) as client:
        client.post("/api/v1/predict/customer-360", json=sample_customer_payload)
        for _ in range(30):
            t0 = time.perf_counter()
            resp = client.post("/api/v1/predict/customer-360", json=sample_customer_payload)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            assert resp.status_code == 200
            latencies.append(elapsed_ms)

    p95 = float(np.percentile(latencies, 95))
    assert p95 < 200.0, f"API P95 latency {p95:.2f}ms exceeded 200ms SLA"
