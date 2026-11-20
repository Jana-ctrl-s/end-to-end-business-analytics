"""Multi-source data ingestion package (SQL, REST API, Web Scraper)."""

from src.ingestion.api_connector import MacroAPIConnector
from src.ingestion.sql_connector import SQLConnector
from src.ingestion.web_scraper import CompetitorPriceScraper

__all__ = ["SQLConnector", "MacroAPIConnector", "CompetitorPriceScraper"]
