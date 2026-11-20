"""Benchmark FastAPI real-time inference latency across 100 requests."""

from __future__ import annotations

import json
import time
from typing import Any

import numpy as np
from fastapi.testclient import TestClient

from api.main import app
from src.config import get_logger, settings

logger = get_logger(__name__)

SAMPLE_PAYLOAD: dict[str, Any] = {
    "account_tenure_days": 420,
    "recency_days": 24.0,
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


def benchmark_api_latency(n_requests: int = 100) -> dict[str, Any]:
    """Measure P50, P95, and P99 latency for FastAPI Customer-360 endpoint."""
    latencies_ms: list[float] = []
    with TestClient(app) as client:
        # Warm-up call
        warm = client.post("/api/v1/predict/customer-360", json=SAMPLE_PAYLOAD)
        warm.raise_for_status()

        for _ in range(n_requests):
            t0 = time.perf_counter()
            resp = client.post("/api/v1/predict/customer-360", json=SAMPLE_PAYLOAD)
            elapsed = (time.perf_counter() - t0) * 1000.0
            resp.raise_for_status()
            latencies_ms.append(elapsed)

    p50 = round(float(np.percentile(latencies_ms, 50)), 2)
    p95 = round(float(np.percentile(latencies_ms, 95)), 2)
    p99 = round(float(np.percentile(latencies_ms, 99)), 2)
    mean_ms = round(float(np.mean(latencies_ms)), 2)

    if p95 >= 200.0:
        raise RuntimeError(f"API P95 latency {p95}ms exceeds 200ms SLA!")

    result = {
        "requests_tested": n_requests,
        "api_mean_latency_ms": mean_ms,
        "api_p50_latency_ms": p50,
        "api_p95_latency_ms": p95,
        "api_p99_latency_ms": p99,
        "api_p95_under_200ms_sla": p95 < 200.0,
    }

    summary_path = settings.reports_dir / "metrics_summary.json"
    summary = (
        json.loads(summary_path.read_text(encoding="utf-8"))
        if summary_path.exists()
        else {}
    )
    summary.update(result)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    logger.info(
        "API Benchmark (%d reqs): P50=%.2fms | P95=%.2fms | P99=%.2fms",
        n_requests, p50, p95, p99,
    )
    return result


if __name__ == "__main__":
    benchmark_api_latency()
