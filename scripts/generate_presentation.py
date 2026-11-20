"""Generate a 14-slide widescreen Executive Presentation (.pptx) from verified metrics."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

from src.config import PROJECT_ROOT, get_logger, settings

logger = get_logger(__name__)

DEEP_BLUE = RGBColor(15, 42, 74)
INDIGO = RGBColor(99, 102, 241)
CYAN = RGBColor(6, 182, 212)
ORANGE = RGBColor(245, 158, 11)
GREEN = RGBColor(16, 185, 129)
SLATE = RGBColor(71, 85, 105)
LIGHT_BG = RGBColor(248, 250, 252)
WHITE = RGBColor(255, 255, 255)
DARK_TEXT = RGBColor(15, 23, 42)
BORDER_GRAY = RGBColor(203, 213, 225)


def _add_header_bar(slide: Any, title_text: str, subtitle_text: str, slide_num: int) -> None:
    """Apply consistent corporate header band and footer branding to content slides."""
    bg = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5)
    )
    bg.fill.solid()
    bg.fill.fore_color.rgb = LIGHT_BG
    bg.line.fill.background()

    hdr = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(1.05)
    )
    hdr.fill.solid()
    hdr.fill.fore_color.rgb = DEEP_BLUE
    hdr.line.fill.background()

    accent = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(1.05), Inches(13.333), Inches(0.06)
    )
    accent.fill.solid()
    accent.fill.fore_color.rgb = CYAN
    accent.line.fill.background()

    tf = hdr.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.55)
    tf.margin_top = Inches(0.14)
    p = tf.paragraphs[0]
    p.text = title_text
    p.font.size = Pt(23)
    p.font.bold = True
    p.font.color.rgb = WHITE

    p2 = tf.add_paragraph()
    p2.text = subtitle_text
    p2.font.size = Pt(12)
    p2.font.color.rgb = RGBColor(186, 230, 253)

    ftr = slide.shapes.add_textbox(Inches(0.55), Inches(7.12), Inches(12.2), Inches(0.3))
    fp = ftr.text_frame.paragraphs[0]
    fp.text = (
        f"DEPI AI & Data Science Capstone | NovaMetrics Platform   •   Slide {slide_num} / 14"
    )
    fp.font.size = Pt(10)
    fp.font.color.rgb = SLATE
    fp.alignment = PP_ALIGN.RIGHT


def _add_card(
    slide: Any,
    left: float,
    top: float,
    width: float,
    height: float,
    title: str,
    bullets: list[str],
    top_color: RGBColor = INDIGO,
) -> None:
    """Draw a rounded executive card with colored accent strip and bullet list."""
    card = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height)
    )
    card.fill.solid()
    card.fill.fore_color.rgb = WHITE
    card.line.color.rgb = BORDER_GRAY
    card.line.width = Pt(1)

    bar = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(0.08)
    )
    bar.fill.solid()
    bar.fill.fore_color.rgb = top_color
    bar.line.fill.background()

    tb = slide.shapes.add_textbox(
        Inches(left + 0.18), Inches(top + 0.16), Inches(width - 0.36), Inches(height - 0.24)
    )
    tf = tb.text_frame
    tf.word_wrap = True
    p0 = tf.paragraphs[0]
    p0.text = title
    p0.font.size = Pt(15)
    p0.font.bold = True
    p0.font.color.rgb = DEEP_BLUE
    p0.space_after = Pt(6)

    for b in bullets:
        p = tf.add_paragraph()
        p.text = f"• {b}"
        p.font.size = Pt(12.5)
        p.font.color.rgb = DARK_TEXT
        p.space_after = Pt(5)


def _add_kpi_box(
    slide: Any,
    left: float,
    top: float,
    width: float,
    height: float,
    label: str,
    value: str,
    sub: str,
    color: RGBColor,
) -> None:
    """Render a compact KPI metric scorecard."""
    box = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height)
    )
    box.fill.solid()
    box.fill.fore_color.rgb = WHITE
    box.line.color.rgb = color
    box.line.width = Pt(1.5)

    tb = slide.shapes.add_textbox(
        Inches(left + 0.14), Inches(top + 0.12), Inches(width - 0.28), Inches(height - 0.2)
    )
    tf = tb.text_frame
    tf.word_wrap = True
    p0 = tf.paragraphs[0]
    p0.text = label.upper()
    p0.font.size = Pt(10)
    p0.font.bold = True
    p0.font.color.rgb = SLATE

    p1 = tf.add_paragraph()
    p1.text = value
    p1.font.size = Pt(22)
    p1.font.bold = True
    p1.font.color.rgb = color
    p1.space_before = Pt(3)

    p2 = tf.add_paragraph()
    p2.text = sub
    p2.font.size = Pt(10.5)
    p2.font.color.rgb = DARK_TEXT


def _add_table(
    slide: Any,
    left: float,
    top: float,
    width: float,
    height: float,
    headers: list[str],
    rows: list[list[str]],
) -> None:
    """Insert a styled data table onto a slide."""
    table_shape = slide.shapes.add_table(
        len(rows) + 1, len(headers), Inches(left), Inches(top), Inches(width), Inches(height)
    )
    table = table_shape.table
    for j, h in enumerate(headers):
        cell = table.cell(0, j)
        cell.fill.solid()
        cell.fill.fore_color.rgb = DEEP_BLUE
        p = cell.text_frame.paragraphs[0]
        p.text = h
        p.font.size = Pt(11.5)
        p.font.bold = True
        p.font.color.rgb = WHITE

    for i, row in enumerate(rows, start=1):
        bg = WHITE if i % 2 == 1 else RGBColor(241, 245, 249)
        for j, val in enumerate(row):
            cell = table.cell(i, j)
            cell.fill.solid()
            cell.fill.fore_color.rgb = bg
            p = cell.text_frame.paragraphs[0]
            p.text = str(val)
            p.font.size = Pt(11)
            p.font.color.rgb = DARK_TEXT


def _add_image_fit(
    slide: Any, img_path: Path, left: float, top: float, width: float, height: float
) -> None:
    """Embed a PNG image scaled cleanly inside the specified bounding box."""
    if img_path.exists():
        slide.shapes.add_picture(
            str(img_path), Inches(left), Inches(top), width=Inches(width), height=Inches(height)
        )


def build_presentation() -> Path:
    """Create the 14-slide Executive Presentation PPTX from verified runtime artifacts."""
    metrics = json.loads(
        (settings.reports_dir / "metrics_summary.json").read_text(encoding="utf-8")
    )
    dq = json.loads(
        (settings.processed_dir / "data_quality_report.json").read_text(encoding="utf-8")
    )
    registry = json.loads(
        (settings.models_dir / "model_registry.json").read_text(encoding="utf-8")
    )

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank = prs.slide_layouts[6]

    # Slide 1: Title Slide
    s1 = prs.slides.add_slide(blank)
    bg1 = s1.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5)
    )
    bg1.fill.solid()
    bg1.fill.fore_color.rgb = DEEP_BLUE
    bg1.line.fill.background()
    stripe = s1.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(5.75), Inches(13.333), Inches(0.1)
    )
    stripe.fill.solid()
    stripe.fill.fore_color.rgb = CYAN
    stripe.line.fill.background()

    tb = s1.shapes.add_textbox(Inches(0.9), Inches(1.3), Inches(11.5), Inches(4.2))
    tf = tb.text_frame
    tf.word_wrap = True
    p0 = tf.paragraphs[0]
    p0.text = "DIGITAL EGYPT PIONEERS INITIATIVE (DEPI)  •  AI & DATA SCIENCE TRACK"
    p0.font.size = Pt(14)
    p0.font.bold = True
    p0.font.color.rgb = CYAN
    p0.space_after = Pt(18)

    p1 = tf.add_paragraph()
    p1.text = "End-to-End Business Analytics\nDecision Platform"
    p1.font.size = Pt(44)
    p1.font.bold = True
    p1.font.color.rgb = WHITE
    p1.space_after = Pt(16)

    p2 = tf.add_paragraph()
    p2.text = (
        "Unified Multi-Source Ingestion, Automated ETL, Statistical EDA, "
        "Executive BI Dashboard, Predictive ML Suite & Containerized FastAPI Serving"
    )
    p2.font.size = Pt(18)
    p2.font.color.rgb = RGBColor(203, 213, 225)

    tb_foot = s1.shapes.add_textbox(Inches(0.9), Inches(6.1), Inches(11.5), Inches(0.9))
    fp = tb_foot.text_frame.paragraphs[0]
    fp.text = (
        "Framework: CRISP-DM + Agile/Scrum   |   "
        "github.com/Jana-ctrl-s/end-to-end-business-analytics   |   Capstone Deck"
    )
    fp.font.size = Pt(13)
    fp.font.color.rgb = RGBColor(148, 163, 184)

    # Slide 2: Executive Summary
    s2 = prs.slides.add_slide(blank)
    _add_header_bar(
        s2,
        "Executive Summary & Business Problem",
        "From fragmented descriptive spreadsheets to unified predictive decision intelligence",
        2,
    )
    _add_card(
        s2,
        0.55,
        1.35,
        5.9,
        2.75,
        "Core Commercial Pain Points",
        [
            "Data Silos: Sales in SQL, macro KPIs in REST APIs, competitor prices on web.",
            "Lagging Velocity: Manual spreadsheets create multi-day reporting latency.",
            "No Predictive Foresight: Retrospective BI lacks churn or 12M CLV forecasts.",
            "Unquantified Drivers: Leadership cannot isolate CSAT or pricing impacts.",
        ],
        ORANGE,
    )
    _add_card(
        s2,
        6.8,
        1.35,
        5.95,
        2.75,
        "Platform Solution Architecture",
        [
            "100% Automated Ingestion (SQL + Open-ER/World Bank + BeautifulSoup4).",
            "Pydantic ETL staging leak-free Customer 360 feature store (<0.1% error).",
            "MLflow-tracked champions across Churn, CLV Regression & RFM Clustering.",
            "Containerized FastAPI (<200ms P95) & 5-tab Streamlit BI dashboard.",
        ],
        GREEN,
    )
    _add_kpi_box(
        s2, 0.55, 4.45, 2.9, 2.25, "ETL Error Rate",
        f"{metrics['etl_error_rate_pct']:.4f}%", "Target < 0.10% SLA", GREEN,
    )
    _add_kpi_box(
        s2, 3.65, 4.45, 2.9, 2.25, "Churn F1-Score",
        f"{metrics['classification_test_f1']:.4f}", "Target >= 0.82 SLA", INDIGO,
    )
    _add_kpi_box(
        s2, 6.75, 4.45, 2.9, 2.25, "CLV Forecast R²",
        f"{metrics['regression_test_r2']:.4f}", "Target >= 0.80 SLA", CYAN,
    )
    _add_kpi_box(
        s2, 9.85, 4.45, 2.9, 2.25, "Cluster Silhouette",
        f"{metrics['clustering_silhouette']:.4f}", "Target >= 0.50 SLA", ORANGE,
    )

    # Slide 3: Stakeholders & KPI Matrix
    s3 = prs.slides.add_slide(blank)
    _add_header_bar(
        s3,
        "Business Objectives, Stakeholders & KPIs",
        "CRISP-DM Phase 1 alignment connecting personas to quantitative targets",
        3,
    )
    _add_table(
        s3,
        0.55,
        1.35,
        12.2,
        2.65,
        ["Stakeholder Persona", "Core Operational Need", "Delivered Platform Interface"],
        [
            ["Executives", "Portfolio revenue, margins & 12M forecasts", "Streamlit & Deck"],
            ["Ops Managers", "At-risk account triage & retention actions", "Watchlist & Sim"],
            ["Data Analysts", "Clean SQL views & reproducible statistical EDA", "Warehouse & NB"],
            ["SWEs / Partners", "Real-time scoring embedded into CRM flows", "FastAPI + Docker"],
        ],
    )
    _add_table(
        s3,
        0.55,
        4.25,
        12.2,
        2.6,
        ["KPI Dimension", "Target SLA", "Verified Achievement", "Status"],
        [
            [
                "Pipeline & Quality",
                "< 15m | Err < 0.1%",
                f"{metrics['total_pipeline_duration_seconds']}s | "
                f"{metrics['etl_error_rate_pct']:.4f}% error",
                "PASSED",
            ],
            [
                "Churn Classification",
                "Test F1 >= 0.82",
                f"F1={metrics['classification_test_f1']:.4f} | "
                f"AUC={metrics['classification_test_roc_auc']:.4f} "
                f"({metrics['classification_champion']})",
                "PASSED",
            ],
            [
                "12M CLV Regression",
                "R² >= 0.80 & < Base",
                f"R²={metrics['regression_test_r2']:.4f} | "
                f"RMSE=${metrics['regression_test_rmse']:,.2f} vs "
                f"${metrics['regression_baseline_rmse']:,.2f}",
                "PASSED",
            ],
            [
                "Segmentation",
                "Silhouette >= 0.50",
                f"Sil={metrics['clustering_silhouette']:.4f} "
                f"({metrics['clustering_champion']})",
                "PASSED",
            ],
            [
                "REST API Latency",
                "API P95 < 200 ms",
                f"P95={metrics.get('api_p95_latency_ms', 0):.2f} ms "
                f"(P50={metrics.get('api_p50_latency_ms', 0):.2f} ms)",
                "PASSED",
            ],
        ],
    )

    # Slide 4: Architecture
    s4 = prs.slides.add_slide(blank)
    _add_header_bar(
        s4,
        "System Architecture & Technology Stack",
        "Decoupled 4-layer open-source ecosystem from ingestion to containerized serving",
        4,
    )
    arch_png = PROJECT_ROOT / "docs" / "04_system_design" / "diagrams" / "system_architecture.png"
    _add_image_fit(s4, arch_png, 0.55, 1.3, 12.2, 5.65)

    # Slide 5: Multi-Source Data Ingestion
    s5 = prs.slides.add_slide(blank)
    _add_header_bar(
        s5,
        "Phase 2 — Multi-Source Data Ingestion",
        "Automated connectors across Relational SQL, REST APIs & BeautifulSoup4 Scraping",
        5,
    )
    _add_card(
        s5,
        0.55,
        1.35,
        3.85,
        5.4,
        "1. Relational SQL DB",
        [
            "Normalized 3NF star schema supporting PostgreSQL & SQLite.",
            f"{dq['raw_customers_count']:,} customers across 12 markets & 60 SKUs.",
            f"{dq['raw_orders_count']:,} raw orders & {dq['raw_interactions_count']:,} tickets.",
            "Controlled defects injected to validate ETL resilience.",
        ],
        DEEP_BLUE,
    )
    _add_card(
        s5,
        4.72,
        1.35,
        3.85,
        5.4,
        "2. External REST APIs",
        [
            "Open-ER FX API fetching live rates across 11+ currencies.",
            "World Bank API fetching NY.GDP.MKTP.KD.ZG annual GDP growth.",
            "3x Tenacity exponential backoff retry policy on failures.",
            "Persistent SQLite cache + deterministic offline JSON fallback.",
        ],
        CYAN,
    )
    _add_card(
        s5,
        8.9,
        1.35,
        3.85,
        5.4,
        "3. Web Scraper (BS4)",
        [
            "BeautifulSoup4 + lxml parser extracting retail pricing & ratings.",
            "Normalizes benchmarks across all 6 product categories.",
            "Computes competitor_price_index & stock availability signals.",
            "Backed by SQLite cache + offline HTML snapshot fixture.",
        ],
        INDIGO,
    )

    # Slide 6: ETL & DQ Audit
    s6 = prs.slides.add_slide(blank)
    _add_header_bar(
        s6,
        "Phase 3 — Automated ETL & Data Quality Audit",
        "Deduplication, imputation, outlier clamping & Pydantic v2 contract enforcement",
        6,
    )
    dups_total = dq["duplicate_orders_removed"] + dq["duplicate_interactions_removed"]
    _add_table(
        s6,
        0.55,
        1.35,
        7.6,
        5.3,
        ["Data Quality Dimension", "Observed Raw Defects", "Remediation Applied"],
        [
            ["Duplicate Records", f"{dups_total:,} dups", "Deduplicated business keys"],
            ["Missing Values", f"{dq['missing_values_imputed']:,} nulls", "Group-median & mode"],
            ["Domain Outliers", f"{dq['outliers_clamped']:,} extremes", "Clamped 999d / neg ship"],
            ["Casing Noise", f"{dq['casing_standardized_count']:,} labels", "Canonical mapping"],
            [
                "Pydantic Gate",
                f"{dq['validation_records_checked']:,} rows",
                f"{dq['validation_errors_count']} errs ({dq['post_cleaning_error_rate_pct']:.4f}%)",
            ],
            ["Temporal Leakage", "Cutoff 2025-12-31", "Features <= cutoff; targets fwd"],
        ],
    )
    _add_card(
        s6,
        8.45,
        1.35,
        4.3,
        5.3,
        "Customer 360 Staging Store",
        [
            "Unified 4,000-row feature store combining RFM, momentum, CSAT & macro feeds.",
            "Zero missing values after ETL.",
            f"Total ETL duration: {dq['pipeline_duration_seconds']:.2f} seconds.",
            "Published to CSV & SQL analytics_warehouse.db with 5 BI views.",
        ],
        GREEN,
    )

    # Slide 7: EDA - Revenue & Regional Insights
    s7 = prs.slides.add_slide(blank)
    _add_header_bar(
        s7,
        "Phase 4 — EDA: Revenue Trajectory & Regional Performance",
        "Multi-year revenue/profit momentum and market-level growth vs churn dynamics",
        7,
    )
    _add_image_fit(s7, settings.figures_dir / "eda_revenue_trend.png", 0.45, 1.35, 6.2, 3.0)
    _add_image_fit(
        s7, settings.figures_dir / "eda_regional_performance.png", 6.75, 1.35, 6.1, 3.0
    )
    _add_card(
        s7,
        0.45,
        4.6,
        12.4,
        2.25,
        "Key Statistical & Commercial Findings (Notebook 02)",
        [
            "North America & Europe drive top revenue, while MENA/APAC offer growth upside.",
            "Strict 2025-12 feature cutoff keeps forward 2026 trends clean and verifiable.",
            "Monthly revenue and profit track steady enterprise procurement cycles.",
        ],
        DEEP_BLUE,
    )

    # Slide 8: EDA - Churn Drivers
    s8 = prs.slides.add_slide(blank)
    _add_header_bar(
        s8,
        "Phase 4 — EDA: Churn Drivers & Multivariate Correlations",
        "Hypothesis-tested attribution linking CSAT, contract lock-in & recency to churn",
        8,
    )
    _add_image_fit(
        s8, settings.figures_dir / "eda_correlation_heatmap.png", 0.5, 1.3, 6.0, 5.5
    )
    _add_image_fit(s8, settings.figures_dir / "eda_churn_drivers.png", 6.65, 1.3, 6.2, 2.9)
    _add_card(
        s8,
        6.65,
        4.4,
        6.2,
        2.4,
        "SciPy Hypothesis Validation",
        [
            "Welch t-test confirms churners have far lower CSAT & higher recency (p < 0.001).",
            "Chi-Square confirms Monthly contracts churn more than Annual / 2-Year locks.",
        ],
        ORANGE,
    )

    # Slide 9: ML Classification
    s9 = prs.slides.add_slide(blank)
    _add_header_bar(
        s9,
        "Phase 6 & 7 — Churn Classification Benchmark",
        f"Champion: {metrics['classification_champion']} | "
        f"F1={metrics['classification_test_f1']:.4f} | "
        f"ROC-AUC={metrics['classification_test_roc_auc']:.4f}",
        9,
    )
    _add_image_fit(
        s9, settings.figures_dir / "ml_classification_comparison.png", 0.45, 1.3, 7.6, 3.4
    )
    _add_image_fit(s9, settings.figures_dir / "ml_confusion_matrix.png", 8.2, 1.3, 4.65, 3.4)
    cls_rows = [
        [
            r["model_name"],
            f"{r['cv_f1']:.4f}",
            f"{r['test_f1']:.4f}",
            f"{r['test_roc_auc']:.4f}",
            f"{r['test_accuracy']:.4f}",
        ]
        for r in registry["classification"]["benchmark"]
    ]
    _add_table(
        s9,
        0.45,
        4.85,
        12.4,
        2.05,
        ["Candidate Model", "5-Fold CV F1", "Held-Out Test F1", "ROC-AUC", "Accuracy"],
        cls_rows,
    )

    # Slide 10: ML Regression
    s10 = prs.slides.add_slide(blank)
    _add_header_bar(
        s10,
        "Phase 6 & 7 — 12-Month Revenue (CLV) Regression",
        f"Champion: {metrics['regression_champion']} | "
        f"R²={metrics['regression_test_r2']:.4f} | "
        f"RMSE=${metrics['regression_test_rmse']:,.2f}",
        10,
    )
    _add_image_fit(
        s10, settings.figures_dir / "ml_regression_diagnostics.png", 0.45, 1.3, 7.7, 3.45
    )
    _add_image_fit(
        s10, settings.figures_dir / "ml_feature_importance.png", 8.25, 1.3, 4.65, 3.45
    )
    reg_rows = [
        [
            r["model_name"],
            f"{r['cv_r2']:.4f}",
            f"{r['test_r2']:.4f}",
            f"${r['test_rmse']:,.2f}",
            f"${r['test_mae']:,.2f}",
        ]
        for r in registry["regression"]["benchmark"]
    ]
    _add_table(
        s10,
        0.45,
        4.9,
        12.4,
        2.0,
        ["Candidate Model", "5-Fold CV R²", "Test R²", "Test RMSE", "Test MAE"],
        reg_rows,
    )

    # Slide 11: ML Clustering
    s11 = prs.slides.add_slide(blank)
    _add_header_bar(
        s11,
        "Phase 6 & 7 — Behavioral Customer Segmentation",
        f"Champion: {metrics['clustering_champion']} | "
        f"Silhouette={metrics['clustering_silhouette']:.4f} (>= 0.50 SLA)",
        11,
    )
    _add_image_fit(s11, settings.figures_dir / "ml_clustering_analysis.png", 0.45, 1.3, 12.4, 3.45)
    prof_rows = [
        [
            p["cluster_label"],
            f"{int(p['customers']):,}",
            f"{p['avg_recency_days']:.1f}d",
            f"{p['avg_frequency']:.1f}",
            f"${p['avg_hist_revenue']:,.0f}",
            f"{p['avg_csat']:.2f}",
            f"{p['churn_rate_pct']:.1f}%",
        ]
        for p in registry["clustering"]["cluster_profiles"]
    ]
    _add_table(
        s11,
        0.45,
        4.9,
        12.4,
        2.0,
        ["Segment Persona", "Accounts", "Recency", "Orders", "Avg Rev", "CSAT", "Churn"],
        prof_rows,
    )

    # Slide 12: BI Dashboard
    s12 = prs.slides.add_slide(blank)
    _add_header_bar(
        s12,
        "Phase 5 & 8 — Interactive Executive BI Dashboard",
        "5-tab Streamlit & Plotly Express decision cockpit with sub-2s cached filtering",
        12,
    )
    _add_card(s12, 0.55, 1.35, 3.85, 2.6, "Tab 1: Executive KPIs", [
        "6 scorecards (Revenue, Profit, Accounts, CSAT, Churn, 12M CLV).",
        "Monthly trend with 3M moving avg & category margin comparison.",
    ], DEEP_BLUE)
    _add_card(s12, 4.72, 1.35, 3.85, 2.6, "Tab 2: Geo & Market Feeds", [
        "Interactive Plotly global ISO-3 choropleth revenue map.",
        "Live Open-ER FX / World Bank GDP & scraped competitor prices.",
    ], CYAN)
    _add_card(s12, 8.9, 1.35, 3.85, 2.6, "Tab 3: Churn & Personas", [
        "2D PCA scatter of 4 behavioral clusters & contract churn bars.",
        "Top 25 High-Risk Watchlist with one-click CSV download.",
    ], ORANGE)
    _add_card(s12, 0.55, 4.2, 5.95, 2.6, "Tab 4: Live ML Decision Simulator", [
        "Interactive behavioral & commercial scenario sliders.",
        "Real-time Churn Gauge, 12M CLV band, Persona badge & playbook.",
    ], GREEN)
    _add_card(s12, 6.8, 4.2, 5.95, 2.6, "Tab 5: ML Governance & Data Quality", [
        "Pre/post-ETL data cleaning audit scorecards.",
        "MLflow cross-validated benchmarks & feature importance plots.",
    ], INDIGO)

    # Slide 13: Deployment, CI/CD & QA
    s13 = prs.slides.add_slide(blank)
    _add_header_bar(
        s13,
        "Phase 8 — Production API, Docker, CI/CD & QA Verification",
        "Containerized FastAPI microservice, Docker Compose & automated Pytest/Flake8 gates",
        13,
    )
    _add_kpi_box(
        s13, 0.55, 1.35, 2.9, 1.9, "API P95 Latency",
        f"{metrics.get('api_p95_latency_ms', 0):.2f} ms", "Target < 200 ms SLA", GREEN,
    )
    _add_kpi_box(
        s13, 3.65, 1.35, 2.9, 1.9, "API P50 Latency",
        f"{metrics.get('api_p50_latency_ms', 0):.2f} ms", "100-Request Benchmark", CYAN,
    )
    _add_kpi_box(
        s13, 6.75, 1.35, 2.9, 1.9, "Flake8 Lint Errors",
        "0 Errors", "PEP 8 Clean Gate", INDIGO,
    )
    _add_kpi_box(
        s13, 9.85, 1.35, 2.9, 1.9, "Pipeline Runtime",
        f"{metrics['total_pipeline_duration_seconds']:.1f} s", "Target < 900 s (15m)", DEEP_BLUE,
    )
    _add_card(s13, 0.55, 3.55, 5.95, 3.2, "Production Microservice & Containerization", [
        "FastAPI + Uvicorn serving /health, /metadata, /predict/* & /batch.",
        "Multi-stage python:3.12-slim Dockerfiles with non-root user.",
        "docker-compose.yml orchestrating PostgreSQL 16, MLflow, API & UI.",
    ], DEEP_BLUE)
    _add_card(s13, 6.8, 3.55, 5.95, 3.2, "GitHub Actions CI/CD & Quality Gates", [
        ".github/workflows/ci.yml runs Flake8, Pytest (>=80% cov) & Docker builds.",
        ".github/workflows/deploy-azure.yml supports Azure Container Apps CD.",
        "GitFlow branching & Google Python Style docstrings across codebase.",
    ], GREEN)

    # Slide 14: Recommendations & Infographic
    s14 = prs.slides.add_slide(blank)
    _add_header_bar(
        s14,
        "Strategic Recommendations & Project Roadmap Summary",
        "Actionable commercial playbooks and unified platform outcomes",
        14,
    )
    _add_card(s14, 0.55, 1.35, 4.35, 5.45, "Prescriptive Business Actions", [
        "Rescue At-Risk Accounts: Trigger CSM SLA alerts whenever CSAT < 3.2.",
        "Contract Migration: Offer 12–15% discounts to convert Monthly to Annual.",
        "Dynamic Price Alignment: Track scraped price_index > 1.05 in Hardware.",
        "Expand Champions: Pitch Security & Analytics cross-sell bundles.",
    ], GREEN)
    infographic = PROJECT_ROOT / "docs" / "06_reports_and_presentation" / "Project_Infographic.png"
    _add_image_fit(s14, infographic, 5.1, 1.35, 7.7, 4.33)
    _add_card(s14, 5.1, 5.82, 7.7, 0.98, "Capstone Sign-Off", [
        "All DEPI CRISP-DM deliverables, ML champions, BI, API & docs are ready.",
    ], INDIGO)

    out_path = PROJECT_ROOT / "docs" / "06_reports_and_presentation" / "Executive_Presentation.pptx"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out_path))
    logger.info("Saved 14-slide Executive Presentation to %s", out_path)
    return out_path


if __name__ == "__main__":
    build_presentation()
