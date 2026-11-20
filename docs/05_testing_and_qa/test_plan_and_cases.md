# Test Plan & Verification Test Cases

**Project:** End-to-End Business Analytics Decision Platform  
**DEPI Milestone:** M6 — Testing & Quality Assurance  

---

## 1. Testing Strategy & Quality Gates

1. **Static Code Quality Gate (`Flake8`):** Enforces PEP 8 compliance, unused import detection, and 100-character max line length across `src/`, `api/`, `dashboard/`, `tests/`, and `scripts/` with **0 fatal lint errors**.
2. **Unit & Integration Test Suite (`Pytest + Coverage.py`):** Exercises multi-source connectors (with mocked HTTP failure fallback), ETL cleaning/imputation/validation, ML champion SLA gates, and FastAPI REST endpoints with **`>= 80%` line coverage**.
3. **Performance & SLA Benchmarks:** Verifies end-to-end pipeline completion `< 15 minutes` and FastAPI P95 inference latency `< 200 ms`.
4. **UI Smoke Verification:** Confirms Streamlit BI dashboard boots cleanly and passes `/_stcore/health` HTTP 200 probe.

---

## 2. Test Case Catalog

| Test ID | Suite / File | Scenario Description | Expected Outcome |
|---|---|---|---|
| **TC-01** | `tests/test_ingestion.py` | Extract all 6 raw SQL operational tables & reject unknown table names | Returns exact row counts (`12` regions, `60` products, `4,000` customers); raises `ValueError` on invalid table |
| **TC-02** | `tests/test_ingestion.py` | Parameterized SQL read query filtering MENA markets | Returns `EGY`, `ARE`, `SAU` |
| **TC-03** | `tests/test_ingestion.py` | REST API connector network outage fallback & SQLite cache hit | Falls back to `macro_market_indicators.json` cleanly; subsequent cache hit returns cached values |
| **TC-04** | `tests/test_ingestion.py` | BeautifulSoup catalog parsing & live timeout fallback | Parses 12 HTML cards; falls back to `catalog_snapshot.html` and caches 6 category indices |
| **TC-05** | `tests/test_etl.py` | Order deduplication, casing standardization, outlier clamping & imputation | Removes duplicate `order_code`, fixes `" credit_card "`, clamps `999.0` delivery & `-45.0` shipping |
| **TC-06** | `tests/test_etl.py` | Full ETL Data Quality Report & leak-free Customer 360 | `post_cleaning_error_rate_pct < 0.1%`; `0` nulls in 4,000 Customer 360 rows |
| **TC-07** | `tests/test_ml.py` | Champion ML benchmark KPI verification | Classification `F1 >= 0.82`; Regression `R² >= 0.80` & `RMSE < Baseline`; Clustering `Silhouette >= 0.50` |
| **TC-08** | `tests/test_ml.py` | Single, high-friction risk comparison & batch scoring | High-friction profile yields higher churn probability; empty batch returns `[]` |
| **TC-09** | `tests/test_ml.py` | Evaluation visualization export completeness | All 9 PNG charts exist in `reports/figures/` with size `> 10 KB` |
| **TC-10** | `tests/test_api.py` | FastAPI `/`, `/health`, `/api/v1/models/metadata` | HTTP 200 with `models_loaded = True` and compliant KPIs |
| **TC-11** | `tests/test_api.py` | All 5 `/api/v1/predict/*` endpoints + invalid input rejection | HTTP 200 with `X-Process-Time-Ms`; HTTP 422 when `avg_csat = 99.0` |
| **TC-12** | `tests/test_api.py` | API latency SLA benchmark (`P95 < 200 ms`) | P95 latency strictly `< 200.0 ms` |
