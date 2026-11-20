"""Deterministic enterprise database generator with realistic DQ imperfections."""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

from src.config import get_logger, settings

logger = get_logger(__name__)

CUTOFF_DATE = pd.Timestamp("2025-12-31")
START_DATE = pd.Timestamp("2024-01-01")
FORWARD_END_DATE = pd.Timestamp("2026-06-30")

REGIONS_SPEC: list[dict[str, Any]] = [
    {
        "region_id": 1,
        "macro_region": "North America",
        "country_code": "USA",
        "country_name": "United States",
        "currency_code": "USD",
        "primary_city": "New York",
        "latitude": 40.7128,
        "longitude": -74.0060,
        "market_tier": "Tier 1",
    },
    {
        "region_id": 2,
        "macro_region": "North America",
        "country_code": "CAN",
        "country_name": "Canada",
        "currency_code": "CAD",
        "primary_city": "Toronto",
        "latitude": 43.6532,
        "longitude": -79.3832,
        "market_tier": "Tier 1",
    },
    {
        "region_id": 3,
        "macro_region": "Europe",
        "country_code": "GBR",
        "country_name": "United Kingdom",
        "currency_code": "GBP",
        "primary_city": "London",
        "latitude": 51.5074,
        "longitude": -0.1278,
        "market_tier": "Tier 1",
    },
    {
        "region_id": 4,
        "macro_region": "Europe",
        "country_code": "DEU",
        "country_name": "Germany",
        "currency_code": "EUR",
        "primary_city": "Berlin",
        "latitude": 52.5200,
        "longitude": 13.4050,
        "market_tier": "Tier 1",
    },
    {
        "region_id": 5,
        "macro_region": "Europe",
        "country_code": "FRA",
        "country_name": "France",
        "currency_code": "EUR",
        "primary_city": "Paris",
        "latitude": 48.8566,
        "longitude": 2.3522,
        "market_tier": "Tier 1",
    },
    {
        "region_id": 6,
        "macro_region": "MENA",
        "country_code": "EGY",
        "country_name": "Egypt",
        "currency_code": "EGP",
        "primary_city": "Cairo",
        "latitude": 30.0444,
        "longitude": 31.2357,
        "market_tier": "Growth",
    },
    {
        "region_id": 7,
        "macro_region": "MENA",
        "country_code": "ARE",
        "country_name": "United Arab Emirates",
        "currency_code": "AED",
        "primary_city": "Dubai",
        "latitude": 25.2048,
        "longitude": 55.2708,
        "market_tier": "Tier 1",
    },
    {
        "region_id": 8,
        "macro_region": "MENA",
        "country_code": "SAU",
        "country_name": "Saudi Arabia",
        "currency_code": "SAR",
        "primary_city": "Riyadh",
        "latitude": 24.7136,
        "longitude": 46.6753,
        "market_tier": "Growth",
    },
    {
        "region_id": 9,
        "macro_region": "APAC & LATAM",
        "country_code": "AUS",
        "country_name": "Australia",
        "currency_code": "AUD",
        "primary_city": "Sydney",
        "latitude": -33.8688,
        "longitude": 151.2093,
        "market_tier": "Tier 1",
    },
    {
        "region_id": 10,
        "macro_region": "APAC & LATAM",
        "country_code": "JPN",
        "country_name": "Japan",
        "currency_code": "JPY",
        "primary_city": "Tokyo",
        "latitude": 35.6762,
        "longitude": 139.6503,
        "market_tier": "Tier 1",
    },
    {
        "region_id": 11,
        "macro_region": "APAC & LATAM",
        "country_code": "IND",
        "country_name": "India",
        "currency_code": "INR",
        "primary_city": "Bengaluru",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "market_tier": "Growth",
    },
    {
        "region_id": 12,
        "macro_region": "APAC & LATAM",
        "country_code": "BRA",
        "country_name": "Brazil",
        "currency_code": "BRL",
        "primary_city": "Sao Paulo",
        "latitude": -23.5505,
        "longitude": -46.6333,
        "market_tier": "Emerging",
    },
]

