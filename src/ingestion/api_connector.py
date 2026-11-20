"""REST API ingestion connector with retry backoff, SQLite cache, and fallback."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.config import get_logger, settings
from src.ingestion.seed_database import REGIONS_SPEC

logger = get_logger(__name__)


class MacroAPIConnector:
    """Ingests FX exchange rates and World Bank GDP indicators via REST APIs.

    Implements exponential backoff retries, persistent local SQLite response caching,
    and deterministic offline JSON fallback for high resilience.
    """

    def __init__(
        self,
        cache_db_path: Path | None = None,
        fallback_path: Path | None = None,
        timeout_seconds: float = 8.0,
    ) -> None:
        """Initialize the REST API connector.

        Args:
            cache_db_path: Path to SQLite cache database.
            fallback_path: Path to deterministic offline fallback JSON file.
            timeout_seconds: HTTP request timeout in seconds.
        """
        settings.ensure_directories()
        self.cache_db_path = cache_db_path or (settings.cache_dir / "api_cache.db")
        self.fallback_path = fallback_path or (
            settings.fallback_dir / "macro_market_indicators.json"
        )
        self.timeout_seconds = timeout_seconds
        self._init_cache()

    def _init_cache(self) -> None:
        """Create local SQLite cache table if not already present."""
        with sqlite3.connect(self.cache_db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS api_cache (
                    cache_key TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    cached_at_utc TEXT NOT NULL
                )
                """
            )

    def _get_cached(self, key: str) -> dict[str, Any] | None:
        """Retrieve cached payload by key if present."""
        with sqlite3.connect(self.cache_db_path) as conn:
            row = conn.execute(
                "SELECT payload_json FROM api_cache WHERE cache_key = ?", (key,)
            ).fetchone()
        if row:
            return json.loads(row[0])
        return None

    def _set_cached(self, key: str, payload: dict[str, Any]) -> None:
        """Persist payload JSON in the SQLite cache."""
        now_utc = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.cache_db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO api_cache (cache_key, payload_json, cached_at_utc)
                VALUES (?, ?, ?)
                """,
                (key, json.dumps(payload), now_utc),
            )

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=3.0),
        retry=retry_if_exception_type((requests.RequestException, ValueError)),
    )
    def _fetch_json(self, url: str) -> Any:
        """Fetch JSON payload from a REST endpoint with exponential backoff."""
        resp = requests.get(url, timeout=self.timeout_seconds)
        resp.raise_for_status()
        return resp.json()

    def _load_fallback(self) -> dict[str, Any]:
        """Load deterministic offline macro fallback JSON."""
        if not self.fallback_path.exists():
            raise FileNotFoundError(f"Fallback JSON not found at {self.fallback_path}")
        return json.loads(self.fallback_path.read_text(encoding="utf-8"))

    def fetch_macro_indicators(self, use_cache: bool = True) -> pd.DataFrame:
        """Fetch FX rates and GDP growth percentages for all configured countries.

        Args:
            use_cache: Whether to read/write the persistent SQLite cache.

        Returns:
            Normalized DataFrame with columns matching ``ext_macro_indicators``.
        """
        fallback_data = self._load_fallback()
        fx_rates: dict[str, float] = dict(fallback_data.get("fx_rates", {}))
        gdp_growth: dict[str, dict[str, Any]] = dict(fallback_data.get("gdp_growth", {}))
        provider = "Fallback Snapshot"

        cached_payload = self._get_cached("macro_combined") if use_cache else None
        if cached_payload:
            logger.info("Loaded macro indicators from SQLite cache.")
            fx_rates.update(cached_payload.get("fx_rates", {}))
            gdp_growth.update(cached_payload.get("gdp_growth", {}))
            provider = cached_payload.get("source_provider", "SQLite Cache")
        else:
            live_sources: list[str] = []
            try:
                fx_json = self._fetch_json(settings.fx_api_url)
                rates = fx_json.get("rates", {})
                if isinstance(rates, dict) and "EUR" in rates:
                    for curr, val in rates.items():
                        if isinstance(val, (int, float)) and val > 0:
                            fx_rates[curr] = float(val)
                    live_sources.append("Open-ER API")
                    logger.info(
                        "Fetched live FX rates from Open-ER API (%d currencies).", len(rates)
                    )
            except Exception as exc:
                logger.warning("Live FX API unavailable (%s); retaining fallback FX rates.", exc)

            try:
                codes = ";".join(r["country_code"] for r in REGIONS_SPEC)
                wb_url = settings.worldbank_gdp_url.format(countries=codes)
                wb_json = self._fetch_json(wb_url)
                if isinstance(wb_json, list) and len(wb_json) > 1 and isinstance(wb_json[1], list):
                    for item in wb_json[1]:
                        iso3 = item.get("countryiso3code")
                        val = item.get("value")
                        yr = item.get("date")
                        if iso3 and val is not None:
                            gdp_growth[iso3] = {
                                "gdp_growth_pct": round(float(val), 2),
                                "year": int(yr) if yr else 2024,
                            }
                    live_sources.append("World Bank API")
                    logger.info("Fetched live World Bank GDP indicators.")
            except Exception as exc:
                logger.warning("World Bank API unavailable (%s); retaining fallback GDP data.", exc)

            if live_sources:
                provider = " + ".join(live_sources)
                if use_cache:
                    self._set_cached(
                        "macro_combined",
                        {
                            "fx_rates": fx_rates,
                            "gdp_growth": gdp_growth,
                            "source_provider": provider,
                        },
                    )

        now_utc = datetime.now(timezone.utc).isoformat()
        rows: list[dict[str, Any]] = []
        for region in REGIONS_SPEC:
            c_code = region["country_code"]
            curr = region["currency_code"]
            gdp_entry = gdp_growth.get(c_code, {"gdp_growth_pct": 2.0, "year": 2024})
            rows.append(
                {
                    "country_code": c_code,
                    "currency_code": curr,
                    "fx_rate_to_usd": round(float(fx_rates.get(curr, 1.0)), 4),
                    "gdp_growth_pct": round(float(gdp_entry["gdp_growth_pct"]), 2),
                    "indicator_year": int(gdp_entry.get("year", 2024)),
                    "source_provider": provider,
                    "ingested_at_utc": now_utc,
                }
            )
        return pd.DataFrame(rows)
