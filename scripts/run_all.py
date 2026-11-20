"""Execute the full end-to-end pipeline: seed -> ETL -> ML training -> evaluation."""

from __future__ import annotations

import json
import time
from typing import Any

from src.config import get_logger, settings
from src.etl.pipeline import ETLPipeline
from src.ingestion.seed_database import seed_enterprise_database
from src.ml.evaluate import generate_all_evaluations
from src.ml.train import train_all_models

logger = get_logger(__name__)


def run_end_to_end(force_reseed: bool = False) -> dict[str, Any]:
    """Run seeding, ETL, ML training, and visual/error evaluation end-to-end."""
    t0 = time.perf_counter()
    seed_enterprise_database(force=force_reseed)

    etl_report = ETLPipeline().run()
    registry = train_all_models()
    error_analysis = generate_all_evaluations()

    total_seconds = round(time.perf_counter() - t0, 2)
    cls_m = registry["classification"]["champion_metrics"]
    rev_m = registry["regression"]["champion_metrics"]
    clu_m = registry["clustering"]["champion_metrics"]

    summary: dict[str, Any] = {
        "total_pipeline_duration_seconds": total_seconds,
        "pipeline_under_15_min_sla": total_seconds < 900.0,
        "etl_error_rate_pct": etl_report.post_cleaning_error_rate_pct,
        "etl_under_0_1_pct_sla": etl_report.post_cleaning_error_rate_pct < 0.1,
        "classification_champion": registry["classification"]["champion_name"],
        "classification_test_f1": cls_m["test_f1"],
        "classification_test_roc_auc": cls_m["test_roc_auc"],
        "classification_f1_sla_passed": cls_m["test_f1"] >= 0.82,
        "regression_champion": registry["regression"]["champion_name"],
        "regression_test_r2": rev_m["test_r2"],
        "regression_test_rmse": rev_m["test_rmse"],
        "regression_baseline_rmse": registry["regression"]["baseline_metrics"]["test_rmse"],
        "regression_r2_sla_passed": rev_m["test_r2"] >= 0.80,
        "clustering_champion": registry["clustering"]["champion_name"],
        "clustering_silhouette": clu_m["silhouette_score"],
        "clustering_silhouette_sla_passed": clu_m["silhouette_score"] >= 0.50,
        "error_analysis_summary": error_analysis["classification_error_summary"],
    }

    summary_path = settings.reports_dir / "metrics_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    logger.info(
        "Full pipeline completed in %.2fs. Summary saved to %s", total_seconds, summary_path
    )
    return summary


if __name__ == "__main__":
    run_end_to_end()