CATEGORY_SPECS: dict[str, dict[str, Any]] = {
    "Cloud Software": {"base_price": 420.0, "cost_ratio": 0.28, "price_index": 0.98},
    "Enterprise Hardware": {"base_price": 680.0, "cost_ratio": 0.62, "price_index": 1.07},
    "Analytics Modules": {"base_price": 340.0, "cost_ratio": 0.24, "price_index": 0.95},
    "IoT Sensors": {"base_price": 195.0, "cost_ratio": 0.54, "price_index": 1.04},
    "Security Suites": {"base_price": 490.0, "cost_ratio": 0.30, "price_index": 1.02},
    "Managed Services": {"base_price": 560.0, "cost_ratio": 0.45, "price_index": 1.11},
}

ARCHETYPE_PROFILES: dict[str, dict[str, Any]] = {
    "Champions": {
        "prob": 0.22,
        "segment_probs": [0.70, 0.25, 0.05],  # Enterprise, Mid-Market, SMB
        "contract_probs": [0.65, 0.30, 0.05],  # 2-Year, Annual, Monthly
        "freq_range": (10, 16),
        "recency_range": (4, 30),
        "qty_range": (3, 7),
        "csat_mean": 4.65,
        "csat_std": 0.22,
        "ticket_range": (1, 3),
        "escalate_prob": 0.03,
        "delivery_mean": 3.0,
        "discount_range": (0.04, 0.12),
        "return_prob": 0.015,
    },
    "Loyal_Growth": {
        "prob": 0.30,
        "segment_probs": [0.22, 0.62, 0.16],
        "contract_probs": [0.15, 0.62, 0.23],
        "freq_range": (6, 10),
        "recency_range": (24, 62),
        "qty_range": (2, 4),
        "csat_mean": 4.12,
        "csat_std": 0.26,
        "ticket_range": (1, 4),
        "escalate_prob": 0.08,
        "delivery_mean": 4.2,
        "discount_range": (0.05, 0.15),
        "return_prob": 0.03,
    },
    "At_Risk_Friction": {
        "prob": 0.23,
        "segment_probs": [0.18, 0.48, 0.34],
        "contract_probs": [0.05, 0.28, 0.67],
        "freq_range": (4, 8),
        "recency_range": (68, 132),
        "qty_range": (1, 4),
        "csat_mean": 2.22,
        "csat_std": 0.32,
        "ticket_range": (5, 9),
        "escalate_prob": 0.50,
        "delivery_mean": 8.6,
        "discount_range": (0.02, 0.18),
        "return_prob": 0.12,
    },
    "Dormant_SMB": {
        "prob": 0.25,
        "segment_probs": [0.05, 0.20, 0.75],
        "contract_probs": [0.03, 0.17, 0.80],
        "freq_range": (1, 4),
        "recency_range": (165, 325),
        "qty_range": (1, 2),
        "csat_mean": 3.35,
        "csat_std": 0.30,
        "ticket_range": (0, 2),
        "escalate_prob": 0.14,
        "delivery_mean": 5.8,
        "discount_range": (0.00, 0.22),
        "return_prob": 0.05,
    },
}


def _load_macro_gdp_lookup() -> dict[str, float]:
    """Load country GDP growth lookup from fallback JSON for realistic macro modeling."""
    fallback_path = settings.fallback_dir / "macro_market_indicators.json"
    if fallback_path.exists():
        payload = json.loads(fallback_path.read_text(encoding="utf-8"))
        return {
            code: float(vals["gdp_growth_pct"])
            for code, vals in payload.get("gdp_growth", {}).items()
        }
    return {r["country_code"]: 2.2 for r in REGIONS_SPEC}


def _generate_products(rng: np.random.Generator) -> pd.DataFrame:
    """Create 60 product SKUs across 6 enterprise technology categories."""
    rows: list[dict[str, Any]] = []
    pid = 1
    for cat_idx, (cat, spec) in enumerate(CATEGORY_SPECS.items()):
        for item_idx in range(1, 11):
            multiplier = 0.72 + (item_idx * 0.065) + rng.uniform(-0.04, 0.04)
            list_price = round(spec["base_price"] * multiplier, 2)
            unit_cost = round(list_price * spec["cost_ratio"] * rng.uniform(0.92, 1.08), 2)
            reorder_level = int(rng.integers(20, 55))
            stock_qty = (
                int(rng.integers(5, reorder_level))
                if item_idx in (2, 9)
                else int(rng.integers(reorder_level + 10, 240))
            )
            rows.append(
                {
                    "product_id": pid,
                    "sku": f"NM-{cat_idx + 1}{item_idx:02d}",
                    "product_name": f"{cat.split()[0]} Module v{item_idx}.0",
                    "category": cat,
                    "unit_cost_usd": unit_cost,
                    "list_price_usd": list_price,
                    "reorder_level": reorder_level,
                    "stock_quantity": stock_qty,
                }
            )
            pid += 1
    return pd.DataFrame(rows)


