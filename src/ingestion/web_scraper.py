"""BeautifulSoup web scraper for competitive pricing benchmarks with caching & fallback."""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from bs4 import BeautifulSoup
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.config import get_logger, settings
from src.ingestion.seed_database import CATEGORY_SPECS

logger = get_logger(__name__)

RATING_MAP: dict[str, float] = {
    "One": 1.0,
    "Two": 2.0,
    "Three": 3.0,
    "Four": 4.0,
    "Five": 5.0,
}


class CompetitorPriceScraper:
    """Scrapes public catalog pricing & availability signals via BeautifulSoup4.

    Normalizes extracted catalog statistics into category-level competitive price
    benchmarks, backed by exponential retry, SQLite caching, and offline HTML snapshot.
    """

    def __init__(
        self,
        cache_db_path: Path | None = None,
        fallback_html_path: Path | None = None,
        timeout_seconds: float = 8.0,
    ) -> None:
        """Initialize the web scraper.

        Args:
            cache_db_path: Path to SQLite cache DB.
            fallback_html_path: Path to offline HTML fixture snapshot.
            timeout_seconds: Request timeout in seconds.
        """
        settings.ensure_directories()
        self.cache_db_path = cache_db_path or (settings.cache_dir / "scraper_cache.db")
        self.fallback_html_path = fallback_html_path or (
            settings.fallback_dir / "catalog_snapshot.html"
        )
        self.timeout_seconds = timeout_seconds
        self._init_cache()

    def _init_cache(self) -> None:
        """Create local SQLite table for scraped benchmark caching."""
        with sqlite3.connect(self.cache_db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS scraper_cache (
                    cache_key TEXT PRIMARY KEY,
                    records_json TEXT NOT NULL,
                    cached_at_utc TEXT NOT NULL
                )
                """
            )

    def _get_cached(self, key: str) -> list[dict[str, Any]] | None:
        """Fetch cached scraped records if present."""
        with sqlite3.connect(self.cache_db_path) as conn:
            row = conn.execute(
                "SELECT records_json FROM scraper_cache WHERE cache_key = ?", (key,)
            ).fetchone()
        return json.loads(row[0]) if row else None

    def _set_cached(self, key: str, records: list[dict[str, Any]]) -> None:
        """Store scraped records into SQLite cache."""
        now_utc = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.cache_db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO scraper_cache (cache_key, records_json, cached_at_utc)
                VALUES (?, ?, ?)
                """,
                (key, json.dumps(records), now_utc),
            )

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=3.0),
        retry=retry_if_exception_type((requests.RequestException, ValueError)),
    )
    def _fetch_html(self, url: str) -> str:
        """Download HTML markup from the target URL with retry backoff."""
        headers = {"User-Agent": "NovaMetrics-AnalyticsBot/1.0 (+DEPI-Capstone)"}
        resp = requests.get(url, headers=headers, timeout=self.timeout_seconds)
        resp.raise_for_status()
        if "product_pod" not in resp.text:
            raise ValueError("Unexpected HTML structure returned by target site")
        return resp.text

    @staticmethod
    def parse_catalog_html(html: str) -> list[dict[str, Any]]:
        """Parse product cards from HTML using BeautifulSoup4.

        Args:
            html: Raw HTML markup containing ``article.product_pod`` items.

        Returns:
            List of parsed item dictionaries containing title, price, rating, and in_stock.
        """
        soup = BeautifulSoup(html, "lxml")
        items: list[dict[str, Any]] = []
        for pod in soup.select("article.product_pod"):
            title_el = pod.select_one("h3 a")
            price_el = pod.select_one("p.price_color")
            stock_el = pod.select_one("p.instock")
            rating_el = pod.select_one("p.star-rating")

            title = title_el.get("title", "").strip() if title_el else "Unknown"
            price_text = price_el.get_text(strip=True) if price_el else "0"
            price_match = re.search(r"([0-9]+(?:\.[0-9]+)?)", price_text)
            price_val = float(price_match.group(1)) if price_match else 0.0

            rating_val = 3.5
            if rating_el and rating_el.get("class"):
                for cls in rating_el["class"]:
                    if cls in RATING_MAP:
                        rating_val = RATING_MAP[cls]
                        break

            stock_txt = stock_el.get_text(strip=True).lower() if stock_el else ""
            in_stock = 1.0 if "in stock" in stock_txt else 0.0

            if price_val > 0:
                items.append(
                    {
                        "title": title,
                        "raw_price": price_val,
                        "rating": rating_val,
                        "in_stock": in_stock,
                    }
                )
        return items

    def scrape_competitor_benchmarks(self, use_cache: bool = True) -> pd.DataFrame:
        """Scrape and normalize competitive pricing indices across product categories.

        Args:
            use_cache: Whether to consult and update the local SQLite cache.

        Returns:
            DataFrame matching ``ext_competitor_benchmarks``.
        """
        if use_cache:
            cached = self._get_cached("competitor_benchmarks_v1")
            if cached:
                logger.info("Loaded scraped competitor benchmarks from SQLite cache.")
                return pd.DataFrame(cached)

        source_url = settings.scraper_target_url
        try:
            html = self._fetch_html(source_url)
            logger.info("Scraped live catalog HTML from %s.", source_url)
        except Exception as exc:
            logger.warning(
                "Live scraping failed (%s); parsing offline HTML snapshot %s.",
                exc,
                self.fallback_html_path,
            )
            html = self.fallback_html_path.read_text(encoding="utf-8")
            source_url = f"fallback://{self.fallback_html_path.name}"

        parsed_items = self.parse_catalog_html(html)
        if not parsed_items:
            html = self.fallback_html_path.read_text(encoding="utf-8")
            parsed_items = self.parse_catalog_html(html)
            source_url = f"fallback://{self.fallback_html_path.name}"

        categories = list(CATEGORY_SPECS.keys())
        buckets: dict[str, list[dict[str, Any]]] = {cat: [] for cat in categories}
        for idx, item in enumerate(parsed_items):
            buckets[categories[idx % len(categories)]].append(item)

        overall_mean_raw = sum(i["raw_price"] for i in parsed_items) / len(parsed_items)
        now_utc = datetime.now(timezone.utc).isoformat()
        records: list[dict[str, Any]] = []

        for cat, spec in CATEGORY_SPECS.items():
            cat_items = buckets[cat] or parsed_items
            raw_cat_mean = sum(i["raw_price"] for i in cat_items) / len(cat_items)
            rating_avg = sum(i["rating"] for i in cat_items) / len(cat_items)
            stock_rate = sum(i["in_stock"] for i in cat_items) / len(cat_items)

            # Scale public catalog dispersion around enterprise category baseline
            dispersion_factor = raw_cat_mean / max(overall_mean_raw, 1.0)
            blended_index = round(
                0.70 * spec["price_index"] + 0.30 * dispersion_factor,
                3,
            )
            comp_avg_price = round(spec["base_price"] * blended_index, 2)

            records.append(
                {
                    "category": cat,
                    "competitor_avg_price": comp_avg_price,
                    "competitor_price_index": blended_index,
                    "market_rating_avg": round(rating_avg, 2),
                    "in_stock_rate": round(stock_rate, 3),
                    "scraped_sample_count": len(cat_items),
                    "source_url": source_url,
                    "ingested_at_utc": now_utc,
                }
            )

        if use_cache:
            self._set_cached("competitor_benchmarks_v1", records)

        return pd.DataFrame(records)
