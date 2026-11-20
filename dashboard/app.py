"""Interactive Executive BI Dashboard powered by Streamlit and Plotly Express."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

from src.config import PROJECT_ROOT, settings
from src.ml.predict import AnalyticsPredictor

st.set_page_config(
    page_title="NovaMetrics | Enterprise Business Analytics Platform",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

THEME_CSS = """
<style>
    .main-header {
        background: linear-gradient(120deg, #0F2A4A 0%, #1E3A8A 60%, #4F46E5 100%);
        padding: 1.25rem 1.75rem;
        border-radius: 12px;
        color: #FFFFFF;
        margin-bottom: 1.25rem;
    }
    .main-header h1 { margin: 0; font-size: 1.75rem; font-weight: 700; }
    .main-header p { margin: 0.3rem 0 0 0; opacity: 0.9; font-size: 0.95rem; }
    div[data-testid="metric-container"] {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 0.85rem 1rem;
    }
</style>
"""
st.markdown(THEME_CSS, unsafe_allow_html=True)

COLOR_SEQUENCE = ["#0F2A4A", "#6366F1", "#06B6D4", "#F59E0B", "#10B981", "#EF4444"]


@st.cache_data(show_spinner=False)
def load_dashboard_data() -> dict[str, Any]:
    """Load processed datasets and evaluation JSON artifacts with caching."""
    pdir: Path = settings.processed_dir
    mdir: Path = settings.models_dir
    data: dict[str, Any] = {
        "orders": pd.read_csv(pdir / "orders_clean.csv", parse_dates=["order_date"]),
        "products": pd.read_csv(pdir / "products.csv"),
        "regions": pd.read_csv(pdir / "regions.csv"),
        "c360": pd.read_csv(pdir / "customer_360.csv"),
        "macro": pd.read_csv(pdir / "macro_indicators.csv"),
        "competitors": pd.read_csv(pdir / "competitor_benchmarks.csv"),
        "dq_report": json.loads((pdir / "data_quality_report.json").read_text(encoding="utf-8")),
        "registry": json.loads((mdir / "model_registry.json").read_text(encoding="utf-8")),
    }
    return data


@st.cache_resource(show_spinner=False)
def get_predictor() -> AnalyticsPredictor:
    """Cache serialized champion ML pipelines across dashboard reruns."""
    return AnalyticsPredictor()


def _score_customer_scenario(payload: dict[str, Any]) -> dict[str, Any]:
    """Score scenario via remote API if configured, otherwise in-process predictor."""
    api_url = os.getenv("API_BASE_URL", "").strip()
    if api_url and api_url.startswith("http"):
        try:
            resp = requests.post(
                f"{api_url.rstrip('/')}/api/v1/predict/customer-360",
                json=payload,
                timeout=3.0,
            )
            if resp.ok:
                return resp.json()
        except requests.RequestException:
            pass
    return get_predictor().predict_customer_360(payload)


def main() -> None:
    """Render the interactive multi-tab executive decision intelligence dashboard."""
    st.markdown(
        """
        <div class="main-header">
            <h1>NovaMetrics Enterprise Decision Intelligence Platform</h1>
            <p>Unified Multi-Source BI, Churn Risk, 12M CLV Forecasting &amp; Segmentation</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not (settings.processed_dir / "customer_360.csv").exists():
        st.error("Processed datasets not found. Run `python -m scripts.run_all` first.")
        return

    data = load_dashboard_data()
    orders = data["orders"].merge(
        data["products"][["product_id", "category"]], on="product_id", how="left"
    ).merge(
        data["regions"][["region_id", "macro_region", "country_code", "country_name"]],
        on="region_id",
        how="left",
    ).merge(
        data["c360"][["customer_id", "segment"]], on="customer_id", how="left"
    )
    c360 = data["c360"]

    # Sidebar Dynamic Filters
    st.sidebar.header("Decision Filters")
    min_date = orders["order_date"].min().date()
    max_date = orders["order_date"].max().date()
    date_range = st.sidebar.date_input(
        "Order Date Range", value=(min_date, max_date), min_value=min_date, max_value=max_date
    )
    start_dt, end_dt = (
        (pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1]))
        if isinstance(date_range, (tuple, list)) and len(date_range) == 2
        else (pd.Timestamp(min_date), pd.Timestamp(max_date))
    )

    all_regions = sorted(c360["macro_region"].unique().tolist())
    sel_regions = st.sidebar.multiselect("Macro-Regions", all_regions, default=all_regions)

    all_segments = sorted(c360["segment"].unique().tolist())
    sel_segments = st.sidebar.multiselect("Customer Segments", all_segments, default=all_segments)

    all_cats = sorted(data["products"]["category"].unique().tolist())
    sel_cats = st.sidebar.multiselect("Product Categories", all_cats, default=all_cats)

    filtered_orders = orders[
        (orders["order_date"] >= start_dt)
        & (orders["order_date"] <= end_dt)
        & (orders["macro_region"].isin(sel_regions))
        & (orders["segment"].isin(sel_segments))
        & (orders["category"].isin(sel_cats))
    ]
    filtered_c360 = c360[
        (c360["macro_region"].isin(sel_regions))
        & (c360["segment"].isin(sel_segments))
        & (c360["primary_category"].isin(sel_cats))
    ]

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "Executive KPIs & Trends",
            "Geographic & Market Intelligence",
            "Churn Drivers & Segments",
            "Live ML Decision Simulator",
            "ML Governance & Data Quality",
        ]
    )

    with tab1:
        total_rev = filtered_orders["gross_revenue_usd"].sum()
        total_prof = filtered_orders["net_profit_usd"].sum()
        margin_pct = (total_prof / total_rev * 100.0) if total_rev > 0 else 0.0
        avg_csat = filtered_c360["avg_csat"].mean() if len(filtered_c360) else 0.0
        churn_pct = filtered_c360["is_churned"].mean() * 100.0 if len(filtered_c360) else 0.0
        fwd_clv = filtered_c360["next_12m_revenue_usd"].sum()

        k1, k2, k3, k4, k5, k6 = st.columns(6)
        k1.metric("Gross Revenue", f"${total_rev / 1e6:.2f}M", f"{len(filtered_orders):,} orders")
        k2.metric("Net Profit", f"${total_prof / 1e6:.2f}M", f"{margin_pct:.1f}% margin")
        k3.metric(
            "Active Accounts",
            f"{len(filtered_c360):,}",
            f"{filtered_c360['order_frequency'].mean():.1f} avg orders",
        )
        k4.metric("Avg CSAT", f"{avg_csat:.2f} / 5.0", "Target >= 4.0")
        k5.metric("Churn Rate", f"{churn_pct:.1f}%", "Forward 6M Cohort")
        k6.metric("Projected 12M CLV", f"${fwd_clv / 1e6:.2f}M", "ML Forecast Portfolio")

        col_l, col_r = st.columns([1.4, 1.0])
        with col_l:
            monthly = (
                filtered_orders.groupby("order_month")
                .agg(Revenue=("gross_revenue_usd", "sum"), Profit=("net_profit_usd", "sum"))
                .reset_index()
                .sort_values("order_month")
            )
            monthly["Revenue_MA3"] = monthly["Revenue"].rolling(3, min_periods=1).mean()
            fig_trend = go.Figure()
            fig_trend.add_trace(
                go.Scatter(
                    x=monthly["order_month"],
                    y=monthly["Revenue"],
                    name="Gross Revenue",
                    line=dict(color="#0F2A4A", width=2.5),
                )
            )
            fig_trend.add_trace(
                go.Scatter(
                    x=monthly["order_month"],
                    y=monthly["Profit"],
                    name="Net Profit",
                    line=dict(color="#10B981", width=2.2),
                )
            )
            fig_trend.add_trace(
                go.Scatter(
                    x=monthly["order_month"],
                    y=monthly["Revenue_MA3"],
                    name="3M Moving Avg",
                    line=dict(color="#F59E0B", width=1.8, dash="dot"),
                )
            )
            fig_trend.update_layout(
                title="Monthly Revenue & Profit Trajectory",
                template="plotly_white",
                height=380,
                legend=dict(orientation="h", y=1.08),
            )
            st.plotly_chart(fig_trend, use_container_width=True)

        with col_r:
            cat_perf = (
                filtered_orders.groupby("category")
                .agg(
                    Revenue=("gross_revenue_usd", "sum"),
                    Profit=("net_profit_usd", "sum"),
                    Orders=("order_id", "count"),
                )
                .reset_index()
                .sort_values("Revenue", ascending=True)
            )
            fig_cat = px.bar(
                cat_perf,
                x="Revenue",
                y="category",
                color="Profit",
                orientation="h",
                color_continuous_scale="Tealgrn",
                title="Category Revenue & Net Profit Comparison",
            )
            fig_cat.update_layout(template="plotly_white", height=380)
            st.plotly_chart(fig_cat, use_container_width=True)

    with tab2:
        geo_df = (
            filtered_c360.groupby(["country_code", "country_name", "macro_region"])
            .agg(
                Revenue=("hist_total_revenue_usd", "sum"),
                Customers=("customer_id", "count"),
                Churn_Pct=("is_churned", lambda s: s.mean() * 100.0),
                GDP_Growth=("gdp_growth_pct", "mean"),
            )
            .reset_index()
        )
        g_col1, g_col2 = st.columns([1.3, 1.0])
        with g_col1:
            fig_map = px.choropleth(
                geo_df,
                locations="country_code",
                color="Revenue",
                hover_name="country_name",
                hover_data={"Customers": True, "Churn_Pct": ":.1f", "GDP_Growth": ":.2f"},
                color_continuous_scale="Blues",
                title="Global Revenue Distribution Across Operating Markets",
            )
            fig_map.update_layout(height=410, margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig_map, use_container_width=True)

        with g_col2:
            fig_geo_bar = px.bar(
                geo_df.sort_values("Churn_Pct", ascending=False),
                x="country_code",
                y="Churn_Pct",
                color="macro_region",
                color_discrete_sequence=COLOR_SEQUENCE,
                title="Market Churn Rate (%) & Regional Benchmark",
            )
            fig_geo_bar.update_layout(template="plotly_white", height=410)
            st.plotly_chart(fig_geo_bar, use_container_width=True)

        m_col1, m_col2 = st.columns(2)
        with m_col1:
            st.subheader("External Macroeconomic & FX Feed (REST API)")
            st.dataframe(data["macro"], use_container_width=True, hide_index=True)
        with m_col2:
            st.subheader("Competitive Price Benchmarks (BeautifulSoup Scraper)")
            st.dataframe(data["competitors"], use_container_width=True, hide_index=True)

    with tab3:
        c_left, c_right = st.columns(2)
        with c_left:
            if "pca_1" in filtered_c360.columns:
                fig_pca = px.scatter(
                    filtered_c360,
                    x="pca_1",
                    y="pca_2",
                    color="cluster_label",
                    hover_data=["customer_code", "segment", "hist_total_revenue_usd", "avg_csat"],
                    color_discrete_sequence=["#10B981", "#06B6D4", "#EF4444", "#F59E0B"],
                    title="2D PCA Behavioral Customer Segmentation",
                    opacity=0.72,
                )
                fig_pca.update_layout(template="plotly_white", height=410)
                st.plotly_chart(fig_pca, use_container_width=True)

        with c_right:
            contract_churn = (
                filtered_c360.groupby(["contract_type", "segment"])["is_churned"]
                .mean()
                .mul(100)
                .reset_index()
                .rename(columns={"is_churned": "Churn Rate (%)"})
            )
            fig_cc = px.bar(
                contract_churn,
                x="contract_type",
                y="Churn Rate (%)",
                color="segment",
                barmode="group",
                color_discrete_sequence=COLOR_SEQUENCE,
                title="Churn Rate by Contract Commitment & Segment",
            )
            fig_cc.update_layout(template="plotly_white", height=410)
            st.plotly_chart(fig_cc, use_container_width=True)

        st.subheader("High-Priority At-Risk Accounts Watchlist")
        watchlist = (
            filtered_c360[
                (filtered_c360["avg_csat"] < 3.3) | (filtered_c360["recency_days"] > 90)
            ][
                [
                    "customer_code",
                    "segment",
                    "contract_type",
                    "macro_region",
                    "recency_days",
                    "hist_total_revenue_usd",
                    "avg_csat",
                    "escalation_rate",
                    "cluster_label",
                ]
            ]
            .sort_values("hist_total_revenue_usd", ascending=False)
            .head(25)
        )
        st.dataframe(watchlist, use_container_width=True, hide_index=True)
        st.download_button(
            "Download High-Risk Watchlist (CSV)",
            data=watchlist.to_csv(index=False).encode("utf-8"),
            file_name="high_risk_watchlist.csv",
            mime="text/csv",
        )

    with tab4:
        st.subheader("Interactive Real-Time Customer Decision Simulator")
        st.caption(
            "Adjust behavioral and commercial attributes to run live Churn, CLV, "
            "and Segmentation scoring."
        )
        with st.form("simulator_form"):
            fc1, fc2, fc3, fc4 = st.columns(4)
            segment = fc1.selectbox("Segment", ["Enterprise", "Mid-Market", "SMB"])
            contract_type = fc1.selectbox("Contract Type", ["2-Year", "Annual", "Monthly"])
            macro_region = fc1.selectbox("Macro-Region", all_regions)
            primary_cat = fc1.selectbox("Primary Category", all_cats)

            recency_days = fc2.slider("Recency (Days Since Order)", 1, 365, 28)
            order_frequency = fc2.slider("Historical Orders", 1, 25, 9)
            hist_rev = fc2.number_input(
                "Historical Revenue ($)", 100.0, 250000.0, 14500.0, step=500.0
            )
            recent_90d = fc2.number_input(
                "Recent 90-Day Revenue ($)", 0.0, 100000.0, 3600.0, step=250.0
            )

            avg_csat = fc3.slider("Avg CSAT Score (1–5)", 1.0, 5.0, 4.3, step=0.05)
            tickets_cnt = fc3.slider("Support Tickets", 0, 20, 2)
            escalation_rate = fc3.slider("Escalation Rate", 0.0, 1.0, 0.05, step=0.05)
            avg_deliv = fc3.slider("Avg Delivery Days", 1.0, 25.0, 3.5, step=0.5)

            tenure_days = fc4.slider("Account Tenure (Days)", 30, 1000, 420)
            gdp_growth = fc4.slider("Market GDP Growth (%)", -2.0, 10.0, 2.8, step=0.1)
            comp_idx = fc4.slider("Competitor Price Index", 0.85, 1.25, 1.00, step=0.01)
            submitted = st.form_submit_button("Run ML Decision Prediction", type="primary")

        payload = {
            "account_tenure_days": int(tenure_days),
            "recency_days": float(recency_days),
            "order_frequency": int(order_frequency),
            "hist_total_revenue_usd": float(hist_rev),
            "hist_total_profit_usd": float(hist_rev * 0.42),
            "avg_order_value_usd": float(hist_rev / max(order_frequency, 1)),
            "recent_90d_revenue_usd": float(recent_90d),
            "spend_momentum_ratio": float(recent_90d / ((hist_rev / 4.0) + 100.0)),
            "avg_discount_pct": 0.08,
            "avg_delivery_days": float(avg_deliv),
            "return_rate": 0.02,
            "support_tickets_count": int(tickets_cnt),
            "avg_resolution_hours": 10.0 + escalation_rate * 25.0,
            "avg_csat": float(avg_csat),
            "avg_nps": max(0.0, min(10.0, (avg_csat - 1.0) * 2.5)),
            "escalation_rate": float(escalation_rate),
            "gdp_growth_pct": float(gdp_growth),
            "fx_rate_to_usd": 1.0,
            "competitor_price_index": float(comp_idx),
            "segment": segment,
            "contract_type": contract_type,
            "acquisition_channel": "Direct Sales",
            "macro_region": macro_region,
            "primary_category": primary_cat,
        }
        if submitted or "last_sim" not in st.session_state:
            st.session_state["last_sim"] = _score_customer_scenario(payload)

        res = st.session_state["last_sim"]
        r1, r2, r3 = st.columns(3)
        r1.metric("Churn Probability", f"{res['churn_probability'] * 100:.1f}%", res["risk_tier"])
        r2.metric(
            "Projected 12M Revenue",
            f"${res['predicted_next_12m_revenue_usd']:,.2f}",
            f"80% Band: ${res['prediction_interval_low_usd']:,.0f}"
            f"–${res['prediction_interval_high_usd']:,.0f}",
        )
        r3.metric("Behavioral Persona", res["cluster_label"], f"Cluster #{res['cluster_id']}")

        st.info(f"**Prescriptive Action:** {res['recommended_action']}")
        st.write("**Top Risk & Behavioral Signals:**", ", ".join(res["top_risk_drivers"]))

    with tab5:
        st.subheader("Automated ETL Data Quality Audit")
        dq = data["dq_report"]
        dq1, dq2, dq3, dq4 = st.columns(4)
        dq_dups = dq["duplicate_orders_removed"] + dq["duplicate_interactions_removed"]
        dq_fixed = dq["outliers_clamped"] + dq["casing_standardized_count"]
        dq1.metric("Duplicate Rows Removed", f"{dq_dups:,}")
        dq2.metric("Missing Values Imputed", f"{dq['missing_values_imputed']:,}")
        dq3.metric("Outliers & Casing Fixed", f"{dq_fixed:,}")
        dq4.metric(
            "Post-ETL Error Rate",
            f"{dq['post_cleaning_error_rate_pct']:.4f}%",
            f"Duration: {dq['pipeline_duration_seconds']}s",
        )

        st.subheader("MLflow Model Benchmarking & Selection")
        reg = data["registry"]
        b1, b2, b3 = st.columns(3)
        with b1:
            st.markdown("**Churn Classification Benchmark**")
            st.dataframe(
                pd.DataFrame(reg["classification"]["benchmark"]),
                use_container_width=True,
                hide_index=True,
            )
        with b2:
            st.markdown("**Next-12M Revenue Regression Benchmark**")
            st.dataframe(
                pd.DataFrame(reg["regression"]["benchmark"]),
                use_container_width=True,
                hide_index=True,
            )
        with b3:
            st.markdown("**Customer Segmentation Benchmark**")
            st.dataframe(
                pd.DataFrame(reg["clustering"]["benchmark"]),
                use_container_width=True,
                hide_index=True,
            )

        fig_dir = PROJECT_ROOT / "reports" / "figures"
        img_cols = st.columns(2)
        if (fig_dir / "ml_classification_comparison.png").exists():
            img_cols[0].image(
                str(fig_dir / "ml_classification_comparison.png"),
                caption="Classification ROC & F1 Comparison",
            )
        if (fig_dir / "ml_feature_importance.png").exists():
            img_cols[1].image(
                str(fig_dir / "ml_feature_importance.png"),
                caption="Top Predictive Churn & CLV Drivers",
            )


if __name__ == "__main__":
    main()