def _generate_customers(
    rng: np.random.Generator, n_customers: int = 4000
) -> tuple[pd.DataFrame, list[str]]:
    """Generate customer dimension table and latent behavioral archetypes."""
    archetype_names = list(ARCHETYPE_PROFILES.keys())
    archetype_probs = [ARCHETYPE_PROFILES[k]["prob"] for k in archetype_names]
    assigned_archetypes = rng.choice(archetype_names, size=n_customers, p=archetype_probs).tolist()

    segments = ["Enterprise", "Mid-Market", "SMB"]
    contracts = ["2-Year", "Annual", "Monthly"]
    channels = ["Direct Sales", "Partner Network", "Inbound Web", "Referral", "Cloud Marketplace"]
    region_weights = np.array(
        [0.22, 0.07, 0.11, 0.10, 0.08, 0.08, 0.07, 0.06, 0.06, 0.06, 0.05, 0.04]
    )
    region_ids = np.arange(1, len(REGIONS_SPEC) + 1)

    rows: list[dict[str, Any]] = []
    cutoff_py = date(2025, 12, 31)
    for idx in range(n_customers):
        arch = assigned_archetypes[idx]
        prof = ARCHETYPE_PROFILES[arch]
        segment = str(rng.choice(segments, p=prof["segment_probs"]))
        contract = str(rng.choice(contracts, p=prof["contract_probs"]))
        channel = str(rng.choice(channels, p=[0.26, 0.22, 0.27, 0.13, 0.12]))
        region_id = int(rng.choice(region_ids, p=region_weights))
        min_tenure = max(140, prof["recency_range"][1] + 45)
        tenure_days = int(rng.integers(min_tenure, 725))
        signup = cutoff_py - timedelta(days=tenure_days)

        rows.append(
            {
                "customer_id": idx + 1,
                "customer_code": f"CUST-{idx + 1:05d}",
                "company_name": f"GlobalAccount {idx + 1:04d} Corp",
                "segment": segment,
                "contract_type": contract,
                "acquisition_channel": channel,
                "region_id": region_id,
                "signup_date": signup.isoformat(),
                "account_tenure_days": tenure_days,
                "is_active": 1,
            }
        )

    return pd.DataFrame(rows), assigned_archetypes


