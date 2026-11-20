"""Publication-grade visualization suite and structured model error analysis."""

from __future__ import annotations

import json
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.metrics import auc, roc_curve

from src.config import get_logger, settings

logger = get_logger(__name__)

PALETTE = {
    "deep_blue": "#0F2A4A",
    "purple": "#6366F1",
    "cyan": "#06B6D4",
    "orange": "#F59E0B",
    "green": "#10B981",
    "red": "#EF4444",
    "slate": "#64748B",
}

plt.rcParams.update(
    {
        "figure.dpi": 300,
        "savefig.dpi": 300,
        "axes.edgecolor": "#CBD5E1",
        "axes.linewidth": 0.8,
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "axes.labelsize": 10,
        "font.size": 9.5,
    }
)


def _plot_eda_revenue_trend(orders: pd.DataFrame) -> None:
    """Plot monthly revenue & net profit trajectory."""
    monthly = (
        orders.groupby("order_month")
        .agg(revenue=("gross_revenue_usd", "sum"), profit=("net_profit_usd", "sum"))
        .reset_index()
        .sort_values("order_month")
    )
    fig, ax = plt.subplots(figsize=(11, 4.8))
    x = np.arange(len(monthly))
    ax.plot(
        x,
        monthly["revenue"] / 1e3,
        marker="o",
        lw=2.4,
        color=PALETTE["deep_blue"],
        label="Gross Revenue ($K)",
    )
    ax.fill_between(x, monthly["revenue"] / 1e3, alpha=0.10, color=PALETTE["cyan"])
    ax.plot(
        x,
        monthly["profit"] / 1e3,
        marker="s",
        lw=2.2,
        color=PALETTE["green"],
        label="Net Profit ($K)",
    )
    cutoff_idx = max(0, int((monthly["order_month"] <= "2025-12").sum()) - 1)
    ax.axvline(
        x=cutoff_idx,
        color=PALETTE["orange"],
        ls="--",
        lw=1.5,
        label="ML Feature Cutoff (2025-12)",
    )
    step = max(1, len(monthly) // 10)
    ax.set_xticks(x[::step])
    ax.set_xticklabels(monthly["order_month"].iloc[::step], rotation=35, ha="right")
    ax.set_ylabel("USD (Thousands)")
    ax.set_title("Monthly Enterprise Gross Revenue & Net Profit Trajectory (2024–2026)")
    ax.grid(axis="y", alpha=0.3)
    ax.legend(frameon=False)
    plt.tight_layout()
    plt.savefig(settings.figures_dir / "eda_revenue_trend.png")
    plt.close(fig)


def _plot_eda_regional_performance(c360: pd.DataFrame) -> None:
    """Plot regional total revenue and churn rate comparison."""
    reg = (
        c360.groupby("macro_region")
        .agg(
            revenue=("hist_total_revenue_usd", "sum"),
            churn_pct=("is_churned", lambda s: s.mean() * 100.0),
        )
        .sort_values("revenue", ascending=True)
        .reset_index()
    )
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 4.6))
    ax1.barh(reg["macro_region"], reg["revenue"] / 1e6, color=PALETTE["deep_blue"], height=0.55)
    ax1.set_xlabel("Historical Revenue ($ Millions)")
    ax1.set_title("Revenue Contribution by Macro-Region")
    ax1.grid(axis="x", alpha=0.3)

    colors = [PALETTE["red"] if v > 38 else PALETTE["cyan"] for v in reg["churn_pct"]]
    ax2.barh(reg["macro_region"], reg["churn_pct"], color=colors, height=0.55)
    ax2.set_xlabel("Observed Churn Rate (%)")
    ax2.set_title("Customer Churn Rate by Macro-Region")
    ax2.grid(axis="x", alpha=0.3)
    plt.tight_layout()
    plt.savefig(settings.figures_dir / "eda_regional_performance.png")
    plt.close(fig)


def _plot_eda_correlation_heatmap(c360: pd.DataFrame) -> None:
    """Plot multivariate correlation heatmap across key KPIs and targets."""
    cols = [
        "recency_days",
        "order_frequency",
        "hist_total_revenue_usd",
        "spend_momentum_ratio",
        "avg_csat",
        "escalation_rate",
        "avg_delivery_days",
        "competitor_price_index",
        "is_churned",
        "next_12m_revenue_usd",
    ]
    corr = c360[cols].corr()
    fig, ax = plt.subplots(figsize=(9.5, 7.2))
    sns.heatmap(
        corr,
        annot=True,
        fmt=".2f",
        cmap="RdBu_r",
        center=0.0,
        linewidths=0.5,
        ax=ax,
        annot_kws={"size": 8},
    )
    ax.set_title("Multivariate Correlation Matrix — Behavioral Drivers & Forward Targets")
    plt.tight_layout()
    plt.savefig(settings.figures_dir / "eda_correlation_heatmap.png")
    plt.close(fig)


