# Software Requirements Specification (SRS) & Use Case Catalog

**Project:** End-to-End Business Analytics Decision Platform  
**DEPI Milestone:** M3 — Requirements Gathering  

---

## 1. Stakeholder Analysis

| Stakeholder | Role & Interest | Technical Proficiency | Frequency of Use |
|---|---|---|---|
| **VP of Sales / C-Suite** | Strategic KPI tracking, regional revenue, churn financial impact | Non-technical | Weekly / Monthly |
| **Operations & CSM Managers** | At-risk watchlist triage, support escalation remediation, retention simulation | Moderate | Daily |
| **Data Analysts / Scientists** | SQL warehouse views, statistical EDA notebooks, MLflow benchmarks | High | Daily |
| **Backend / DevOps Engineers** | FastAPI REST endpoints, Docker deployment, CI/CD test automation | High | Continuous |

---

## 2. User Stories & Use Cases

| ID | Actor | User Story | Acceptance Criterion |
|---|---|---|---|
| **UC-01** | Data Engineer | As a Data Engineer, I want automated extraction from SQL, REST APIs, and web scraping with offline fallbacks so pipelines never fail due to transient API outages. | Connectors retry with backoff, cache in SQLite, and fall back to local fixtures seamlessly. |
| **UC-02** | Data Analyst | As a Data Analyst, I want automated deduplication, imputation, outlier clamping, and Pydantic validation so warehouse tables are trustworthy. | Post-cleaning Pydantic schema error rate `< 0.1%` and `data_quality_report.json` generated. |
| **UC-03** | Executive | As an Executive, I want interactive KPI scorecards, revenue trends, and a global choropleth map filtered by date, region, segment, and category. | Streamlit dashboard updates filters smoothly under 2 seconds. |
| **UC-04** | Operations Manager | As an Ops Manager, I want to simulate a customer's behavioral attributes and receive real-time churn risk, 12M CLV, persona, and prescriptive action. | Decision Simulator & `/api/v1/predict/customer-360` return risk tier, CLV interval, and action. |
| **UC-05** | Integration Partner | As an Engineer, I want containerized REST endpoints with OpenAPI/Swagger documentation and `< 200 ms` P95 latency for CRM integration. | FastAPI `/docs`, `/health`, and batch/single inference endpoints pass latency & schema tests. |

---

## 3. Functional Requirements

- **FR-01 (Multi-Source Ingestion):** Extract relational tables (`dim_regions`, `dim_products`, `dim_customers`, `fact_orders`, `fact_customer_interactions`, `customer_future_outcomes`) via SQLAlchemy, FX & World Bank GDP growth via REST APIs, and competitive pricing benchmarks via BeautifulSoup4.
- **FR-02 (ETL & Warehouse Staging):** Deduplicate business keys, normalize categorical strings, clamp out-of-range numerics, impute missing values, construct leak-free `customer_360.csv` (cutoff `2025-12-31`), and publish SQL views (`vw_executive_kpis`, `vw_monthly_revenue_trends`, `vw_regional_performance`, `vw_product_profitability`, `vw_customer_churn_risk`).
- **FR-03 (ML Training & Registry):** Train and cross-validate multiple candidate models across Classification, Regression, and Clustering; track experiments in MLflow; persist champion `.joblib` pipelines and `model_registry.json`.
- **FR-04 (Interactive BI Dashboard):** Provide 5 Streamlit tabs covering Executive KPIs, Geographic/External Intelligence, Churn Drivers & Segments (with CSV export), Live ML Decision Simulator, and ML Governance/DQ Audit.
- **FR-05 (Inference REST API):** Expose `/health`, `/api/v1/models/metadata`, `/api/v1/predict/churn`, `/api/v1/predict/revenue`, `/api/v1/predict/segment`, `/api/v1/predict/customer-360`, and `/api/v1/predict/batch`.

---

## 4. Non-Functional Requirements

| Category | Requirement Specification | Verification Method |
|---|---|---|
| **Performance** | FastAPI P95 response latency `< 200 ms`; full ETL + ML pipeline `< 15 min` | `scripts/benchmark_api.py`, `scripts/run_all.py` |
| **Data Quality** | Post-ETL schema validation error rate `< 0.1%`; zero nulls in ML feature matrix | Pydantic v2 validation & `tests/test_etl.py` |
| **Reliability** | API connectors and scraper support 3x exponential retry, SQLite caching, and offline fallbacks | Unit tests with mocked connection failures |
| **Maintainability** | Modular package layout, Google Python Style docstrings, `0` Flake8 errors, `>= 80%` test coverage | GitHub Actions CI (`flake8`, `pytest --cov`) |
| **Portability** | Reproducible execution via Python 3.12 `.venv` or multi-container `docker-compose.yml` | Dockerfiles & Compose configuration |

---

## 5. Requirements Traceability Matrix

| Requirement | Implementing Module(s) | Verification Test(s) |
|---|---|---|
| FR-01 | `src/ingestion/sql_connector.py`, `api_connector.py`, `web_scraper.py` | `tests/test_ingestion.py` |
| FR-02 | `src/etl/pipeline.py`, `src/etl/schemas.py`, `sql/views.sql` | `tests/test_etl.py` |
| FR-03 | `src/ml/train.py`, `src/ml/evaluate.py`, `src/ml/features.py` | `tests/test_ml.py` |
| FR-04 | `dashboard/app.py` | Streamlit headless HTTP health & render check |
| FR-05 | `api/main.py`, `api/schemas.py`, `src/ml/predict.py` | `tests/test_api.py`, `scripts/benchmark_api.py` |