def _generate_historical_activity(
    rng: np.random.Generator,
    customers_df: pd.DataFrame,
    products_df: pd.DataFrame,
    archetypes: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame, dict[int, str]]:
    """Generate historical orders and support tickets up to 2025-12-31."""
    product_lookup = products_df.set_index("product_id").to_dict("index")
    product_ids = products_df["product_id"].to_numpy()
    payment_methods = ["Credit Card", "Wire Transfer", "ACH Direct", "Invoice Net-30"]
    issue_cats = ["Billing", "Integration", "Latency", "Onboarding", "License Key"]
    channels = ["Email", "Live Chat", "Phone", "Portal"]

    order_rows: list[dict[str, Any]] = []
    interaction_rows: list[dict[str, Any]] = []
    primary_cat_map: dict[int, str] = {}

    order_id = 1
    interaction_id = 1
    cutoff_py = date(2025, 12, 31)

    for idx, cust in customers_df.iterrows():
        cid = int(cust["customer_id"])
        arch = archetypes[idx]
        prof = ARCHETYPE_PROFILES[arch]
        tenure = int(cust["account_tenure_days"])
        region_id = int(cust["region_id"])

        preferred_cat = str(rng.choice(list(CATEGORY_SPECS.keys())))
        primary_cat_map[cid] = preferred_cat
        cat_products = products_df[
            products_df["category"] == preferred_cat
        ]["product_id"].to_numpy()

        n_orders = int(rng.integers(prof["freq_range"][0], prof["freq_range"][1] + 1))
        rec_low = prof["recency_range"][0]
        rec_high = max(rec_low + 1, min(prof["recency_range"][1], tenure - 10))
        recency_days = int(rng.integers(rec_low, rec_high + 1))
        last_order_day = cutoff_py - timedelta(days=recency_days)
        first_possible = cutoff_py - timedelta(days=tenure - 2)
        span = max((last_order_day - first_possible).days, 5)

        if n_orders == 1:
            order_offsets = [0]
        else:
            earlier = sorted(rng.integers(1, span + 1, size=n_orders - 1).tolist(), reverse=True)
            order_offsets = earlier + [0]

        for offset in order_offsets:
            odate = last_order_day - timedelta(days=int(offset))
            if rng.random() < 0.72:
                pid = int(rng.choice(cat_products))
            else:
                pid = int(rng.choice(product_ids))
            pinfo = product_lookup[pid]

            qty = int(rng.integers(prof["qty_range"][0], prof["qty_range"][1] + 1))
            discount = round(float(rng.uniform(*prof["discount_range"])), 4)
            unit_price = float(pinfo["list_price_usd"])
            gross_rev = round(qty * unit_price * (1.0 - discount), 2)
            shipping = round(float(rng.uniform(12.0, 58.0)), 2)
            net_profit = round(
                gross_rev - (qty * float(pinfo["unit_cost_usd"])) - shipping * 0.45, 2
            )
            delivery_days = round(
                float(np.clip(rng.normal(prof["delivery_mean"], 1.3), 1.0, 21.0)), 1
            )
            status = "Returned" if rng.random() < prof["return_prob"] else "Completed"
            if status == "Returned":
                net_profit = round(-abs(shipping * 1.2) - 15.0, 2)

            order_rows.append(
                {
                    "order_id": order_id,
                    "order_code": f"ORD-{order_id:06d}",
                    "customer_id": cid,
                    "product_id": pid,
                    "region_id": region_id,
                    "order_date": odate.isoformat(),
                    "quantity": qty,
                    "unit_price_usd": unit_price,
                    "discount_pct": discount,
                    "shipping_cost_usd": shipping,
                    "gross_revenue_usd": gross_rev,
                    "net_profit_usd": net_profit,
                    "delivery_days": delivery_days,
                    "payment_method": str(rng.choice(payment_methods)),
                    "order_status": status,
                }
            )
            order_id += 1

        n_tickets = int(rng.integers(prof["ticket_range"][0], prof["ticket_range"][1] + 1))
        for _ in range(n_tickets):
            t_offset = int(rng.integers(1, max(tenure - 1, 10)))
            tdate = cutoff_py - timedelta(days=t_offset)
            csat = round(
                float(np.clip(rng.normal(prof["csat_mean"], prof["csat_std"]), 1.0, 5.0)), 2
            )
            nps = int(np.clip(round((csat - 1.0) * 2.5 + rng.normal(0, 0.8)), 0, 10))
            escalated = int(rng.random() < prof["escalate_prob"])
            res_hours = round(
                float(
                    np.clip(
                        rng.normal(8.0 + escalated * 28.0 + (5.0 - csat) * 5.0, 4.0),
                        1.0,
                        96.0,
                    )
                ),
                1,
            )
            interaction_rows.append(
                {
                    "interaction_id": interaction_id,
                    "ticket_code": f"TKT-{interaction_id:06d}",
                    "customer_id": cid,
                    "interaction_date": tdate.isoformat(),
                    "channel": str(rng.choice(channels)),
                    "issue_category": str(rng.choice(issue_cats)),
                    "resolution_hours": res_hours,
                    "csat_score": csat,
                    "nps_score": nps,
                    "escalated": escalated,
                }
            )
            interaction_id += 1

    return pd.DataFrame(order_rows), pd.DataFrame(interaction_rows), primary_cat_map


