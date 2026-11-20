"""Render the 2560x1440 DEPI Infographic and System Design PNG diagrams via headless Chrome."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from src.config import PROJECT_ROOT, get_logger

logger = get_logger(__name__)

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]


def _find_browser() -> str:
    """Locate Chrome or Edge binary for deterministic high-DPI HTML screenshot rendering."""
    for path in CHROME_CANDIDATES:
        if Path(path).exists():
            return path
    for cmd in ("chrome", "msedge"):
        resolved = shutil.which(cmd)
        if resolved:
            return resolved
    raise FileNotFoundError("Neither Chrome nor Edge browser found for diagram rendering.")


def _render_html_to_png(html: str, out_path: Path, width: int, height: int) -> None:
    """Render standalone HTML/CSS/SVG page to a PNG screenshot at exact pixel size."""
    out_path = out_path.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_html = out_path.with_suffix(".tmp.html")
    tmp_html.write_text(html, encoding="utf-8")
    browser = _find_browser()
    cmd = [
        browser,
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--force-device-scale-factor=1",
        f"--window-size={width},{height}",
        f"--screenshot={out_path}",
        tmp_html.as_uri(),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    tmp_html.unlink(missing_ok=True)
    logger.info("Rendered %s (%dx%d)", out_path.name, width, height)


def build_infographic_html() -> str:
    """Build executive 16:9 (2560x1440) DEPI Roadmap Infographic HTML."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    width: 2560px; height: 1440px; overflow: hidden;
    font-family: 'Segoe UI', 'Inter', Arial, sans-serif;
    background: linear-gradient(135deg, #F8FAFC 0%, #EEF2FF 55%, #ECFEFF 100%);
    color: #0F172A;
    padding: 36px 52px;
    display: flex; flex-direction: column; justify-content: space-between;
  }
  /* Header ~8% height (~115px) */
  .header {
    height: 112px;
    display: flex; align-items: center; justify-content: space-between;
    background: linear-gradient(90deg, #0F2A4A 0%, #1E3A8A 62%, #4F46E5 100%);
    border-radius: 20px; padding: 0 38px; color: #FFFFFF;
    box-shadow: 0 12px 30px rgba(15, 42, 74, 0.18);
  }
  .brand { display: flex; align-items: center; gap: 22px; }
  .depi-mark {
    background: rgba(255,255,255,0.14); border: 2px solid #06B6D4;
    border-radius: 14px; padding: 10px 20px; text-align: center;
  }
  .depi-mark .abbr { font-size: 28px; font-weight: 800; letter-spacing: 2px; color: #FFFFFF; line-height: 1; }
  .depi-mark .sub { font-size: 11px; letter-spacing: 0.8px; color: #A5F3FC; margin-top: 3px; text-transform: uppercase; }
  .brand-meta .init { font-size: 15px; color: #CBD5E1; font-weight: 600; }
  .brand-meta .track { font-size: 20px; color: #38BDF8; font-weight: 700; }
  .title-block { text-align: center; }
  .title-block h1 { font-size: 38px; font-weight: 800; letter-spacing: -0.5px; }
  .title-block p { font-size: 17px; color: #E2E8F0; margin-top: 4px; }
  .kpi-pill {
    background: rgba(16, 185, 129, 0.18); border: 1.5px solid #10B981;
    border-radius: 14px; padding: 10px 20px; text-align: right;
  }
  .kpi-pill .lbl { font-size: 12px; text-transform: uppercase; color: #A7F3D0; letter-spacing: 1px; }
  .kpi-pill .val { font-size: 22px; font-weight: 800; color: #FFFFFF; }

  /* Row 1: Left-to-Right CRISP-DM Roadmap */
  .section-label {
    font-size: 16px; font-weight: 800; text-transform: uppercase; letter-spacing: 1.5px;
    color: #0F2A4A; margin-bottom: 10px; display: flex; align-items: center; gap: 10px;
  }
  .section-label span.dot { width: 10px; height: 10px; border-radius: 50%; background: #6366F1; display: inline-block; }
  .roadmap-row {
    display: grid;
    grid-template-columns: 1fr 36px 1fr 36px 1fr 36px 1fr 36px 1fr 36px 1fr;
    align-items: stretch; gap: 4px; height: 245px;
  }
  .arrow-col { display: flex; align-items: center; justify-content: center; }
  .rm-card {
    background: rgba(255,255,255,0.88);
    backdrop-filter: blur(8px);
    border-radius: 18px; padding: 20px 20px;
    border: 1.5px solid #E2E8F0;
    box-shadow: 0 8px 24px rgba(15, 42, 74, 0.07);
    display: flex; flex-direction: column; justify-content: space-between;
    border-top: 6px solid #0F2A4A;
  }
  .rm-card.c2 { border-top-color: #6366F1; }
  .rm-card.c3 { border-top-color: #06B6D4; }
  .rm-card.c4 { border-top-color: #F59E0B; }
  .rm-card.c5 { border-top-color: #10B981; }
  .rm-card.c6 { border-top-color: #0F2A4A; }
  .rm-top { display: flex; align-items: center; gap: 14px; }
  .icon-box {
    width: 50px; height: 50px; border-radius: 14px;
    display: flex; align-items: center; justify-content: center;
    background: #EFF6FF; flex-shrink: 0;
  }
  .rm-card.c2 .icon-box { background: #EEF2FF; }
  .rm-card.c3 .icon-box { background: #ECFEFF; }
  .rm-card.c4 .icon-box { background: #FFFBEB; }
  .rm-card.c5 .icon-box { background: #ECFDF5; }
  .rm-title { font-size: 21px; font-weight: 800; color: #0F2A4A; line-height: 1.15; }
  .rm-step { font-size: 12px; font-weight: 700; color: #64748B; text-transform: uppercase; letter-spacing: 0.8px; }
  .kw-list { list-style: none; display: flex; flex-direction: column; gap: 8px; margin-top: 10px; }
  .kw-list li {
    font-size: 16.5px; font-weight: 600; color: #334155;
    padding-left: 16px; position: relative;
  }
  .kw-list li::before {
    content: ""; position: absolute; left: 0; top: 8px;
    width: 7px; height: 7px; border-radius: 50%; background: #06B6D4;
  }

  /* Row 2: 3-Column Core (System Architecture | AI/ML Engine | Tech Stack + Timeline) */
  .middle-grid {
    display: grid; grid-template-columns: 1.25fr 1.15fr 1.0fr; gap: 24px; height: 730px;
  }
  .panel {
    background: rgba(255,255,255,0.92); border-radius: 22px; padding: 24px 28px;
    border: 1.5px solid #E2E8F0; box-shadow: 0 10px 28px rgba(15, 42, 74, 0.08);
    display: flex; flex-direction: column; justify-content: space-between;
  }
  .panel-title {
    font-size: 22px; font-weight: 800; color: #0F2A4A;
    padding-bottom: 10px; border-bottom: 2px solid #F1F5F9;
    display: flex; align-items: center; justify-content: space-between;
  }
  .panel-tag { font-size: 13px; background: #EEF2FF; color: #4F46E5; padding: 4px 12px; border-radius: 999px; font-weight: 700; }

  /* Architecture Flow */
  .arch-flow { display: flex; flex-direction: column; gap: 14px; flex: 1; justify-content: center; }
  .arch-layer {
    display: flex; align-items: center; justify-content: space-between;
    padding: 18px 22px; border-radius: 16px; border: 1.5px solid #CBD5E1;
    background: linear-gradient(90deg, #F8FAFC 0%, #FFFFFF 100%);
  }
  .arch-layer.l1 { border-left: 8px solid #0F2A4A; }
  .arch-layer.l2 { border-left: 8px solid #06B6D4; }
  .arch-layer.l3 { border-left: 8px solid #6366F1; }
  .arch-layer.l4 { border-left: 8px solid #10B981; }
  .arch-name { font-size: 19px; font-weight: 800; color: #0F2A4A; }
  .arch-sub { font-size: 15px; color: #475569; font-weight: 600; margin-top: 3px; }
  .arch-chips { display: flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end; max-width: 440px; }
  .chip {
    background: #EFF6FF; color: #1E3A8A; border: 1px solid #BFDBFE;
    padding: 5px 12px; border-radius: 8px; font-size: 14px; font-weight: 700;
  }
  .arch-conn { text-align: center; color: #6366F1; font-weight: 900; font-size: 18px; line-height: 0.7; }

  /* AI/ML Components */
  .ai-grid { display: flex; flex-direction: column; gap: 16px; flex: 1; justify-content: center; }
  .ai-card {
    border-radius: 16px; padding: 18px 22px;
    background: linear-gradient(135deg, #F8FAFC 0%, #EEF2FF 100%);
    border: 1.5px solid #C7D2FE; display: flex; align-items: center; justify-content: space-between;
  }
  .ai-card.reg { background: linear-gradient(135deg, #F8FAFC 0%, #ECFEFF 100%); border-color: #A5F3FC; }
  .ai-card.clu { background: linear-gradient(135deg, #F8FAFC 0%, #ECFDF5 100%); border-color: #A7F3D0; }
  .ai-left h3 { font-size: 20px; font-weight: 800; color: #0F2A4A; }
  .ai-left p { font-size: 15px; color: #475569; font-weight: 600; margin-top: 4px; }
  .ai-kpi {
    text-align: right; background: #FFFFFF; padding: 10px 16px; border-radius: 12px;
    border: 1px solid #E2E8F0; min-width: 155px;
  }
  .ai-kpi .t { font-size: 12px; text-transform: uppercase; color: #64748B; font-weight: 700; }
  .ai-kpi .v { font-size: 23px; font-weight: 800; color: #10B981; }
  .mlops-bar {
    background: #0F2A4A; color: #FFFFFF; border-radius: 14px; padding: 14px 20px;
    display: flex; justify-content: space-between; align-items: center; font-size: 16px; font-weight: 700;
  }
  .mlops-bar span { color: #38BDF8; }

  /* Tech Stack + Timeline */
  .badges-wrap { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 8px; }
  .badge {
    padding: 9px 15px; border-radius: 10px; font-size: 15.5px; font-weight: 700;
    background: #F1F5F9; color: #0F2A4A; border: 1.5px solid #CBD5E1;
  }
  .badge.pri { background: #0F2A4A; color: #FFFFFF; border-color: #0F2A4A; }
  .badge.sec { background: #6366F1; color: #FFFFFF; border-color: #6366F1; }
  .badge.acc { background: #06B6D4; color: #FFFFFF; border-color: #06B6D4; }
  .badge.suc { background: #10B981; color: #FFFFFF; border-color: #10B981; }
  .badge.hi  { background: #F59E0B; color: #FFFFFF; border-color: #F59E0B; }

  .timeline-box { margin-top: 12px; display: flex; flex-direction: column; gap: 12px; }
  .tl-item {
    display: flex; align-items: center; gap: 14px; padding: 10px 14px;
    border-radius: 12px; background: #F8FAFC; border: 1px solid #E2E8F0;
  }
  .tl-wk {
    background: #0F2A4A; color: #FFFFFF; font-weight: 800; font-size: 14px;
    padding: 6px 12px; border-radius: 8px; min-width: 78px; text-align: center;
  }
  .tl-txt { font-size: 16px; font-weight: 700; color: #1E293B; }
  .tl-sub { font-size: 13.5px; color: #64748B; font-weight: 600; }

  /* Bottom Outcomes Bar */
  .outcomes-bar {
    height: 110px;
    background: linear-gradient(90deg, #0F2A4A 0%, #1E293B 100%);
    border-radius: 18px; padding: 0 34px; color: #FFFFFF;
    display: flex; align-items: center; justify-content: space-between;
    box-shadow: 0 10px 26px rgba(15, 42, 74, 0.16);
  }
  .out-title { font-size: 21px; font-weight: 800; color: #38BDF8; text-transform: uppercase; letter-spacing: 1px; }
  .out-items { display: flex; gap: 26px; align-items: center; }
  .out-item {
    display: flex; align-items: center; gap: 10px;
    background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.16);
    padding: 12px 20px; border-radius: 12px; font-size: 18px; font-weight: 700;
  }
  .chk {
    width: 26px; height: 26px; border-radius: 50%; background: #10B981; color: #FFFFFF;
    display: flex; align-items: center; justify-content: center; font-size: 15px; font-weight: 900;
  }
</style>
</head>
<body>
  <!-- TOP DEPI BRANDING & TITLE -->
  <header class="header">
    <div class="brand">
      <div class="depi-mark">
        <div class="abbr">DEPI</div>
        <div class="sub">MCIT Egypt</div>
      </div>
      <div class="brand-meta">
        <div class="init">Digital Egypt Pioneers Initiative</div>
        <div class="track">Track: AI &amp; Data Science</div>
      </div>
    </div>
    <div class="title-block">
      <h1>End-to-End Business Analytics Decision Platform</h1>
      <p>Unified Multi-Source ETL, Executive BI, Predictive ML Engine &amp; Containerized FastAPI Microservice</p>
    </div>
    <div class="kpi-pill">
      <div class="lbl">Methodology</div>
      <div class="val">CRISP-DM + Agile</div>
    </div>
  </header>

  <!-- LEFT-TO-RIGHT ROADMAP -->
  <div>
    <div class="section-label"><span class="dot"></span>End-to-End CRISP-DM Execution Roadmap</div>
    <section class="roadmap-row">
      <div class="rm-card c1">
        <div class="rm-top">
          <div class="icon-box">
            <svg width="28" height="28" fill="none" stroke="#0F2A4A" stroke-width="2.2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M12 8v4l3 3"/></svg>
          </div>
          <div><div class="rm-step">Phase 1</div><div class="rm-title">Business Problem</div></div>
        </div>
        <ul class="kw-list">
          <li>Data Silos &amp; Latency</li>
          <li>Zero Predictive Foresight</li>
          <li>Unquantified Churn Drivers</li>
        </ul>
      </div>
      <div class="arrow-col"><svg width="28" height="28" fill="none" stroke="#6366F1" stroke-width="3" viewBox="0 0 24 24"><path d="M5 12h14M13 6l6 6-6 6"/></svg></div>

      <div class="rm-card c2">
        <div class="rm-top">
          <div class="icon-box">
            <svg width="28" height="28" fill="none" stroke="#6366F1" stroke-width="2.2" viewBox="0 0 24 24"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5M3 12c0 1.66 4 3 9 3s9-1.34 9-3"/></svg>
          </div>
          <div><div class="rm-step">Phase 2</div><div class="rm-title">Data Collection</div></div>
        </div>
        <ul class="kw-list">
          <li>SQL Relational DB</li>
          <li>FX &amp; GDP REST APIs</li>
          <li>BeautifulSoup Scraper</li>
        </ul>
      </div>
      <div class="arrow-col"><svg width="28" height="28" fill="none" stroke="#06B6D4" stroke-width="3" viewBox="0 0 24 24"><path d="M5 12h14M13 6l6 6-6 6"/></svg></div>

      <div class="rm-card c3">
        <div class="rm-top">
          <div class="icon-box">
            <svg width="28" height="28" fill="none" stroke="#06B6D4" stroke-width="2.2" viewBox="0 0 24 24"><path d="M3 6h18M7 12h10M10 18h4"/></svg>
          </div>
          <div><div class="rm-step">Phase 3</div><div class="rm-title">Automated ETL</div></div>
        </div>
        <ul class="kw-list">
          <li>Deduplication &amp; Imputing</li>
          <li>Outlier Clamping</li>
          <li>Pydantic Schema (&lt;0.1%)</li>
        </ul>
      </div>
      <div class="arrow-col"><svg width="28" height="28" fill="none" stroke="#F59E0B" stroke-width="3" viewBox="0 0 24 24"><path d="M5 12h14M13 6l6 6-6 6"/></svg></div>

      <div class="rm-card c4">
        <div class="rm-top">
          <div class="icon-box">
            <svg width="28" height="28" fill="none" stroke="#F59E0B" stroke-width="2.2" viewBox="0 0 24 24"><path d="M3 3v18h18"/><path d="M7 14l4-4 4 3 5-6"/></svg>
          </div>
          <div><div class="rm-step">Phase 4–5</div><div class="rm-title">EDA &amp; BI Suite</div></div>
        </div>
        <ul class="kw-list">
          <li>SciPy Hypothesis Tests</li>
          <li>Plotly Choropleth Maps</li>
          <li>Streamlit KPI Filters</li>
        </ul>
      </div>
      <div class="arrow-col"><svg width="28" height="28" fill="none" stroke="#10B981" stroke-width="3" viewBox="0 0 24 24"><path d="M5 12h14M13 6l6 6-6 6"/></svg></div>

      <div class="rm-card c5">
        <div class="rm-top">
          <div class="icon-box">
            <svg width="28" height="28" fill="none" stroke="#10B981" stroke-width="2.2" viewBox="0 0 24 24"><path d="M12 2a4 4 0 0 1 4 4v2h2a3 3 0 0 1 0 6h-2v2a4 4 0 0 1-8 0v-2H6a3 3 0 0 1 0-6h2V6a4 4 0 0 1 4-4z"/></svg>
          </div>
          <div><div class="rm-step">Phase 6–7</div><div class="rm-title">ML &amp; Evaluation</div></div>
        </div>
        <ul class="kw-list">
          <li>Churn, CLV &amp; Clustering</li>
          <li>5-Fold Cross-Validation</li>
          <li>MLflow Run Tracking</li>
        </ul>
      </div>
      <div class="arrow-col"><svg width="28" height="28" fill="none" stroke="#0F2A4A" stroke-width="3" viewBox="0 0 24 24"><path d="M5 12h14M13 6l6 6-6 6"/></svg></div>

      <div class="rm-card c6">
        <div class="rm-top">
          <div class="icon-box">
            <svg width="28" height="28" fill="none" stroke="#0F2A4A" stroke-width="2.2" viewBox="0 0 24 24"><rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/></svg>
          </div>
          <div><div class="rm-step">Phase 8–9</div><div class="rm-title">Deployment &amp; QA</div></div>
        </div>
        <ul class="kw-list">
          <li>FastAPI (&lt;200ms P95)</li>
          <li>Docker Multi-Container</li>
          <li>GitHub Actions CI/CD</li>
        </ul>
      </div>
    </section>
  </div>

  <!-- MIDDLE GRID: ARCHITECTURE | AI/ML COMPONENTS | TECH STACK + TIMELINE -->
  <section class="middle-grid">
    <!-- Panel 1: 4-Layer Architecture -->
    <div class="panel">
      <div class="panel-title">
        <span>4-Layer System Architecture</span>
        <span class="panel-tag">Decoupled &amp; Containerized</span>
      </div>
      <div class="arch-flow">
        <div class="arch-layer l1">
          <div>
            <div class="arch-name">1. Data Acquisition Layer</div>
            <div class="arch-sub">Multi-source connectors + SQLite cache</div>
          </div>
          <div class="arch-chips">
            <span class="chip">PostgreSQL / SQLite</span>
            <span class="chip">REST APIs</span>
            <span class="chip">BeautifulSoup4</span>
          </div>
        </div>
        <div class="arch-conn">&#8595;</div>
        <div class="arch-layer l2">
          <div>
            <div class="arch-name">2. Engineering &amp; Staging Layer</div>
            <div class="arch-sub">Cleaning, imputation &amp; Customer 360</div>
          </div>
          <div class="arch-chips">
            <span class="chip">Pandas / NumPy</span>
            <span class="chip">Pydantic v2</span>
            <span class="chip">SQL Views</span>
          </div>
        </div>
        <div class="arch-conn">&#8595;</div>
        <div class="arch-layer l3">
          <div>
            <div class="arch-name">3. Predictive ML &amp; MLOps Layer</div>
            <div class="arch-sub">Training, CV tuning &amp; model registry</div>
          </div>
          <div class="arch-chips">
            <span class="chip">Scikit-Learn</span>
            <span class="chip">XGBoost / LightGBM</span>
            <span class="chip">MLflow</span>
          </div>
        </div>
        <div class="arch-conn">&#8595;</div>
        <div class="arch-layer l4">
          <div>
            <div class="arch-name">4. Serving &amp; Decision Layer</div>
            <div class="arch-sub">Real-time inference &amp; executive UI</div>
          </div>
          <div class="arch-chips">
            <span class="chip">FastAPI / Uvicorn</span>
            <span class="chip">Streamlit / Plotly</span>
            <span class="chip">Docker</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Panel 2: AI & ML Components -->
    <div class="panel">
      <div class="panel-title">
        <span>AI &amp; Machine Learning Engine</span>
        <span class="panel-tag">Verified KPI Targets</span>
      </div>
      <div class="ai-grid">
        <div class="ai-card">
          <div class="ai-left">
            <h3>Customer Churn Prediction</h3>
            <p>LogReg &bull; RandomForest &bull; XGBoost &bull; LightGBM</p>
            <p>Stratified 5-Fold CV + Risk Flags</p>
          </div>
          <div class="ai-kpi">
            <div class="t">Target Metric</div>
            <div class="v">F1 &ge; 0.82</div>
          </div>
        </div>
        <div class="ai-card reg">
          <div class="ai-left">
            <h3>12M Revenue / CLV Forecasting</h3>
            <p>Dummy Baseline &bull; Ridge &bull; RF &bull; XGB &bull; LGBM</p>
            <p>Forward Spend + 80% Confidence Band</p>
          </div>
          <div class="ai-kpi">
            <div class="t">Target Metric</div>
            <div class="v">R&sup2; &ge; 0.80</div>
          </div>
        </div>
        <div class="ai-card clu">
          <div class="ai-left">
            <h3>Behavioral Segmentation</h3>
            <p>KMeans (k=2..7) &bull; GMM &bull; Agglomerative</p>
            <p>4 Personas + 2D PCA Projection</p>
          </div>
          <div class="ai-kpi">
            <div class="t">Target Metric</div>
            <div class="v">Sil &ge; 0.50</div>
          </div>
        </div>
        <div class="mlops-bar">
          <div>MLflow Registry &amp; Prescriptive Actions</div>
          <span>API P95 &lt; 200 ms</span>
        </div>
      </div>
    </div>

    <!-- Panel 3: Tech Stack & Timeline -->
    <div class="panel">
      <div>
        <div class="panel-title">
          <span>Technology Stack</span>
          <span class="panel-tag">Open-Source</span>
        </div>
        <div class="badges-wrap">
          <span class="badge pri">Python 3.12</span>
          <span class="badge sec">FastAPI</span>
          <span class="badge acc">Streamlit</span>
          <span class="badge acc">Plotly</span>
          <span class="badge pri">PostgreSQL</span>
          <span class="badge">SQLAlchemy</span>
          <span class="badge">Pandas</span>
          <span class="badge">NumPy</span>
          <span class="badge suc">scikit-learn</span>
          <span class="badge suc">XGBoost</span>
          <span class="badge suc">LightGBM</span>
          <span class="badge sec">MLflow</span>
          <span class="badge">BeautifulSoup4</span>
          <span class="badge">Pydantic</span>
          <span class="badge hi">Docker</span>
          <span class="badge hi">GitHub Actions</span>
          <span class="badge">Pytest &amp; Flake8</span>
        </div>
      </div>

      <div>
        <div class="panel-title" style="margin-top: 8px;">
          <span>Development Timeline</span>
          <span class="panel-tag">9 Weeks (Oct–Dec 2026)</span>
        </div>
        <div class="timeline-box">
          <div class="tl-item">
            <div class="tl-wk">W1–W2</div>
            <div><div class="tl-txt">Planning, Literature &amp; SRS</div><div class="tl-sub">Proposal, Gantt, RACI, Use Cases</div></div>
          </div>
          <div class="tl-item">
            <div class="tl-wk">W3–W5</div>
            <div><div class="tl-txt">System Design &amp; Data Pipelines</div><div class="tl-sub">ERD, DFD, SQL, API, Scraper, ETL</div></div>
          </div>
          <div class="tl-item">
            <div class="tl-wk">W6–W7</div>
            <div><div class="tl-txt">EDA, Dashboard &amp; ML Modeling</div><div class="tl-sub">Notebooks, Streamlit BI, MLflow</div></div>
          </div>
          <div class="tl-item">
            <div class="tl-wk">W8–W9</div>
            <div><div class="tl-txt">FastAPI, Docker, QA &amp; Demo</div><div class="tl-sub">Pytest (&ge;80% Cov), CI/CD, Deck</div></div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- PROJECT OUTCOMES BAR -->
  <footer class="outcomes-bar">
    <div class="out-title">Project Outcomes</div>
    <div class="out-items">
      <div class="out-item"><span class="chk">&#10003;</span>Working System</div>
      <div class="out-item"><span class="chk">&#10003;</span>Executive BI Dashboard</div>
      <div class="out-item"><span class="chk">&#10003;</span>3 Champion ML Models</div>
      <div class="out-item"><span class="chk">&#10003;</span>Containerized REST API</div>
      <div class="out-item"><span class="chk">&#10003;</span>CI/CD &amp; Full Docs</div>
    </div>
  </footer>
</body>
</html>"""


def build_system_architecture_html() -> str:
    """Build System Architecture Diagram HTML (1600x900)."""
    return """<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
* { box-sizing: border-box; }
body { width:1600px; height:900px; overflow:hidden; margin:0; padding:34px 40px; font-family:'Segoe UI',Arial,sans-serif; background:#F8FAFC; color:#0F172A; display:flex; flex-direction:column; justify-content:space-between; }
h1 { font-size:28px; color:#0F2A4A; margin:0 0 6px 0; }
.sub { color:#475569; font-size:15px; margin-bottom:14px; }
.grid { display:grid; grid-template-columns:1fr 42px 1fr 42px 1fr 42px 1fr; align-items:stretch; flex:1; }
.col { background:#FFFFFF; border:2px solid #CBD5E1; border-radius:18px; padding:20px; display:flex; flex-direction:column; gap:14px; box-shadow:0 8px 20px rgba(15,42,74,0.06); border-top:8px solid #0F2A4A; }
.col.c2 { border-top-color:#06B6D4; } .col.c3 { border-top-color:#6366F1; } .col.c4 { border-top-color:#10B981; }
.col h2 { margin:0; font-size:19px; color:#0F2A4A; }
.box { background:#F1F5F9; border:1px solid #CBD5E1; border-radius:12px; padding:13px; flex:1; display:flex; flex-direction:column; justify-content:center; }
.box h3 { margin:0 0 5px 0; font-size:15.5px; color:#1E3A8A; }
.box p { margin:0; font-size:13.5px; color:#334155; line-height:1.4; }
.arr { display:flex; align-items:center; justify-content:center; font-size:30px; font-weight:900; color:#6366F1; }
.foot { background:#0F2A4A; color:#E2E8F0; border-radius:12px; padding:14px 28px; display:flex; justify-content:space-between; font-size:14px; font-weight:600; margin-top:16px; }
</style></head><body>
<div><h1>System Architecture — 4-Layer Decoupled Analytics Platform</h1><div class="sub">NovaMetrics End-to-End Business Analytics Decision Platform (DEPI Capstone)</div></div>
<div class="grid">
  <div class="col">
    <h2>1. Acquisition Layer</h2>
    <div class="box"><h3>Relational SQL Store</h3><p>PostgreSQL / SQLite operational star-schema: customers, products, regions, orders, tickets.</p></div>
    <div class="box"><h3>External REST APIs</h3><p>Open-ER FX exchange rates &amp; World Bank GDP indicators with exponential retry &amp; SQLite cache.</p></div>
    <div class="box"><h3>Web Scraper</h3><p>BeautifulSoup4 competitive catalog benchmark scraper with offline HTML snapshot fallback.</p></div>
  </div>
  <div class="arr">&#10132;</div>
  <div class="col c2">
    <h2>2. Data Engineering</h2>
    <div class="box"><h3>Automated Cleaning</h3><p>Business-key deduplication, canonical string casing, outlier clamping, group-median imputation.</p></div>
    <div class="box"><h3>Pydantic Validation</h3><p>Strict row-level schema contracts enforcing &lt;0.1% post-cleaning error SLA.</p></div>
    <div class="box"><h3>Analytical Warehouse</h3><p>Leak-free Customer 360 feature matrix (cutoff 2025-12-31) + 5 SQL analytical views.</p></div>
  </div>
  <div class="arr">&#10132;</div>
  <div class="col c3">
    <h2>3. ML &amp; Governance</h2>
    <div class="box"><h3>Churn Classification</h3><p>LogReg, RandomForest, XGBoost, LightGBM (5-Fold CV, F1 &ge; 0.82).</p></div>
    <div class="box"><h3>12M CLV Regression</h3><p>Dummy Baseline vs Ridge, RF, XGBoost, LightGBM (R&sup2; &ge; 0.80).</p></div>
    <div class="box"><h3>Segmentation &amp; MLflow</h3><p>KMeans / GMM / Agglomerative (Silhouette &ge; 0.50) + MLflow experiment registry.</p></div>
  </div>
  <div class="arr">&#10132;</div>
  <div class="col c4">
    <h2>4. Serving &amp; DevOps</h2>
    <div class="box"><h3>FastAPI Microservice</h3><p>Async REST endpoints (/predict/churn, /revenue, /segment, /customer-360, /batch), P95 &lt; 200ms.</p></div>
    <div class="box"><h3>Streamlit BI Dashboard</h3><p>5-tab interactive executive cockpit with Plotly maps, cohort charts &amp; live ML simulator.</p></div>
    <div class="box"><h3>Docker &amp; CI/CD</h3><p>Multi-container Compose + GitHub Actions (Flake8, Pytest &ge;80% coverage, Docker builds).</p></div>
  </div>
</div>
<div class="foot"><span>Cross-Cutting Quality: Flake8 Static Linting</span><span>Pytest Automated Suite (&ge;80% Coverage)</span><span>Docker Multi-Stage Images</span><span>GitFlow Version Control</span></div>
</body></html>"""


def build_erd_html() -> str:
    """Build Entity-Relationship Diagram HTML (1600x900)."""
    return """<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
body { width:1600px; height:900px; margin:0; padding:32px; font-family:'Segoe UI',Arial,sans-serif; background:#F8FAFC; color:#0F172A; }
h1 { font-size:27px; color:#0F2A4A; margin:0 0 6px 0; }
.sub { color:#475569; font-size:15px; margin-bottom:20px; }
.canvas { position:relative; width:1536px; height:760px; background:#FFFFFF; border:2px solid #E2E8F0; border-radius:18px; }
.tbl { position:absolute; width:295px; background:#FFFFFF; border:2px solid #0F2A4A; border-radius:12px; overflow:hidden; box-shadow:0 6px 16px rgba(15,42,74,0.08); }
.tbl.ext { border-color:#06B6D4; } .tbl.stg { border-color:#10B981; } .tbl.fact { border-color:#6366F1; }
.th { background:#0F2A4A; color:#FFFFFF; padding:8px 14px; font-weight:800; font-size:15px; }
.tbl.ext .th { background:#06B6D4; } .tbl.stg .th { background:#10B981; } .tbl.fact .th { background:#6366F1; }
.tb { padding:10px 14px; font-size:13px; line-height:1.45; font-family:Consolas,monospace; }
.pk { color:#D97706; font-weight:700; } .fk { color:#2563EB; font-weight:700; }
</style></head><body>
<h1>Entity-Relationship Diagram (ERD) — Operational 3NF &amp; Analytical Warehouse</h1>
<div class="sub">Normalized relational star/snowflake schema integrating operational SQL tables, external API/scraper feeds, and Customer 360 staging</div>
<div class="canvas">
  <svg width="1536" height="760" style="position:absolute;top:0;left:0;">
    <line x1="340" y1="150" x2="430" y2="150" stroke="#475569" stroke-width="2.5"/>
    <line x1="725" y1="150" x2="820" y2="150" stroke="#475569" stroke-width="2.5"/>
    <line x1="577" y1="260" x2="577" y2="380" stroke="#475569" stroke-width="2.5"/>
    <line x1="725" y1="490" x2="820" y2="490" stroke="#475569" stroke-width="2.5"/>
    <line x1="1115" y1="160" x2="1200" y2="160" stroke="#475569" stroke-width="2.5"/>
    <line x1="1115" y1="470" x2="1200" y2="470" stroke="#10B981" stroke-width="2.5" stroke-dasharray="6,4"/>
    <line x1="340" y1="530" x2="430" y2="530" stroke="#06B6D4" stroke-width="2.5" stroke-dasharray="6,4"/>
  </svg>
  <div class="tbl" style="left:45px; top:45px;"><div class="th">dim_regions (12)</div><div class="tb"><span class="pk">PK region_id INT</span><br>macro_region VARCHAR<br>country_code CHAR(3) UQ<br>country_name VARCHAR<br>currency_code CHAR(3)<br>latitude / longitude FLOAT</div></div>
  <div class="tbl" style="left:430px; top:45px;"><div class="th">dim_customers (4,000)</div><div class="tb"><span class="pk">PK customer_id INT</span><br>customer_code VARCHAR UQ<br>segment VARCHAR<br>contract_type VARCHAR<br>acquisition_channel VARCHAR<br><span class="fk">FK region_id INT</span><br>signup_date DATE</div></div>
  <div class="tbl fact" style="left:820px; top:35px;"><div class="th">fact_orders (~28K)</div><div class="tb"><span class="pk">PK order_id INT</span><br>order_code VARCHAR<br><span class="fk">FK customer_id INT</span><br><span class="fk">FK product_id INT</span><br><span class="fk">FK region_id INT</span><br>order_date DATE<br>gross_revenue_usd NUMERIC<br>net_profit_usd NUMERIC<br>delivery_days / status</div></div>
  <div class="tbl" style="left:1200px; top:45px;"><div class="th">dim_products (60)</div><div class="tb"><span class="pk">PK product_id INT</span><br>sku VARCHAR UQ<br>product_name VARCHAR<br>category VARCHAR<br>unit_cost_usd NUMERIC<br>list_price_usd NUMERIC<br>stock_quantity INT</div></div>
  <div class="tbl fact" style="left:430px; top:380px;"><div class="th">fact_customer_interactions (~10K)</div><div class="tb"><span class="pk">PK interaction_id INT</span><br>ticket_code VARCHAR<br><span class="fk">FK customer_id INT</span><br>interaction_date DATE<br>channel / issue_category<br>resolution_hours FLOAT<br>csat_score / nps_score<br>escalated INT</div></div>
  <div class="tbl ext" style="left:45px; top:430px;"><div class="th">ext_macro_indicators (API)</div><div class="tb"><span class="pk">PK country_code CHAR(3)</span><br>currency_code CHAR(3)<br>fx_rate_to_usd FLOAT<br>gdp_growth_pct FLOAT<br>source_provider VARCHAR</div></div>
  <div class="tbl fact" style="left:820px; top:390px;"><div class="th">customer_future_outcomes</div><div class="tb"><span class="pk">PK/FK customer_id INT</span><br>observation_cutoff DATE<br>is_churned INT (0/1)<br>next_12m_revenue_usd NUMERIC</div></div>
  <div class="tbl stg" style="left:1200px; top:360px;"><div class="th">stg_customer_360 (ML Store)</div><div class="tb"><span class="pk">PK customer_id INT</span><br>RFM &amp; Spend Momentum<br>CSAT / Escalation Metrics<br>Macro GDP &amp; FX Rates<br>competitor_price_index<br>cluster_id / cluster_label<br>is_churned / next_12m_rev</div></div>
</div>
</body></html>"""


def build_dfd_html() -> str:
    """Build Data Flow Diagram (Level 1) HTML (1600x900)."""
    return """<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
body { width:1600px; height:900px; margin:0; padding:36px; font-family:'Segoe UI',Arial,sans-serif; background:#F8FAFC; color:#0F172A; }
h1 { font-size:27px; color:#0F2A4A; margin:0 0 6px 0; }
.sub { color:#475569; font-size:15px; margin-bottom:22px; }
.row { display:grid; grid-template-columns:280px 80px 300px 80px 300px 80px 320px; align-items:center; height:680px; }
.stack { display:flex; flex-direction:column; gap:24px; }
.ext { background:#EFF6FF; border:2px solid #0F2A4A; border-radius:10px; padding:18px; text-align:center; font-weight:700; }
.proc { background:#FFFFFF; border:3px solid #6366F1; border-radius:22px; padding:22px; text-align:center; box-shadow:0 8px 20px rgba(99,102,241,0.12); }
.proc h3 { margin:0 0 8px 0; color:#4F46E5; font-size:18px; }
.proc p { margin:0; font-size:14px; color:#334155; }
.store { background:#ECFDF5; border-top:3px solid #10B981; border-bottom:3px solid #10B981; padding:16px; text-align:center; font-weight:700; }
.arrow { text-align:center; font-size:28px; color:#06B6D4; font-weight:900; }
.arrow span { display:block; font-size:12px; color:#475569; font-weight:600; }
</style></head><body>
<h1>Data Flow Diagram (Level 1 DFD) — Ingestion, ETL, Modeling &amp; Serving</h1>
<div class="sub">End-to-end lineage from external entities through transformation processes and analytical data stores to executive decision consumers</div>
<div class="row">
  <div class="stack">
    <div class="ext">External Entity 1:<br>Operational SQL DB<br><small>(Orders, Customers, Tickets)</small></div>
    <div class="ext">External Entity 2:<br>Open-ER &amp; World Bank API<br><small>(FX Rates &amp; GDP Growth)</small></div>
    <div class="ext">External Entity 3:<br>Public Retail Catalog<br><small>(Competitor Prices via BS4)</small></div>
  </div>
  <div class="arrow">&#10132;<span>Raw Feeds</span></div>
  <div class="stack">
    <div class="proc"><h3>P1: Multi-Source Ingestion</h3><p>SQLAlchemy + Retry HTTP + SQLite Cache + Offline Fallback</p></div>
    <div class="proc"><h3>P2: Automated ETL &amp; DQ</h3><p>Deduplicate, Standardize, Clamp Outliers, Impute, Pydantic Gate (&lt;0.1%)</p></div>
  </div>
  <div class="arrow">&#10132;<span>Clean Tables</span></div>
  <div class="stack">
    <div class="store">D1: Analytics Warehouse<br><small>(analytics_warehouse.db &amp; CSVs)</small></div>
    <div class="proc"><h3>P3: ML Training &amp; MLflow</h3><p>5-Fold CV Benchmarking, Champion Registration &amp; Cluster Scoring</p></div>
    <div class="store">D2: Model Registry<br><small>(.joblib Champions &amp; mlflow.db)</small></div>
  </div>
  <div class="arrow">&#10132;<span>Insights &amp; API</span></div>
  <div class="stack">
    <div class="proc" style="border-color:#10B981;"><h3>P4: Serving Layer</h3><p>FastAPI (/predict/*) &amp; Streamlit BI Dashboard</p></div>
    <div class="ext">Stakeholders:<br>Executives, Ops Managers, Analysts &amp; Integrators</div>
  </div>
</div>
</body></html>"""


def generate_all_visual_diagrams() -> None:
    """Render infographic and all system design diagrams into docs/."""
    infographic_path = (
        PROJECT_ROOT / "docs" / "06_reports_and_presentation" / "Project_Infographic.png"
    )
    diagrams_dir = PROJECT_ROOT / "docs" / "04_system_design" / "diagrams"
    _render_html_to_png(build_infographic_html(), infographic_path, 2560, 1440)
    _render_html_to_png(
        build_system_architecture_html(), diagrams_dir / "system_architecture.png", 1600, 900
    )
    _render_html_to_png(build_erd_html(), diagrams_dir / "erd_schema.png", 1600, 900)
    _render_html_to_png(build_dfd_html(), diagrams_dir / "dfd_pipeline.png", 1600, 900)


if __name__ == "__main__":
    generate_all_visual_diagrams()
