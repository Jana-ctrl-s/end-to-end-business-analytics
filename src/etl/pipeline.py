"""Automated ETL pipeline integrating SQL, REST API, and Web Scraper sources."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from pydantic import ValidationError
from sqlalchemy import create_engine, text

from src.config import get_logger, settings
from src.etl.schemas import (
    CompetitorBenchmarkRecord,
    CustomerRecord,
    DataQualityReport,
    InteractionRecord,
    MacroIndicatorRecord,
    OrderRecord,
)
from src.ingestion.api_connector import MacroAPIConnector
from src.ingestion.sql_connector import SQLConnector
from src.ingestion.web_scraper import CompetitorPriceScraper

logger = get_logger(__name__)

SEGMENT_CANONICAL: dict[str, str] = {
    "enterprise": "Enterprise",
    "mid-market": "Mid-Market",
    "smb": "SMB",
}

PAYMENT_CANONICAL: dict[str, str] = {
    "credit card": "Credit Card",
    "credit_card": "Credit Card",
    "wire transfer": "Wire Transfer",
    "ach direct": "ACH Direct",
    "invoice net-30": "Invoice Net-30",
}


def _standardize_series(series: pd.Series, mapping: dict[str, str]) -> tuple[pd.Series, int]:
    """Strip whitespace and map lowercase strings to canonical labels."""
    raw_vals = series.astype(str)
    cleaned = raw_vals.str.strip().str.lower().map(lambda x: mapping.get(x, x.title()))
    changed = int((raw_vals != cleaned).sum())
    return cleaned, changed


def _validate_dataframe(df: pd.DataFrame, model_cls: type[Any]) -> int:
    """Validate every record in a DataFrame against a Pydantic schema."""
    errors = 0
    for record in df.to_dict(orient="records"):
        try:
            model_cls.model_validate(record)
        except ValidationError as exc:
            errors += 1
            if errors <= 3:
                logger.error("Schema validation failure in %s: %s", model_cls.__name__, exc)
    return errors


class ETLPipeline:
    """End-to-end ETL orchestration: extraction, cleaning, validation, and staging."""

    def __init__(
        self,
        sql_connector: SQLConnector | None = None,
        api_connector: MacroAPIConnector | None = None,
        scraper: CompetitorPriceScraper | None = None,
        warehouse_url: str | None = None,
    ) -> None:
        """Initialize pipeline connectors and target directories.

        Args:
            sql_connector: Relational DB connector instance.
            api_connector: REST API macro indicator connector.
            scraper: BeautifulSoup competitor price scraper.
            warehouse_url: SQLAlchemy URL for cleaned analytical warehouse.
        """
        settings.ensure_directories()
        self.sql_connector = sql_connector or SQLConnector()
        self.api_connector = api_connector or MacroAPIConnector()
        self.scraper = scraper or CompetitorPriceScraper()
        self.warehouse_url = warehouse_url or settings.warehouse_database_url

    @staticmethod
    def clean_customers(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
        """Clean customer dimension table: standardize strings and impute channels."""
        out = df.copy()
        metrics = {"missing_imputed": 0, "casing_fixed": 0, "duplicates_removed": 0}

        before_len = len(out)
        out = out.drop_duplicates(subset=["customer_code"], keep="first").reset_index(drop=True)
        metrics["duplicates_removed"] = before_len - len(out)

        out["segment"], seg_changed = _standardize_series(out["segment"], SEGMENT_CANONICAL)
        metrics["casing_fixed"] += seg_changed

        out["contract_type"] = out["contract_type"].astype(str).str.strip()

        null_channels = int(out["acquisition_channel"].isna().sum())
        if null_channels > 0:
            mode_val = str(out["acquisition_channel"].dropna().mode().iloc[0])
            out["acquisition_channel"] = out["acquisition_channel"].fillna(mode_val)
            metrics["missing_imputed"] += null_channels

        out["signup_date"] = pd.to_datetime(out["signup_date"]).dt.date.astype(str)
        out["account_tenure_days"] = out["account_tenure_days"].astype(int)
        return out, metrics

    @staticmethod
    def clean_orders(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
        """Deduplicate, standardize, clamp outliers, and impute order transactions."""
        out = df.copy()
        metrics = {
            "missing_imputed": 0,
            "outliers_clamped": 0,
            "casing_fixed": 0,
            "duplicates_removed": 0,
        }

        before_len = len(out)
        out = out.drop_duplicates(subset=["order_code"], keep="first").reset_index(drop=True)
        metrics["duplicates_removed"] = before_len - len(out)

        out["payment_method"], pay_changed = _standardize_series(
            out["payment_method"], PAYMENT_CANONICAL
        )
        metrics["casing_fixed"] += pay_changed
        out["order_status"] = out["order_status"].astype(str).str.strip().str.title()

        # Detect and clamp numeric domain outliers before imputation
        deliv_outliers = (out["delivery_days"] > 45.0) | (out["delivery_days"] < 0.5)
        ship_outliers = (out["shipping_cost_usd"] < 0.0) | (out["shipping_cost_usd"] > 500.0)
        disc_outliers = (out["discount_pct"] < 0.0) | (out["discount_pct"] > 0.50)

        metrics["outliers_clamped"] += int(
            deliv_outliers.sum() + ship_outliers.sum() + disc_outliers.sum()
        )
        out.loc[deliv_outliers, "delivery_days"] = np.nan
        out.loc[ship_outliers, "shipping_cost_usd"] = (
            out.loc[ship_outliers, "shipping_cost_usd"].abs().clip(lower=8.0, upper=250.0)
        )
        out.loc[disc_outliers, "discount_pct"] = (
            out.loc[disc_outliers, "discount_pct"].clip(lower=0.0, upper=0.35)
        )

        # Group-median imputation
        for col, group_col in (("delivery_days", "region_id"), ("discount_pct", "order_status")):
            na_count = int(out[col].isna().sum())
            if na_count > 0:
                group_med = out.groupby(group_col)[col].transform("median")
                out[col] = out[col].fillna(group_med).fillna(out[col].median())
                metrics["missing_imputed"] += na_count

        out["order_dt"] = pd.to_datetime(out["order_date"])
        out["order_date"] = out["order_dt"].dt.date.astype(str)
        out["order_month"] = out["order_dt"].dt.strftime("%Y-%m")
        out = out.drop(columns=["order_dt"])
        return out, metrics

    @staticmethod
    def clean_interactions(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
        """Deduplicate, clamp resolution outliers, and impute CSAT/resolution hours."""
        out = df.copy()
        metrics = {
            "missing_imputed": 0,
            "outliers_clamped": 0,
            "duplicates_removed": 0,
        }

        before_len = len(out)
        out = out.drop_duplicates(subset=["ticket_code"], keep="first").reset_index(drop=True)
        metrics["duplicates_removed"] = before_len - len(out)

        out["channel"] = out["channel"].astype(str).str.strip()
        out["issue_category"] = out["issue_category"].astype(str).str.strip()

        res_outliers = (out["resolution_hours"] > 168.0) | (out["resolution_hours"] < 0.1)
        metrics["outliers_clamped"] += int(res_outliers.sum())
        out.loc[res_outliers, "resolution_hours"] = np.nan

        for col in ("csat_score", "resolution_hours"):
            na_count = int(out[col].isna().sum())
            if na_count > 0:
                grp_med = out.groupby("escalated")[col].transform("median")
                default_val = 3.8 if col == "csat_score" else 12.0
                out[col] = out[col].fillna(grp_med).fillna(out[col].median()).fillna(default_val)
                metrics["missing_imputed"] += na_count

        out["csat_score"] = out["csat_score"].clip(1.0, 5.0).round(2)
        out["resolution_hours"] = out["resolution_hours"].clip(0.5, 168.0).round(1)
        out["interaction_date"] = pd.to_datetime(out["interaction_date"]).dt.date.astype(str)
        return out, metrics

    @staticmethod
    def build_customer_360(
        customers: pd.DataFrame,
        orders: pd.DataFrame,
        interactions: pd.DataFrame,
        regions: pd.DataFrame,
        products: pd.DataFrame,
        macro_df: pd.DataFrame,
        competitor_df: pd.DataFrame,
        outcomes: pd.DataFrame,
        cutoff_date: str | None = None,
    ) -> pd.DataFrame:
        """Build leak-free Customer 360 feature table strictly from historical window."""
        cutoff = pd.Timestamp(cutoff_date or settings.feature_cutoff_date)
        recent_start = cutoff - pd.Timedelta(days=90)

        hist_orders = orders[pd.to_datetime(orders["order_date"]) <= cutoff].copy()
        hist_orders["order_dt"] = pd.to_datetime(hist_orders["order_date"])
        hist_orders = hist_orders.merge(
            products[["product_id", "category"]], on="product_id", how="left"
        )

        hist_inter = interactions[
            pd.to_datetime(interactions["interaction_date"]) <= cutoff
        ].copy()

        ord_agg = (
            hist_orders.groupby("customer_id")
            .agg(
                last_order_dt=("order_dt", "max"),
                order_frequency=("order_id", "count"),
                hist_total_revenue_usd=("gross_revenue_usd", "sum"),
                hist_total_profit_usd=("net_profit_usd", "sum"),
                avg_order_value_usd=("gross_revenue_usd", "mean"),
                avg_discount_pct=("discount_pct", "mean"),
                avg_delivery_days=("delivery_days", "mean"),
                return_rate=("order_status", lambda s: float((s == "Returned").mean())),
            )
            .reset_index()
        )
        ord_agg["recency_days"] = (cutoff - ord_agg["last_order_dt"]).dt.days.astype(float)
        ord_agg = ord_agg.drop(columns=["last_order_dt"])

        recent_90 = (
            hist_orders[hist_orders["order_dt"] >= recent_start]
            .groupby("customer_id")["gross_revenue_usd"]
            .sum()
            .rename("recent_90d_revenue_usd")
            .reset_index()
        )

        primary_cat = (
            hist_orders.groupby(["customer_id", "category"])["gross_revenue_usd"]
            .sum()
            .reset_index()
            .sort_values(["customer_id", "gross_revenue_usd"], ascending=[True, False])
            .drop_duplicates("customer_id")[["customer_id", "category"]]
            .rename(columns={"category": "primary_category"})
        )

        int_agg = (
            hist_inter.groupby("customer_id")
            .agg(
                support_tickets_count=("interaction_id", "count"),
                avg_resolution_hours=("resolution_hours", "mean"),
                avg_csat=("csat_score", "mean"),
                avg_nps=("nps_score", "mean"),
                escalation_rate=("escalated", "mean"),
            )
            .reset_index()
        )

        c360 = (
            customers[
                [
                    "customer_id",
                    "customer_code",
                    "segment",
                    "contract_type",
                    "acquisition_channel",
                    "region_id",
                    "account_tenure_days",
                ]
            ]
            .merge(
                regions[["region_id", "macro_region", "country_code", "country_name"]],
                on="region_id",
                how="left",
            )
            .merge(ord_agg, on="customer_id", how="left")
            .merge(recent_90, on="customer_id", how="left")
            .merge(primary_cat, on="customer_id", how="left")
            .merge(int_agg, on="customer_id", how="left")
            .merge(
                macro_df[["country_code", "gdp_growth_pct", "fx_rate_to_usd"]],
                on="country_code",
                how="left",
            )
            .merge(
                outcomes[["customer_id", "is_churned", "next_12m_revenue_usd"]],
                on="customer_id",
            )
        )

        c360["recent_90d_revenue_usd"] = c360["recent_90d_revenue_usd"].fillna(0.0)
        c360["primary_category"] = c360["primary_category"].fillna("Cloud Software")
        c360 = c360.merge(
            competitor_df[["category", "competitor_price_index"]],
            left_on="primary_category",
            right_on="category",
            how="left",
        ).drop(columns=["category", "region_id"])

        c360["support_tickets_count"] = c360["support_tickets_count"].fillna(0).astype(int)
        c360["avg_resolution_hours"] = c360["avg_resolution_hours"].fillna(0.0).round(2)
        c360["avg_csat"] = c360["avg_csat"].fillna(3.8).round(2)
        c360["avg_nps"] = c360["avg_nps"].fillna(7.0).round(2)
        c360["escalation_rate"] = c360["escalation_rate"].fillna(0.0).round(4)

        c360["spend_momentum_ratio"] = (
            c360["recent_90d_revenue_usd"] / ((c360["hist_total_revenue_usd"] / 4.0) + 100.0)
        ).round(4)
        c360["log_hist_revenue"] = np.log1p(c360["hist_total_revenue_usd"]).round(4)
        c360["cluster_id"] = -1
        c360["cluster_label"] = "Unassigned"

        for col in (
            "hist_total_revenue_usd",
            "hist_total_profit_usd",
            "avg_order_value_usd",
            "recent_90d_revenue_usd",
            "avg_delivery_days",
            "avg_discount_pct",
            "return_rate",
        ):
            c360[col] = c360[col].round(4)

        return c360

    def _publish_warehouse(
        self,
        regions: pd.DataFrame,
        products: pd.DataFrame,
        customers: pd.DataFrame,
        orders: pd.DataFrame,
        macro_df: pd.DataFrame,
        comp_df: pd.DataFrame,
        c360: pd.DataFrame,
    ) -> None:
        """Persist cleaned tables and execute SQL views in the analytical warehouse."""
        engine = create_engine(self.warehouse_url, future=True)
        regions.to_sql("dim_regions", engine, if_exists="replace", index=False)
        products.to_sql("dim_products", engine, if_exists="replace", index=False)
        customers.to_sql("dim_customers", engine, if_exists="replace", index=False)
        orders.to_sql("stg_orders_clean", engine, if_exists="replace", index=False)
        macro_df.to_sql("ext_macro_indicators", engine, if_exists="replace", index=False)
        comp_df.to_sql("ext_competitor_benchmarks", engine, if_exists="replace", index=False)
        c360.to_sql("stg_customer_360", engine, if_exists="replace", index=False)

        views_path = settings.sql_dir / "views.sql"
        if views_path.exists():
            sql_script = views_path.read_text(encoding="utf-8")
            with engine.begin() as conn:
                for stmt in sql_script.split(";"):
                    stmt_clean = stmt.strip()
                    if stmt_clean:
                        conn.execute(text(stmt_clean))
        logger.info("Analytical SQL warehouse and views updated at %s.", self.warehouse_url)

    def run(self) -> DataQualityReport:
        """Execute full ETL pipeline across SQL, REST API, and Web Scraper sources.

        Returns:
            ``DataQualityReport`` documenting exact cleaning metrics and timing.
        """
        t0 = time.perf_counter()
        logger.info("Starting automated multi-source ETL pipeline...")

        raw_tables = self.sql_connector.extract_all_raw()
        macro_df = self.api_connector.fetch_macro_indicators(use_cache=True)
        comp_df = self.scraper.scrape_competitor_benchmarks(use_cache=True)

        customers_clean, cust_m = self.clean_customers(raw_tables["dim_customers"])
        orders_clean, ord_m = self.clean_orders(raw_tables["fact_orders"])
        inter_clean, int_m = self.clean_interactions(raw_tables["fact_customer_interactions"])

        c360 = self.build_customer_360(
            customers=customers_clean,
            orders=orders_clean,
            interactions=inter_clean,
            regions=raw_tables["dim_regions"],
            products=raw_tables["dim_products"],
            macro_df=macro_df,
            competitor_df=comp_df,
            outcomes=raw_tables["customer_future_outcomes"],
        )

        # Pydantic schema validation
        err_cust = _validate_dataframe(customers_clean, CustomerRecord)
        err_ord = _validate_dataframe(orders_clean, OrderRecord)
        err_int = _validate_dataframe(inter_clean, InteractionRecord)
        err_macro = _validate_dataframe(macro_df, MacroIndicatorRecord)
        err_comp = _validate_dataframe(comp_df, CompetitorBenchmarkRecord)

        total_checked = (
            len(customers_clean) + len(orders_clean) + len(inter_clean)
            + len(macro_df) + len(comp_df)
        )
        total_errors = err_cust + err_ord + err_int + err_macro + err_comp
        error_rate_pct = round((total_errors / max(total_checked, 1)) * 100.0, 4)

        if error_rate_pct >= 0.1:
            raise RuntimeError(
                f"Post-cleaning error rate {error_rate_pct}% exceeds 0.1% SLA threshold!"
            )

        # Save processed CSV datasets
        out_dir = settings.processed_dir
        raw_tables["dim_regions"].to_csv(out_dir / "regions.csv", index=False)
        raw_tables["dim_products"].to_csv(out_dir / "products.csv", index=False)
        customers_clean.to_csv(out_dir / "customers_clean.csv", index=False)
        orders_clean.to_csv(out_dir / "orders_clean.csv", index=False)
        inter_clean.to_csv(out_dir / "interactions_clean.csv", index=False)
        macro_df.to_csv(out_dir / "macro_indicators.csv", index=False)
        comp_df.to_csv(out_dir / "competitor_benchmarks.csv", index=False)
        c360.to_csv(out_dir / "customer_360.csv", index=False)

        self._publish_warehouse(
            regions=raw_tables["dim_regions"],
            products=raw_tables["dim_products"],
            customers=customers_clean,
            orders=orders_clean,
            macro_df=macro_df,
            comp_df=comp_df,
            c360=c360,
        )

        duration = round(time.perf_counter() - t0, 3)
        report = DataQualityReport(
            raw_orders_count=len(raw_tables["fact_orders"]),
            clean_orders_count=len(orders_clean),
            duplicate_orders_removed=ord_m["duplicates_removed"],
            raw_interactions_count=len(raw_tables["fact_customer_interactions"]),
            clean_interactions_count=len(inter_clean),
            duplicate_interactions_removed=int_m["duplicates_removed"],
            raw_customers_count=len(raw_tables["dim_customers"]),
            clean_customers_count=len(customers_clean),
            missing_values_imputed=(
                cust_m["missing_imputed"] + ord_m["missing_imputed"] + int_m["missing_imputed"]
            ),
            outliers_clamped=ord_m["outliers_clamped"] + int_m["outliers_clamped"],
            casing_standardized_count=cust_m["casing_fixed"] + ord_m["casing_fixed"],
            validation_records_checked=total_checked,
            validation_errors_count=total_errors,
            post_cleaning_error_rate_pct=error_rate_pct,
            pipeline_duration_seconds=duration,
        )

        dq_path = Path(out_dir) / "data_quality_report.json"
        dq_path.write_text(json.dumps(report.model_dump(), indent=2), encoding="utf-8")
        logger.info(
            "ETL completed in %.2fs | Clean orders=%d | Error rate=%.4f%%",
            duration,
            len(orders_clean),
            error_rate_pct,
        )
        return report
