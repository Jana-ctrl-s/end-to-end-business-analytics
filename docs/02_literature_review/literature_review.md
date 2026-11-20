# Literature Review & Technical Benchmark Survey

**Project:** End-to-End Business Analytics Decision Platform  
**DEPI Milestone:** M2 — Literature & Tech Review  

---

## 1. Survey of Modern Enterprise Analytics Architectures

Modern commercial data platforms have converged around decoupled **Lakehouse / Analytical Warehouse** patterns separating:
1. **Multi-Source Ingestion Connectors:** Relational CDC/SQL extraction paired with resilient HTTP REST connectors and HTML web scrapers implementing exponential backoff and local caching to tolerate upstream rate limits.
2. **Contract-Driven ETL (Data Quality Gates):** Libraries such as **Pydantic v2** enforce strict schema typing and domain bounds immediately after deduplication, imputation, and outlier clamping, preventing silent downstream model drift.
3. **Unified Feature Staging (Customer 360):** Point-in-time historical feature aggregation (anchoring observation cutoffs before target horizons) prevents temporal data leakage—a critical failure mode documented extensively in applied churn literature (Verbeke et al., 2012).

---

## 2. Machine Learning Benchmarks Across Core Business Tasks

| Task Domain | Benchmark Literature Consensus | Algorithms Evaluated in Platform | Selection Rationale |
|---|---|---|---|
| **Customer Churn Prediction (Classification)** | Gradient-boosted decision trees (`XGBoost`, `LightGBM`) consistently outperform linear baselines on heterogeneous tabular RFM + service-interaction features, while `LogisticRegression` serves as an interpretable linear benchmark. | LogisticRegression, RandomForest, XGBoost, LightGBM | Balanced F1-score, ROC-AUC, and feature attribution across non-linear interactions (CSAT × Contract × Recency). |
| **Customer Lifetime Value / Revenue Forecasting (Regression)** | Tree ensembles capture non-linear spend momentum and retention multipliers substantially better than linear regression (`Ridge`) or mean (`Dummy`) baselines. | DummyRegressor, Ridge, RandomForest, XGBoost, LightGBM | Strict comparison against both Dummy & Ridge baselines using RMSE, MAE, and $R^2$. |
| **Customer Segmentation (Clustering)** | Standard-scaled RFM + engagement matrices partitioned via `KMeans`, `GaussianMixture`, or `AgglomerativeClustering` produce compact, interpretable commercial personas when validated by Silhouette and Davies-Bouldin indices. | KMeans (`k=2..7` scan + `k=4`), GMM, Agglomerative | Quantitative Silhouette (`>= 0.50`) + PCA visual separability + actionable persona mapping. |

---

## 3. BI Dashboard & Production Serving Design Principles

- **Executive BI Design (Few, 2013):** Top-level KPI scorecards must sit above comparative drill-downs and interactive geographic views (`Plotly Choropleth`), backed by aggressive data/resource caching (`@st.cache_data`, `@st.cache_resource`) to satisfy `< 2.0 s` interactive filter latency.
- **MLOps & Microservice Serving:** Tracking experiments via **MLflow** provides full lineage from hyperparameters to serialized `.joblib` champions, while **FastAPI + Uvicorn** delivers async Pydantic-validated JSON scoring well below the `< 200 ms` P95 latency SLA, packaged cleanly via multi-stage `python:3.12-slim` Docker containers.

---

## 4. Academic & Supervisor Feedback Alignment

Per DEPI Capstone Evaluation Guidelines:
- **Reproducibility:** Global random seed (`RANDOM_STATE = 42`), pinned `requirements.txt`, and executed Jupyter notebooks (`nbconvert --execute`).
- **Engineering Rigor:** Modular OOP/functional design, Google Python Style docstrings, Flake8 zero-error linting, and `>= 80%` automated Pytest coverage enforced in GitHub Actions CI/CD.
- **Suggested Enhancements Tracked:** Future iterations can add Kafka streaming ingestion, automated SHAP per-customer waterfall explanations, and scheduled MLflow drift retraining.
