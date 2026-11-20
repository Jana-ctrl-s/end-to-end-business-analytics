# Test Execution & Quality Assurance Report

**Project:** End-to-End Business Analytics Decision Platform  
**DEPI Milestone:** M6 — Testing, Reports & Demo  
**Test Environment:** Python 3.12.14 (`Windows 11 x64`)  

---

## 1. Automated Quality Gate Summary

| Verification Gate | Command Executed | Target Threshold | Verified Result | Status |
|---|---|---|---|---|
| **Flake8 Static Linting** | `python -m flake8 src api dashboard tests scripts` | `0` fatal errors | **`0` errors** | **PASSED** |
| **Pytest Suite** | `python -m pytest --cov=src --cov=api --cov-fail-under=80` | `100%` pass | **`15 / 15 passed`** (`63.70 s`) | **PASSED** |
| **Code Line Coverage** | `Coverage.py` (`src/` + `api/`) | `>= 80.00%` | **`86.45%`** (`1,301 / 1,505` stmts) | **PASSED** |
| **FastAPI Latency SLA** | `python -m scripts.benchmark_api` (`100` reqs) | `P95 < 200.0 ms` | **`P95 = 110.55 ms`** (`P50 = 75.88 ms`) | **PASSED** |
| **Streamlit Smoke Probe** | `python -m streamlit run dashboard/app.py` (`8509`) | HTTP `200` + `ok` | `/_stcore/health = ok`, `/ = 200` | **PASSED** |
| **Jupyter Notebooks** | `python -m scripts.build_notebooks` (`nbconvert`) | `0` execution errors | **3 / 3 notebooks executed** | **PASSED** |

---

## 2. Pytest Coverage Breakdown by Module (`task-356` Output)

| Module | Statements | Missed | Coverage |
|---|---:|---:|---:|
| `api/main.py` | 75 | 5 | **93.33%** |
| `api/schemas.py` | 72 | 0 | **100.00%** |
| `src/config.py` | 59 | 0 | **100.00%** |
| `src/etl/pipeline.py` | 192 | 5 | **97.40%** |
| `src/etl/run_pipeline.py` | 12 | 1 | **91.67%** |
| `src/etl/schemas.py` | 71 | 0 | **100.00%** |
| `src/ingestion/api_connector.py` | 91 | 4 | **95.60%** |
| `src/ingestion/seed_database.py` | 248 | 2 | **99.19%** |
| `src/ingestion/sql_connector.py` | 31 | 1 | **96.77%** |
| `src/ingestion/web_scraper.py` | 103 | 10 | **90.29%** |
| `src/ml/evaluate.py` | 211 | 1 | **99.53%** |
| `src/ml/features.py` | 34 | 0 | **100.00%** |
| `src/ml/predict.py` | 99 | 3 | **96.97%** |
| `src/ml/train.py` | 207 | 172 | **16.91%** *(trained via `scripts/run_all.py`; skipped in unit test if `.joblib` exists)* |
| **TOTAL** | **1,505** | **204** | **86.45%** |

---

## 3. FastAPI Latency Benchmark (`100` Sequential Requests)

- **Endpoint Tested:** `POST /api/v1/predict/customer-360`
- **Mean Latency:** `76.52 ms`
- **P50 (Median) Latency:** `75.88 ms`
- **P95 Latency:** `110.55 ms` (`< 200.0 ms` SLA)
- **P99 Latency:** `117.41 ms`
