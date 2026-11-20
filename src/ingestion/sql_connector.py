"""SQLAlchemy relational database connector for multi-source data extraction."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.config import get_logger, settings
from src.ingestion.seed_database import seed_enterprise_database

logger = get_logger(__name__)


class SQLConnector:
    """Connector for reading relational tables and executing analytical SQL queries.

    Supports both local SQLite and PostgreSQL via SQLAlchemy URLs.
    """

    def __init__(self, database_url: str | None = None) -> None:
        """Initialize the SQLConnector.

        Args:
            database_url: SQLAlchemy connection string. Defaults to ``settings.database_url``.
        """
        self.database_url = database_url or settings.database_url
        if self.database_url.startswith("sqlite:///"):
            db_path = Path(self.database_url.replace("sqlite:///", ""))
            if not db_path.exists():
                seed_enterprise_database(self.database_url)
        self.engine: Engine = create_engine(self.database_url, future=True)

    def extract_table(self, table_name: str) -> pd.DataFrame:
        """Load an entire SQL table into a Pandas DataFrame.

        Args:
            table_name: Name of the database table to extract.

        Returns:
            DataFrame containing all rows from ``table_name``.
        """
        allowed_tables = {
            "dim_regions",
            "dim_products",
            "dim_customers",
            "fact_orders",
            "fact_customer_interactions",
            "customer_future_outcomes",
            "stg_orders_clean",
            "stg_customer_360",
            "ext_macro_indicators",
            "ext_competitor_benchmarks",
        }
        if table_name not in allowed_tables:
            raise ValueError(f"Unsupported table name requested: {table_name}")

        logger.info("Extracting table '%s' from SQL database...", table_name)
        df = pd.read_sql_table(table_name, con=self.engine)
        logger.info("Extracted %d rows from '%s'.", len(df), table_name)
        return df

    def extract_all_raw(self) -> dict[str, pd.DataFrame]:
        """Extract all operational tables required for the ETL pipeline.

        Returns:
            Dictionary mapping table names to DataFrames.
        """
        tables = [
            "dim_regions",
            "dim_products",
            "dim_customers",
            "fact_orders",
            "fact_customer_interactions",
            "customer_future_outcomes",
        ]
        return {tbl: self.extract_table(tbl) for tbl in tables}

    def execute_query(self, query: str, params: dict[str, Any] | None = None) -> pd.DataFrame:
        """Execute a read-only SQL query and return the results as a DataFrame.

        Args:
            query: SQL SELECT statement.
            params: Optional bind parameters.

        Returns:
            Query results as a Pandas DataFrame.
        """
        with self.engine.connect() as conn:
            return pd.read_sql_query(text(query), con=conn, params=params or {})
