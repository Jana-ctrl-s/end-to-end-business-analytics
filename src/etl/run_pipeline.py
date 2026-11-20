"""CLI entry point to execute database seeding (if needed) and the full ETL pipeline."""

from __future__ import annotations

from src.config import get_logger
from src.etl.pipeline import ETLPipeline
from src.ingestion.seed_database import seed_enterprise_database

logger = get_logger(__name__)


def main(force_reseed: bool = False) -> None:
    """Run database seed and automated multi-source ETL pipeline."""
    seed_enterprise_database(force=force_reseed)
    pipeline = ETLPipeline()
    report = pipeline.run()
    logger.info("ETL Report Summary: %s", report.model_dump())


if __name__ == "__main__":
    main()
