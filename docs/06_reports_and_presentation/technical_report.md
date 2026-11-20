# Technical Architecture, Data Engineering & ML Report

**Platform:** End-to-End Business Analytics Decision Platform (*NovaMetrics Commerce*)  
**DEPI Track:** AI & Data Science  

---

## 1. Multi-Source Data Acquisition & Engineering

### 1.1 Automated Extraction Connectors (`src/ingestion/`)
- **Relational SQL (`sql_connector.py`):** Extracts 6 operational tables (`dim_regions` 12 rows, `dim_products` 60 rows, `dim_customers` 4,000 rows, `fact_orders` 36,554 raw rows, `fact_customer_interactions` 12,338 raw rows, `customer_future_outcomes` 4,000 rows) via SQLAlchemy supporting SQLite and PostgreSQL.
- **External REST APIs (`api_connector.py`):** Fetches live exchange rates across 166 currencies from Open-ER (`https://open.er-api.com/v6/latest/USD`) and national GDP growth rates (`NY.GDP.MKTP.KD.ZG`) from the World Bank REST API with 3x exponential backoff retries (`tenacity`), persistent SQLite caching, and deterministic offline JSON fallback.
- **Web Scraper (`web_scraper.py`):** Scrapes live product catalog pricing, ratings, and stock availability from `https://books.toscrape.com/` via `BeautifulSoup4` + `lxml`, computing normalized `competitor_price_index` benchmarks across all 6 product categories with SQLite caching and offline HTML fallback.

### 1.2 Automated ETL & Data Quality Audit (`src/etl/pipeline.py`)
To eliminate temporal leakage, all behavioral features (`recency_days`, `order_frequency`, `hist_total_revenue_usd`, `recent_90d_revenue_usd`, `spend_momentum_ratio`, `avg_csat`, `escalation_rate`) are computed strictly up to `2025-12-31`, while forward targets (`is_churned`, `next_12m_revenue_usd`) belong strictly to the post-cutoff horizon.

| Audit Metric | Verified Value |
|---|---|
| Raw Orders -> Clean Orders | `36,554 -> 36,014` (`540` duplicates removed) |
| Raw Interactions -> Clean Interactions | `12,338 -> 12,156` (`182` duplicates removed) |
| Missing Values Imputed | `3,148` (group-median & categorical mode) |
| Numeric Domain Outliers Clamped | `240` (`delivery_days = 999`, negative shipping, extreme resolution hours) |
| Casing & Whitespace Standardized | `1,582` labels |
| Pydantic v2 Records Validated | `52,188` records (`0` validation errors -> **`0.0000%` error rate**) |
| ETL Pipeline Duration | **`11.77 seconds`** |

Cleaned staging tables and 5 analytical views (`vw_executive_kpis`, `vw_monthly_revenue_trends`, `vw_regional_performance`, `vw_product_profitability`, `vw_customer_churn_risk`) are published into `data/processed/analytics_warehouse.db`.

---

## 2. Machine Learning Benchmarks & MLflow Tracking (`src/ml/`)

All experiments were logged to a local SQLite MLflow backend (`mlflow.db`) and exported to `reports/mlflow_experiments_log.csv` using `RANDOM_STATE = 42` and 80/20 held-out splits with 5-fold cross-validation.

### 2.1 Task 1 — Customer Churn Classification (Target: Test F1 `>= 0.82`)

| Model | 5-Fold CV F1 | Test Accuracy | Precision | Recall | Test F1 | ROC-AUC | PR-AUC |
|---|---|---|---|---|---|---|---|
| **LogisticRegression (Champion)** | **0.9671** | **0.9688** | **0.9506** | **0.9839** | **0.9670** | **0.9871** | **0.9801** |
| XGBClassifier | 0.9660 | 0.9675 | 0.9505 | 0.9812 | 0.9656 | 0.9833 | 0.9709 |
| LGBMClassifier | 0.9657 | 0.9675 | 0.9505 | 0.9812 | 0.9656 | 0.9829 | 0.9716 |
| RandomForestClassifier | 0.9644 | 0.9675 | 0.9505 | 0.9812 | 0.9656 | 0.9851 | 0.9712 |