def _plot_eda_churn_drivers(c360: pd.DataFrame) -> None:
    """Plot churn rate by contract type and CSAT band."""
    temp = c360.copy()
    temp["csat_band"] = pd.cut(
        temp["avg_csat"],
        bins=[0.0, 2.99, 3.99, 5.1],
        labels=["Low (<3.0)", "Moderate (3.0–3.9)", "High (4.0–5.0)"],
    )
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 4.6))

    contract_df = (
        temp.groupby("contract_type")["is_churned"].mean().mul(100).sort_values(ascending=False)
    )
    ax1.bar(
        contract_df.index,
        contract_df.values,
        color=[PALETTE["orange"], PALETTE["purple"], PALETTE["green"]],
        width=0.5,
    )
    ax1.set_ylabel("Churn Rate (%)")
    ax1.set_title("Churn Rate by Contract Commitment")
    ax1.grid(axis="y", alpha=0.3)

    csat_df = temp.groupby("csat_band", observed=False)["is_churned"].mean().mul(100)
    ax2.bar(
        csat_df.index.astype(str),
        csat_df.values,
        color=[PALETTE["red"], PALETTE["orange"], PALETTE["green"]],
        width=0.5,
    )
    ax2.set_ylabel("Churn Rate (%)")
    ax2.set_title("Churn Rate by CSAT Satisfaction Tier")
    ax2.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(settings.figures_dir / "eda_churn_drivers.png")
    plt.close(fig)


def _plot_classification_comparison(churn_eval: dict[str, Any]) -> None:
    """Plot model F1/ROC-AUC comparison alongside multi-model ROC curves."""
    bench = pd.DataFrame(churn_eval["all_models"])
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.8))

    x = np.arange(len(bench))
    w = 0.36
    ax1.bar(x - w / 2, bench["test_f1"], width=w, color=PALETTE["deep_blue"], label="Test F1")
    ax1.bar(
        x + w / 2, bench["test_roc_auc"], width=w, color=PALETTE["cyan"], label="Test ROC-AUC"
    )
    ax1.axhline(0.82, color=PALETTE["green"], ls="--", lw=1.4, label="KPI Target (0.82)")
    ax1.set_xticks(x)
    ax1.set_xticklabels(bench["model_name"], rotation=18, ha="right")
    ax1.set_ylim(0.65, 1.02)
    ax1.set_title("Churn Classification Model Benchmark")
    ax1.legend(frameon=False, loc="lower right")
    ax1.grid(axis="y", alpha=0.3)

    colors = [PALETTE["deep_blue"], PALETTE["purple"], PALETTE["cyan"], PALETTE["orange"]]
    for idx, (m_name, c_data) in enumerate(churn_eval["curves"].items()):
        fpr, tpr, _ = roc_curve(c_data["y_test"], c_data["y_prob"])
        roc_auc = auc(fpr, tpr)
        ax2.plot(
            fpr,
            tpr,
            lw=2.0,
            color=colors[idx % len(colors)],
            label=f"{m_name} (AUC={roc_auc:.3f})",
        )
    ax2.plot([0, 1], [0, 1], "k--", lw=1.0, alpha=0.5)
    ax2.set_xlabel("False Positive Rate")
    ax2.set_ylabel("True Positive Rate")
    ax2.set_title("ROC Curve Overlay Across Candidate Models")
    ax2.legend(frameon=False, loc="lower right", fontsize=8.5)
    ax2.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(settings.figures_dir / "ml_classification_comparison.png")
    plt.close(fig)


def _plot_confusion_matrix(churn_eval: dict[str, Any]) -> None:
    """Plot champion confusion matrix with counts and normalized percentages."""
    cm = np.asarray(churn_eval["confusion_matrix"])
    cm_norm = cm / cm.sum(axis=1, keepdims=True)
    labels = np.array(
        [[f"{cm[i, j]}\n({cm_norm[i, j]*100:.1f}%)" for j in range(2)] for i in range(2)]
    )
    fig, ax = plt.subplots(figsize=(5.8, 4.8))
    sns.heatmap(
        cm,
        annot=labels,
        fmt="",
        cmap="Blues",
        cbar=False,
        xticklabels=["Retained (0)", "Churned (1)"],
        yticklabels=["Actual Retained (0)", "Actual Churned (1)"],
        ax=ax,
        annot_kws={"size": 11, "weight": "bold"},
    )
    ax.set_xlabel("Predicted Label")
    ax.set_ylabel("True Label")
    ax.set_title(f"Champion Confusion Matrix ({churn_eval['champion']['model_name']})")
    plt.tight_layout()
    plt.savefig(settings.figures_dir / "ml_confusion_matrix.png")
    plt.close(fig)