def _compute_forward_outcomes_and_orders(
    rng: np.random.Generator,
    customers_df: pd.DataFrame,
    hist_orders: pd.DataFrame,
    hist_interactions: pd.DataFrame,
    products_df: pd.DataFrame,
    primary_cat_map: dict[int, str],
    gdp_lookup: dict[str, float],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compute leak-free forward churn & 12m revenue targets plus H1 2026 orders."""
    region_map = {r["region_id"]: r["country_code"] for r in REGIONS_SPEC}
    hist_orders_dt = hist_orders.copy()
    hist_orders_dt["order_dt"] = pd.to_datetime(hist_orders_dt["order_date"])

    ord_agg = (
        hist_orders_dt.groupby("customer_id")
        .agg(
            last_order=("order_dt", "max"),
            order_frequency=("order_id", "count"),
            hist_total_revenue=("gross_revenue_usd", "sum"),
            avg_delivery_days=("delivery_days", "mean"),
        )
        .reset_index()
    )
    ord_agg["recency_days"] = (CUTOFF_DATE - ord_agg["last_order"]).dt.days.astype(float)

    recent_90 = (
        hist_orders_dt[hist_orders_dt["order_dt"] >= pd.Timestamp("2025-10-02")]
        .groupby("customer_id")["gross_revenue_usd"]
        .sum()
        .rename("recent_90d_rev")
    )

    int_agg = (
        hist_interactions.groupby("customer_id")
        .agg(
            avg_csat=("csat_score", "mean"),
            escalation_rate=("escalated", "mean"),
            ticket_count=("interaction_id", "count"),
        )
        .reset_index()
    )

    merged = (
        customers_df.merge(ord_agg, on="customer_id", how="left")
        .merge(recent_90, on="customer_id", how="left")
        .merge(int_agg, on="customer_id", how="left")
    )
    merged["recent_90d_rev"] = merged["recent_90d_rev"].fillna(0.0)
    merged["avg_csat"] = merged["avg_csat"].fillna(3.8)
    merged["escalation_rate"] = merged["escalation_rate"].fillna(0.05)
    merged["ticket_count"] = merged["ticket_count"].fillna(0)
    merged["momentum"] = merged["recent_90d_rev"] / (
        (merged["hist_total_revenue"] / 4.0) + 100.0
    )

    outcomes_rows: list[dict[str, Any]] = []
    fwd_orders_rows: list[dict[str, Any]] = []
    next_order_id = int(hist_orders["order_id"].max()) + 1
    product_lookup = products_df.set_index("product_id").to_dict("index")

    for _, row in merged.iterrows():
        cid = int(row["customer_id"])
        recency = float(row["recency_days"])
        freq = float(row["order_frequency"])
        csat = float(row["avg_csat"])
        esc_rate = float(row["escalation_rate"])
        momentum = float(row["momentum"])
        deliv = float(row["avg_delivery_days"])
        contract = str(row["contract_type"])
        country = region_map[int(row["region_id"])]
        gdp = gdp_lookup.get(country, 2.2)
        pcat = primary_cat_map[cid]
        price_idx = CATEGORY_SPECS[pcat]["price_index"]

        contract_shift = {"Monthly": 1.05, "Annual": -0.25, "2-Year": -1.15}[contract]
        logit = (
            -1.45
            + 0.022 * (recency - 65.0)
            - 0.21 * (freq - 5.5)
            - 1.35 * (csat - 3.55)
            + 2.40 * esc_rate
            - 0.65 * momentum
            + 0.14 * (deliv - 4.8)
            + 1.35 * (price_idx - 1.0)
            - 0.08 * (gdp - 2.2)
            + contract_shift
            + float(rng.normal(0.0, 0.42))
        )
        churn_prob = float(1.0 / (1.0 + np.exp(-np.clip(logit, -15.0, 15.0))))
        is_churned = int(rng.random() < churn_prob)

        tenure_yrs = max(float(row["account_tenure_days"]) / 365.25, 0.5)
        annual_run_rate = float(row["hist_total_revenue"]) / tenure_yrs
        contract_mult = {"2-Year": 1.16, "Annual": 1.04, "Monthly": 0.90}[contract]
        csat_mult = 0.80 + 0.08 * csat
        macro_mult = 1.0 + (gdp - 2.0) * 0.018
        retention_mult = (1.0 - 0.86 * churn_prob)
        momentum_bonus = 0.25 * float(row["recent_90d_rev"])

        base_next_rev = (
            (annual_run_rate * 0.88 + momentum_bonus)
            * contract_mult
            * csat_mult
            * macro_mult
            * retention_mult
        )
        noisy_next_rev = max(0.0, round(base_next_rev * float(rng.normal(1.0, 0.11)), 2))

        outcomes_rows.append(
            {
                "customer_id": cid,
                "observation_cutoff": "2025-12-31",
                "is_churned": is_churned,
                "next_12m_revenue_usd": noisy_next_rev,
            }
        )

        # Generate H1 2026 operational orders for active/retained customers
        if is_churned == 0 and noisy_next_rev > 150.0:
            n_h1 = int(np.clip(round(freq * 0.32), 1, 6))
            target_h1_rev = noisy_next_rev * 0.48
            per_order_rev = target_h1_rev / n_h1
            cat_pids = products_df[products_df["category"] == pcat]["product_id"].to_numpy()
            for _ in range(n_h1):
                pid = int(rng.choice(cat_pids))
                pinfo = product_lookup[pid]
                unit_price = float(pinfo["list_price_usd"])
                qty = int(np.clip(round(per_order_rev / max(unit_price, 50.0)), 1, 12))
                discount = round(float(rng.uniform(0.02, 0.12)), 4)
                gross_rev = round(qty * unit_price * (1.0 - discount), 2)
                shipping = round(float(rng.uniform(14.0, 50.0)), 2)
                net_profit = round(
                    gross_rev - (qty * float(pinfo["unit_cost_usd"])) - shipping * 0.45, 2
                )
                h1_date = date(2026, 1, 1) + timedelta(days=int(rng.integers(0, 180)))
                fwd_orders_rows.append(
                    {
                        "order_id": next_order_id,
                        "order_code": f"ORD-{next_order_id:06d}",
                        "customer_id": cid,
                        "product_id": pid,
                        "region_id": int(row["region_id"]),
                        "order_date": h1_date.isoformat(),
                        "quantity": qty,
                        "unit_price_usd": unit_price,
                        "discount_pct": discount,
                        "shipping_cost_usd": shipping,
                        "gross_revenue_usd": gross_rev,
                        "net_profit_usd": net_profit,
                        "delivery_days": round(float(rng.uniform(2.0, 6.5)), 1),
                        "payment_method": "Invoice Net-30",
                        "order_status": "Completed",
                    }
                )
                next_order_id += 1

    return pd.DataFrame(outcomes_rows), pd.DataFrame(fwd_orders_rows)


def _inject_quality_defects(
    rng: np.random.Generator,
    customers_df: pd.DataFrame,
    orders_df: pd.DataFrame,
    interactions_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Inject controlled nulls, duplicates, casing noise, and outliers into raw SQL tables."""
    cust = customers_df.copy()
    orders = orders_df.copy()
    inter = interactions_df.copy()

    # 1. Casing & whitespace inconsistencies (~4%)
    seg_noise_idx = rng.choice(cust.index, size=int(len(cust) * 0.04), replace=False)
    for idx in seg_noise_idx:
        val = str(cust.at[idx, "segment"])
        cust.at[idx, "segment"] = rng.choice([f" {val.lower()} ", val.upper(), f"  {val}"])

    pay_noise_idx = rng.choice(orders.index, size=int(len(orders) * 0.04), replace=False)
    for idx in pay_noise_idx:
        val = str(orders.at[idx, "payment_method"])
        orders.at[idx, "payment_method"] = rng.choice([f" {val.lower()}", val.upper()])

    # 2. Controlled missing values (~3%)
    null_ch_idx = rng.choice(cust.index, size=int(len(cust) * 0.03), replace=False)
    cust.loc[null_ch_idx, "acquisition_channel"] = None

    for col in ("delivery_days", "discount_pct"):
        null_idx = rng.choice(orders.index, size=int(len(orders) * 0.03), replace=False)
        orders.loc[null_idx, col] = np.nan

    for col in ("csat_score", "resolution_hours"):
        null_idx = rng.choice(inter.index, size=int(len(inter) * 0.03), replace=False)
        inter.loc[null_idx, col] = np.nan

    # 3. Numeric outliers (~0.5%)
    out_idx = rng.choice(orders.index, size=max(10, int(len(orders) * 0.005)), replace=False)
    half = len(out_idx) // 2
    orders.loc[out_idx[:half], "delivery_days"] = 999.0
    orders.loc[out_idx[half:], "shipping_cost_usd"] = -45.0

    int_out_idx = rng.choice(inter.index, size=max(5, int(len(inter) * 0.005)), replace=False)
    inter.loc[int_out_idx, "resolution_hours"] = 750.0

    # 4. Duplicate business rows (~1.5% with fresh PKs so SQL PK constraint succeeds)
    dup_orders = orders.sample(frac=0.015, random_state=settings.random_state).copy()
    dup_orders["order_id"] = np.arange(
        int(orders["order_id"].max()) + 1, int(orders["order_id"].max()) + 1 + len(dup_orders)
    )
    orders = pd.concat([orders, dup_orders], ignore_index=True)

    dup_inter = inter.sample(frac=0.015, random_state=settings.random_state).copy()
    dup_inter["interaction_id"] = np.arange(
        int(inter["interaction_id"].max()) + 1,
        int(inter["interaction_id"].max()) + 1 + len(dup_inter),
    )
    inter = pd.concat([inter, dup_inter], ignore_index=True)

    return cust, orders, inter


def seed_enterprise_database(db_url: str | None = None, force: bool = False) -> Path:
    """Seed the enterprise SQL database with normalized tables and controlled defects.

    Args:
        db_url: Optional SQLAlchemy database URL override.
        force: Whether to regenerate tables even if database already exists.

    Returns:
        Path to the SQLite database file (or project raw dir if non-SQLite).
    """
    settings.ensure_directories()
    target_url = db_url or settings.database_url
    sqlite_path = settings.raw_dir / "enterprise_ops.db"

    if target_url.startswith("sqlite:///"):
        sqlite_path = Path(target_url.replace("sqlite:///", ""))
        if sqlite_path.exists() and not force:
            logger.info("Operational database already exists at %s; skipping seed.", sqlite_path)
            return sqlite_path

    logger.info("Seeding deterministic enterprise database (seed=%d)...", settings.random_state)
    rng = np.random.default_rng(settings.random_state)
    gdp_lookup = _load_macro_gdp_lookup()

    regions_df = pd.DataFrame(REGIONS_SPEC)
    products_df = _generate_products(rng)
    customers_clean, archetypes = _generate_customers(rng, n_customers=4000)
    hist_orders, hist_interactions, primary_cat_map = _generate_historical_activity(
        rng, customers_clean, products_df, archetypes
    )
    outcomes_df, fwd_orders = _compute_forward_outcomes_and_orders(
        rng, customers_clean, hist_orders, hist_interactions,
        products_df, primary_cat_map, gdp_lookup
    )
    all_orders_clean = pd.concat([hist_orders, fwd_orders], ignore_index=True)

    customers_raw, orders_raw, interactions_raw = _inject_quality_defects(
        rng, customers_clean, all_orders_clean, hist_interactions
    )

    engine = create_engine(target_url)
    with engine.begin() as conn:
        for tbl in (
            "customer_future_outcomes",
            "fact_customer_interactions",
            "fact_orders",
            "dim_customers",
            "dim_products",
            "dim_regions",
        ):
            conn.execute(text(f"DROP TABLE IF EXISTS {tbl}"))

    regions_df.to_sql("dim_regions", engine, if_exists="replace", index=False)
    products_df.to_sql("dim_products", engine, if_exists="replace", index=False)
    customers_raw.to_sql("dim_customers", engine, if_exists="replace", index=False)
    orders_raw.to_sql("fact_orders", engine, if_exists="replace", index=False)
    interactions_raw.to_sql("fact_customer_interactions", engine, if_exists="replace", index=False)
    outcomes_df.to_sql("customer_future_outcomes", engine, if_exists="replace", index=False)

    logger.info(
        "Database seeded: %d customers, %d raw orders, %d raw interactions, churn_rate=%.2f%%",
        len(customers_raw),
        len(orders_raw),
        len(interactions_raw),
        outcomes_df["is_churned"].mean() * 100.0,
    )
    return sqlite_path


if __name__ == "__main__":
    seed_enterprise_database(force=True)
