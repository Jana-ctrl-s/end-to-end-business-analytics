"""Unit and integration tests for SQL, REST API, Seeding, and Web Scraper ingestion."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest
import requests

from src.config import settings
from src.ingestion.api_connector import MacroAPIConnector
from src.ingestion.seed_database import seed_enterprise_database
from src.ingestion.sql_connector import SQLConnector
from src.ingestion.web_scraper import CompetitorPriceScraper


def test_seed_enterprise_database_roundtrip(tmp_path: Path) -> None:
    """seed_enterprise_database generates a deterministic SQLite DB with all 6 tables."""
    db_path = tmp_path / "seed_test.db"
    db_url = f"sqlite:///{db_path.as_posix()}"
    out_path = seed_enterprise_database(db_url=db_url, force=True)
    assert out_path.exists()
    # Second call without force skips re-seeding cleanly
    out_path_skip = seed_enterprise_database(db_url=db_url, force=False)
    assert out_path_skip == db_path

    conn = SQLConnector(database_url=db_url)
    tables = conn.extract_all_raw()
    assert len(tables["dim_customers"]) == 4000
    assert len(tables["fact_orders"]) > 30000


def test_sql_connector_extracts_all_tables() -> None:
    """SQLConnector loads all six operational tables and rejects invalid table names."""
    connector = SQLConnector()
    tables = connector.extract_all_raw()
    assert set(tables.keys()) == {
        "dim_regions",
        "dim_products",
        "dim_customers",
        "fact_orders",
        "fact_customer_interactions",
        "customer_future_outcomes",
    }
    assert len(tables["dim_regions"]) == 12
    assert len(tables["dim_products"]) == 60
    assert len(tables["dim_customers"]) == 4000

    with pytest.raises(ValueError, match="Unsupported table name"):
        connector.extract_table("nonexistent_table")


def test_sql_connector_execute_query() -> None:
    """SQLConnector executes parameterized read-only SQL queries."""
    connector = SQLConnector()
    df = connector.execute_query(
        "SELECT country_code, macro_region FROM dim_regions WHERE macro_region = :reg",
        params={"reg": "MENA"},
    )
    assert set(df["country_code"]) == {"EGY", "ARE", "SAU"}


def test_api_connector_live_mock_fallback_and_cache(tmp_path: Path) -> None:
    """MacroAPIConnector parses live REST JSON, caches results, and falls back on outage."""
    cache_db = tmp_path / "test_api_cache.db"
    connector = MacroAPIConnector(cache_db_path=cache_db, timeout_seconds=0.5)

    def fake_fetch(url: str) -> object:
        if "er-api" in url:
            return {"rates": {"USD": 1.0, "EUR": 0.91, "EGP": 48.9}}
        return [
            {"page": 1},
            [{"countryiso3code": "EGY", "value": 3.4, "date": "2024"}],
        ]

    with patch.object(MacroAPIConnector, "_fetch_json", side_effect=fake_fetch):
        live_df = connector.fetch_macro_indicators(use_cache=True)
    egy_live = live_df[live_df["country_code"] == "EGY"].iloc[0]
    assert egy_live["fx_rate_to_usd"] == 48.9
    assert egy_live["gdp_growth_pct"] == 3.4

    # Fallback path on fresh uncached DB
    fallback_conn = MacroAPIConnector(
        cache_db_path=tmp_path / "fallback_cache.db", timeout_seconds=0.5
    )
    with patch.object(
        MacroAPIConnector, "_fetch_json", side_effect=requests.ConnectionError("offline")
    ):
        fb_df = fallback_conn.fetch_macro_indicators(use_cache=False)
    assert len(fb_df) == 12
    assert (fb_df["fx_rate_to_usd"] > 0).all()


def test_scraper_parses_html_and_fallback(tmp_path: Path) -> None:
    """CompetitorPriceScraper parses product cards via BeautifulSoup and falls back cleanly."""
    html_sample = (settings.fallback_dir / "catalog_snapshot.html").read_text(encoding="utf-8")
    parsed = CompetitorPriceScraper.parse_catalog_html(html_sample)
    assert len(parsed) == 12
    assert parsed[0]["raw_price"] > 0

    scraper = CompetitorPriceScraper(cache_db_path=tmp_path / "scraper_cache.db")
    with patch.object(
        CompetitorPriceScraper, "_fetch_html", side_effect=requests.Timeout("blocked")
    ):
        df = scraper.scrape_competitor_benchmarks(use_cache=True)

    assert len(df) == 6
    assert (df["competitor_price_index"] > 0.5).all()
    df_cached = scraper.scrape_competitor_benchmarks(use_cache=True)
    pd.testing.assert_frame_equal(df, df_cached)