**Selection Rationale:** `LogisticRegression` achieved the highest 5-fold CV F1 (`0.9671`), Test F1 (`0.9670`), and ROC-AUC (`0.9871`) while offering direct linear log-odds interpretability and sub-millisecond scoring latency. Confusion matrix on 800 held-out accounts: `[[409 TN, 19 FP], [6 FN, 366 TP]]`.

### 2.2 Task 2 — Next-12-Month Customer Revenue / CLV Regression (Target: `R² >= 0.80`)

| Model | 5-Fold CV `R²` | Test `R²` | Test RMSE (USD) | Test MAE (USD) |
|---|---|---|---|---|
| **LGBMRegressor (Champion)** | **0.9672** | **0.9781** | **\$2,843.21** | **\$1,387.47** |
| XGBRegressor | 0.9657 | 0.9778 | \$2,862.21 | \$1,330.80 |
| RandomForestRegressor | 0.9652 | 0.9733 | \$3,138.06 | \$1,448.74 |
| RidgeRegression | 0.8934 | 0.9189 | \$5,470.84 | \$3,147.42 |
| DummyBaseline | -0.0018 | -0.0047 | \$19,254.47 | \$13,052.95 |

**Selection Rationale:** `LGBMRegressor` reduced RMSE by **85.2%** relative to `DummyBaseline` (`\$2,843.21` vs `\$19,254.47`) and **48.0%** relative to linear `RidgeRegression`, capturing non-linear retention and tenure interactions cleanly.

### 2.3 Task 3 — Behavioral Customer Segmentation (Target: Silhouette `>= 0.50`)

| Algorithm (`k=4`) | Silhouette Score | Davies-Bouldin | Calinski-Harabasz |
|---|---|---|---|
| **KMeans_k4 (Champion)** | **0.5501** | **0.6495** | **8,949.06** |
| Agglomerative_k4 | 0.5482 | 0.6531 | 8,924.95 |
| GaussianMixture_k4 | 0.5465 | 0.6550 | 8,871.12 |

#### Resulting Customer Personas
- **Enterprise Champions (`867` accounts):** Avg recency `17.11 d`, `13.08` orders, `\$29,178.04` historical revenue, `4.61` CSAT, **`0.12%` churn**.
- **Loyal Growth Mid-Market (`1,232` accounts):** Avg recency `42.69 d`, `8.08` orders, `\$10,476.02` revenue, `4.11` CSAT, **`3.65%` churn**.
- **At-Risk High-Friction (`887` accounts):** Avg recency `99.82 d`, `5.97` orders, `\$6,449.13` revenue, `2.24` CSAT, **`94.02%` churn**.
- **Dormant Price-Sensitive (`1,014` accounts):** Avg recency `244.22 d`, `2.54` orders, `\$1,626.08` revenue, `3.50` CSAT, **`96.65%` churn**.

---

## 3. Error Analysis, Limitations & Serving Latency

- **Classification Error Analysis (`reports/error_analysis.json`):** Only `6` False Negatives and `19` False Positives occurred across `800` test customers. Because False Negatives carry higher revenue loss risk, lowering the operational trigger threshold from `0.50` to `0.42` further protects high-CLV accounts.
- **Segment-Level Regression MAE:** `SMB = \$449.74`, `Mid-Market = \$1,339.79`, `Enterprise = \$2,546.88` (reflecting wider absolute spend dispersion among large enterprise contracts).
- **Known Limitations:** Static observation cutoff (`2025-12-31`) without live clickstream telemetry; annual macro GDP snapshots rather than quarterly high-frequency indices.
- **FastAPI Serving Latency (`scripts/benchmark_api.py`):** Across `100` sequential Customer-360 inference requests: **Mean = `76.52 ms` / P50 = `75.88 ms` / P95 = `110.55 ms` / P99 = `117.41 ms`** (well below `< 200 ms` SLA). *(Note: exact mean is printed in `metrics_summary.json`.)*
