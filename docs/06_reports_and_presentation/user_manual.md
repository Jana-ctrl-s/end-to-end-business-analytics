# End-User & Operator Manual

**Platform:** NovaMetrics End-to-End Business Analytics Decision Platform  
**Version:** 1.0.0  

---

## 1. Prerequisites & Installation

- **Python:** 3.11 or 3.12 (recommended)
- **Optional:** Docker & Docker Compose for containerized multi-service deployment

### Local Environment Setup
```bash
git clone https://github.com/Jana-ctrl-s/end-to-end-business-analytics.git
cd end-to-end-business-analytics

python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

---

## 2. Running the End-to-End Pipeline

Execute data seeding (if `data/raw/enterprise_ops.db` does not exist), multi-source ingestion, automated ETL, ML model training/MLflow logging, and evaluation chart generation:
```bash
python -m scripts.run_all
```
Outputs created:
- Cleaned CSVs & `analytics_warehouse.db` in `data/processed/`
- Trained champion pipelines & `model_registry.json` in `models/`
- `metrics_summary.json`, `error_analysis.json`, and 9 figures in `reports/`

---

## 3. Launching the Interactive BI Dashboard

Start the Streamlit application locally:
```bash
streamlit run dashboard/app.py
```
Open `http://localhost:8501` in your browser.

### Navigating the Dashboard
1. **Sidebar Filters:** Filter all KPIs and charts simultaneously by **Order Date Range**, **Macro-Regions**, **Customer Segments**, and **Product Categories**.
2. **Tab 1 — Executive KPIs & Trends:** Review top-line Gross Revenue, Net Profit, Active Accounts, Avg CSAT, Churn Rate, and Projected 12M CLV alongside monthly trajectories and category margins.
3. **Tab 2 — Geographic & Market Intelligence:** Hover over countries on the interactive global choropleth map and inspect live FX/GDP macro feeds and scraped competitor pricing indices.
4. **Tab 3 — Churn Drivers & Segments:** Explore PCA customer persona clusters, contract/CSAT attrition rates, and download the top 25 High-Risk Watchlist accounts as CSV.
5. **Tab 4 — Live ML Decision Simulator:** Adjust customer sliders (Recency, Orders, CSAT, Escalations, Contract Type) and click **Run ML Decision Prediction** for real-time churn probability, 12M CLV interval, cluster persona, and prescriptive action.
6. **Tab 5 — ML Governance & Data Quality:** Inspect pre/post-ETL data cleaning counts and MLflow cross-validated model leaderboards.

---

## 4. Using the FastAPI Prediction Microservice

Start the API server:
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```
- Interactive Swagger UI: `http://localhost:8000/docs`
- Health Check: `GET http://localhost:8000/health`

### Example `curl` Request (`/api/v1/predict/customer-360`)
```bash
curl -X POST "http://localhost:8000/api/v1/predict/customer-360" \
  -H "Content-Type: application/json" \
  -d '{
    "account_tenure_days": 420,
    "recency_days": 22.0,
    "order_frequency": 9,
    "hist_total_revenue_usd": 14800.0,
    "hist_total_profit_usd": 6200.0,
    "avg_order_value_usd": 1644.44,
    "recent_90d_revenue_usd": 3850.0,
    "spend_momentum_ratio": 1.01,
    "avg_discount_pct": 0.08,
    "avg_delivery_days": 3.4,
    "return_rate": 0.02,
    "support_tickets_count": 2,
    "avg_resolution_hours": 9.5,
    "avg_csat": 4.45,
    "avg_nps": 8.5,
    "escalation_rate": 0.0,
    "gdp_growth_pct": 2.8,
    "fx_rate_to_usd": 1.0,
    "competitor_price_index": 0.98,
    "segment": "Enterprise",
    "contract_type": "Annual",
    "acquisition_channel": "Direct Sales",
    "macro_region": "North America",
    "primary_category": "Cloud Software"
  }'
```

---

## 5. Docker Multi-Service Deployment

Launch PostgreSQL, MLflow Tracking UI, FastAPI, and Streamlit Dashboard together:
```bash
docker compose up --build -d
```
- FastAPI Swagger Docs: `http://localhost:8000/docs`
- Streamlit BI Dashboard: `http://localhost:8501`
- MLflow Experiment UI: `http://localhost:5000`
