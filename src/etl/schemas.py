"""Pydantic v2 validation schemas for cleaned records and data quality auditing."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class CustomerRecord(BaseModel):
    """Schema for validated customer dimension rows."""

    customer_id: int = Field(gt=0)
    customer_code: str = Field(min_length=4)
    company_name: str = Field(min_length=2)
    segment: Literal["Enterprise", "Mid-Market", "SMB"]
    contract_type: Literal["Monthly", "Annual", "2-Year"]
    acquisition_channel: str = Field(min_length=2)
    region_id: int = Field(ge=1, le=12)
    signup_date: date
    account_tenure_days: int = Field(ge=1)


class OrderRecord(BaseModel):
    """Schema for validated order transaction rows."""

    order_id: int = Field(gt=0)
    order_code: str = Field(min_length=4)
    customer_id: int = Field(gt=0)
    product_id: int = Field(gt=0)
    region_id: int = Field(ge=1, le=12)
    order_date: date
    quantity: int = Field(ge=1, le=1000)
    unit_price_usd: float = Field(gt=0.0)
    discount_pct: float = Field(ge=0.0, le=0.5)
    shipping_cost_usd: float = Field(ge=0.0, le=500.0)
    gross_revenue_usd: float = Field(ge=0.0)
    net_profit_usd: float
    delivery_days: float = Field(ge=0.5, le=45.0)
    payment_method: Literal["Credit Card", "Wire Transfer", "ACH Direct", "Invoice Net-30"]
    order_status: Literal["Completed", "Returned"]


class InteractionRecord(BaseModel):
    """Schema for validated support interaction rows."""

    interaction_id: int = Field(gt=0)
    ticket_code: str = Field(min_length=4)
    customer_id: int = Field(gt=0)
    interaction_date: date
    channel: Literal["Email", "Live Chat", "Phone", "Portal"]
    issue_category: str = Field(min_length=2)
    resolution_hours: float = Field(ge=0.1, le=168.0)
    csat_score: float = Field(ge=1.0, le=5.0)
    nps_score: int = Field(ge=0, le=10)
    escalated: int = Field(ge=0, le=1)


class MacroIndicatorRecord(BaseModel):
    """Schema for validated external macroeconomic and FX indicator rows."""

    country_code: str = Field(min_length=3, max_length=3)
    currency_code: str = Field(min_length=3, max_length=3)
    fx_rate_to_usd: float = Field(gt=0.0)
    gdp_growth_pct: float = Field(ge=-25.0, le=30.0)
    indicator_year: int = Field(ge=2000, le=2030)
    source_provider: str = Field(min_length=3)


class CompetitorBenchmarkRecord(BaseModel):
    """Schema for validated web-scraped competitor pricing benchmark rows."""

    category: str = Field(min_length=3)
    competitor_avg_price: float = Field(gt=0.0)
    competitor_price_index: float = Field(ge=0.5, le=2.0)
    market_rating_avg: float = Field(ge=1.0, le=5.0)
    in_stock_rate: float = Field(ge=0.0, le=1.0)
    scraped_sample_count: int = Field(ge=1)


class DataQualityReport(BaseModel):
    """Structured audit report capturing pre- and post-ETL quality metrics."""

    raw_orders_count: int
    clean_orders_count: int
    duplicate_orders_removed: int
    raw_interactions_count: int
    clean_interactions_count: int
    duplicate_interactions_removed: int
    raw_customers_count: int
    clean_customers_count: int
    missing_values_imputed: int
    outliers_clamped: int
    casing_standardized_count: int
    validation_records_checked: int
    validation_errors_count: int
    post_cleaning_error_rate_pct: float
    pipeline_duration_seconds: float