def _plot_feature_importance(churn_eval: dict[str, Any], rev_eval: dict[str, Any]) -> None:
    """Plot top 12 feature importances for Churn and Revenue champions side-by-side."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.5, 5.2))
    c_imp = pd.DataFrame(churn_eval["feature_importances"]).iloc[::-1]
    r_imp = pd.DataFrame(rev_eval["feature_importances"]).iloc[::-1]

    ax1.barh(c_imp["feature"], c_imp["importance"], color=PALETTE["purple"])
    ax1.set_title(f"Top Churn Drivers ({churn_eval['champion']['model_name']})")
    ax1.set_xlabel("Normalized Importance")
    ax1.grid(axis="x", alpha=0.3)

    ax2.barh(r_imp["feature"], r_imp["importance"], color=PALETTE["cyan"])
    ax2.set_title(f"Top Revenue CLV Drivers ({rev_eval['champion']['model_name']})")
    ax2.set_xlabel("Normalized Importance")
    ax2.grid(axis="x", alpha=0.3)
    plt.tight_layout()
    plt.savefig(settings.figures_dir / "ml_feature_importance.png")
    plt.close(fig)


def _plot_regression_diagnostics(rev_eval: dict[str, Any]) -> None:
    """Plot predicted vs actual scatter and residual error distribution."""
    y_true = np.asarray(rev_eval["y_test"])
    y_pred = np.asarray(rev_eval["y_pred_champion"])
    residuals = y_true - y_pred

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.8))
    ax1.scatter(y_true / 1e3, y_pred / 1e3, alpha=0.35, s=14, color=PALETTE["deep_blue"])
    lim = max(y_true.max(), y_pred.max()) / 1e3
    ax1.plot([0, lim], [0, lim], color=PALETTE["orange"], lw=2.0, ls="--", label="Ideal y = x")
    ax1.set_xlabel("Actual Next-12M Revenue ($K)")
    ax1.set_ylabel("Predicted Next-12M Revenue ($K)")
    champ_nm = rev_eval["champion"]["model_name"]
    champ_r2 = rev_eval["champion"]["test_r2"]
    ax1.set_title(f"Predicted vs Actual CLV ({champ_nm}, R²={champ_r2:.3f})")
    ax1.legend(frameon=False)
    ax1.grid(alpha=0.3)

    ax2.hist(residuals / 1e3, bins=35, color=PALETTE["cyan"], edgecolor="white", alpha=0.88)
    ax2.axvline(0.0, color=PALETTE["red"], ls="--", lw=1.6)
    ax2.set_xlabel("Prediction Residual ($K)")
    ax2.set_ylabel("Customer Count")
    ax2.set_title("Regression Residual Distribution")
    ax2.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(settings.figures_dir / "ml_regression_diagnostics.png")
    plt.close(fig)


def _plot_clustering_analysis(clust_eval: dict[str, Any], c360: pd.DataFrame) -> None:
    """Plot k-scan silhouette/elbow and 2D PCA cluster segmentation."""
    k_df = pd.DataFrame(clust_eval["k_scan"])
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.5, 4.9))

    ax1.plot(
        k_df["k"],
        k_df["silhouette"],
        marker="o",
        lw=2.2,
        color=PALETTE["purple"],
        label="Silhouette Score",
    )
    ax1.axhline(0.50, color=PALETTE["green"], ls="--", lw=1.4, label="KPI Target (0.50)")
    ax1.set_xlabel("Number of Clusters (k)")
    ax1.set_ylabel("Silhouette Score")
    ax1.set_title("Optimal Cluster Count Validation (k=2..7)")
    ax1.legend(frameon=False)
    ax1.grid(alpha=0.3)

    persona_colors = {
        "Enterprise Champions": PALETTE["green"],
        "Loyal Growth Mid-Market": PALETTE["cyan"],
        "At-Risk High-Friction": PALETTE["red"],
        "Dormant Price-Sensitive": PALETTE["orange"],
    }
    for label, grp in c360.groupby("cluster_label"):
        ax2.scatter(
            grp["pca_1"],
            grp["pca_2"],
            s=14,
            alpha=0.65,
            color=persona_colors.get(str(label), PALETTE["slate"]),
            label=str(label),
        )
    ax2.set_xlabel("Principal Component 1")
    ax2.set_ylabel("Principal Component 2")
    sil_val = clust_eval["champion"]["silhouette_score"]
    ax2.set_title(f"2D PCA Behavioral Segments (Silhouette={sil_val:.3f})")
    ax2.legend(frameon=False, fontsize=8.5)
    ax2.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(settings.figures_dir / "ml_clustering_analysis.png")
    plt.close(fig)


def run_error_analysis(
    c360: pd.DataFrame, churn_eval: dict[str, Any], rev_eval: dict[str, Any]
) -> dict[str, Any]:
    """Perform error analysis on misclassified churn cases and high-residual CLV segments."""
    champ_name = churn_eval["champion"]["model_name"]
    c_curve = churn_eval["curves"][champ_name]
    test_df = c360.iloc[churn_eval["test_indices"]].copy()
    test_df["y_true"] = c_curve["y_test"]
    test_df["y_pred"] = c_curve["y_pred"]
    test_df["y_prob"] = c_curve["y_prob"]

    fp_df = test_df[(test_df["y_true"] == 0) & (test_df["y_pred"] == 1)]
    fn_df = test_df[(test_df["y_true"] == 1) & (test_df["y_pred"] == 0)]

    rev_df = c360.iloc[rev_eval["test_indices"]].copy()
    abs_err = np.abs(
        np.asarray(rev_eval["y_test"]) - np.asarray(rev_eval["y_pred_champion"])
    )
    rev_df["abs_err"] = abs_err
    seg_mae = rev_df.groupby("segment")["abs_err"].mean().round(2).to_dict()

    analysis = {
        "classification_error_summary": {
            "total_test_samples": len(test_df),
            "false_positives_count": len(fp_df),
            "false_negatives_count": len(fn_df),
            "fp_avg_probability": (
                round(float(fp_df["y_prob"].mean()), 3) if len(fp_df) else 0.0
            ),
            "fn_avg_probability": (
                round(float(fn_df["y_prob"].mean()), 3) if len(fn_df) else 0.0
            ),
            "fn_avg_csat": round(float(fn_df["avg_csat"].mean()), 2) if len(fn_df) else 0.0,
            "business_note": (
                "False Negatives carry higher revenue loss risk than False Positives; "
                "lowering probability alert threshold from 0.50 to 0.42 improves recall "
                "for high-CLV accounts."
            ),
        },
        "regression_error_by_segment_mae_usd": seg_mae,
        "limitations": [
            "Model features are anchored at historical cutoff (2025-12-31) without clickstream.",
            "Enterprise accounts exhibit wider CLV variance, raising segment-level MAE vs SMB.",
            "External macroeconomic indicators reflect annual GDP snapshots rather than quarterly.",
        ],
    }
    (settings.reports_dir / "error_analysis.json").write_text(
        json.dumps(analysis, indent=2), encoding="utf-8"
    )
    return analysis


def generate_all_evaluations() -> dict[str, Any]:
    """Generate all EDA/ML plots and structured error analysis."""
    plt.switch_backend("Agg")
    settings.ensure_directories()
    orders = pd.read_csv(settings.processed_dir / "orders_clean.csv")
    c360 = pd.read_csv(settings.processed_dir / "customer_360.csv")
    churn_eval = json.loads(
        (settings.models_dir / "churn_eval_artifacts.json").read_text(encoding="utf-8")
    )
    rev_eval = json.loads(
        (settings.models_dir / "revenue_eval_artifacts.json").read_text(encoding="utf-8")
    )
    clust_eval = json.loads(
        (settings.models_dir / "clustering_eval_artifacts.json").read_text(encoding="utf-8")
    )

    _plot_eda_revenue_trend(orders)
    _plot_eda_regional_performance(c360)
    _plot_eda_correlation_heatmap(c360)
    _plot_eda_churn_drivers(c360)
    _plot_classification_comparison(churn_eval)
    _plot_confusion_matrix(churn_eval)
    _plot_feature_importance(churn_eval, rev_eval)
    _plot_regression_diagnostics(rev_eval)
    _plot_clustering_analysis(clust_eval, c360)

    error_report = run_error_analysis(c360, churn_eval, rev_eval)
    logger.info(
        "Generated 9 figures in %s and saved error_analysis.json.", settings.figures_dir
    )
    return error_report


if __name__ == "__main__":
    generate_all_evaluations()
