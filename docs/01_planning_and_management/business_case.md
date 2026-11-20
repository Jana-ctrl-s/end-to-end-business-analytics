# Business Case & Problem Formulation

**Project:** End-to-End Business Analytics Decision Platform (*NovaMetrics Commerce*)  
**Initiative:** Digital Egypt Pioneers Initiative (DEPI) — AI & Data Science Track  
**Methodology:** CRISP-DM Phase 1 (Business Understanding)

---

## 1. Executive Context & Problem Statement

Commercial enterprises generate high-velocity operational signals across disparate systems: relational transaction databases, customer support ticketing logs, external macroeconomic/FX feeds, and competitive market pricing portals. Without a unified analytical pipeline:

1. **Data Silos & Schema Fragmentation:** Finance, Sales, Operations, and Support teams query disconnected exports, creating metric discrepancies and multi-day reconciliation delays.
2. **Lagging Analytical Velocity:** Manual spreadsheet compilation restricts leadership to retrospective monthly reviews rather than interactive, near-real-time decision intelligence.
3. **Absence of Predictive Foresight:** Reporting explains *what happened* (descriptive BI) without predicting *what will happen* (customer attrition risk, 12-month revenue trajectory) or recommending *how to intervene*.
4. **Unquantified Operational Drivers:** Management lacks rigorous statistical and machine-learning attribution linking CSAT degradation, support escalations, contract commitment, and competitive pricing pressure to churn and revenue contraction.

---

## 2. Target Stakeholders & Analytical Questions

| Stakeholder Role | Primary Decision Need | Key Platform Interface |
|---|---|---|
| **Executive Leadership (C-Suite, VP Sales/Ops)** | Monitor portfolio revenue, profit margin, churn exposure, and 12-month CLV forecast by region | Streamlit Executive KPIs & Geographic Tabs; Executive Deck |
| **Business & Operations Managers** | Identify at-risk high-value accounts, compare regional churn hotspots, and deploy retention offers | Churn Drivers & Segments Tab; High-Risk Watchlist CSV; Decision Simulator |
| **Data Analysts & BI Teams** | Query clean, normalized 3NF/warehouse tables and reproducible SQL views without manual cleaning | `analytics_warehouse.db`, `sql/views.sql`, Jupyter Notebooks |
| **Software & Integration Engineers** | Embed automated real-time churn, CLV, and segment scoring inside CRM and ERP workflows | Containerized FastAPI REST Microservice (`/api/v1/predict/*`) |

### Core Analytical Questions Answered
1. Which macro-regions, product categories, and customer segments generate the highest net profit margin versus highest churn attrition?
2. How strongly do CSAT scores, support ticket escalations, delivery delays, and contract lock-in terms drive forward customer churn?
3. What is the projected next-12-month revenue (CLV) per customer after accounting for spend momentum and macroeconomic GDP/FX conditions?
4. What natural behavioral customer personas exist across RFM + support engagement dimensions?
5. How do external competitive pricing gaps affect segment retention and category margin?

---

## 3. Measurable Success Criteria & Cost-Benefit Justification

| Objective Dimension | Success Criterion (KPI Target) | Business Impact |
|---|---|---|
| **Multi-Source Ingestion** | 100% automated SQL + REST API + BeautifulSoup extraction | Eliminates manual CSV preparation |
| **ETL & Governance** | Post-cleaning schema error rate `< 0.1%`; runtime `< 15 min` | Single source of truth across units |
| **Interactive BI** | Dashboard filter-to-render latency `< 2.0 s` | Reduces reporting latency by `> 75%` |
| **Churn Classification** | Cross-validated & Test F1-Score `>= 0.82` | Targets proactive retention at highest-ROI accounts |
| **CLV Regression** | Test `R² >= 0.80` and RMSE strictly `<` baseline | Supports accurate quarterly revenue budgeting |
| **Behavioral Clustering** | Silhouette Score `>= 0.50` across actionable personas | Enables tailored lifecycle campaigns |
| **Production API & QA** | FastAPI P95 latency `< 200 ms`; Pytest coverage `>= 80%`; `0` Flake8 errors | Enterprise-grade reliability and CI/CD readiness |

### Economic Cost-Benefit Summary
- **Implementation Cost:** Zero proprietary licensing overhead (100% open-source Python, PostgreSQL/SQLite, Scikit-Learn, XGBoost, LightGBM, MLflow, FastAPI, Streamlit, Docker).
- **Expected Return:** Reducing annual churn by even 3–5 percentage points among high-CLV *At-Risk High-Friction* and *Mid-Market* accounts preserves recurring revenue while eliminating >75% of manual analyst reporting hours.
