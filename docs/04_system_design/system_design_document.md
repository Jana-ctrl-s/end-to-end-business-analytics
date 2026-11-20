# System Design Document (SDD)

**Project:** End-to-End Business Analytics Decision Platform (*NovaMetrics Commerce*)  
**DEPI Milestone:** M4 — System Analysis & Design  

---

## 1. Problem Statement, Objectives & Use Case Model

Commercial operations suffer from siloed relational transactions, disconnected external market signals, and lack of predictive churn/revenue visibility. The platform unifies multi-source ingestion, automated ETL governance, interactive BI visualization, and containerized ML scoring.

### 1.1 Use Case Diagram

```mermaid
flowchart LR
    DE["Data Engineer"]
    BA["BI / Data Analyst"]
    OM["Operations Manager"]
    EX["Executive Leadership"]
    SP["Software Integration Partner"]

    subgraph Platform["NovaMetrics Analytics Platform"]
        UC1(["Ingest SQL + REST API + Scraper"])
        UC2(["Run Automated ETL & DQ Gate"])
        UC3(["Explore SQL Views & EDA Notebooks"])
        UC4(["Filter KPI & Geo BI Dashboard"])
        UC5(["Simulate Churn, CLV & Segment"])
        UC6(["Train & Register ML Champions"])
        UC7(["Invoke FastAPI REST Scoring"])
    end

    DE --> UC1
    DE --> UC2
    DE --> UC6
    BA --> UC3
    BA --> UC4
    OM --> UC4
    OM --> UC5
    EX --> UC4
    SP --> UC7
```

### 1.2 Software Architecture Style
The platform follows a **4-Layer Decoupled Microservice + Analytical Warehouse Architecture**:
1. **Data Acquisition Layer:** Connector abstraction (`SQLConnector`, `MacroAPIConnector`, `CompetitorPriceScraper`).
2. **Data Engineering & Transformation Layer:** Pure-Python + Pandas ETL pipeline (`ETLPipeline`) with Pydantic v2 contract enforcement and SQL warehouse staging.
3. **Analytical & Predictive ML Layer:** Scikit-Learn Pipelines + XGBoost + LightGBM tracked via MLflow (`train.py`, `evaluate.py`, `predict.py`).
4. **Serving & Presentation Layer:** Asynchronous **FastAPI** inference microservice paired with a reactive **Streamlit + Plotly** executive dashboard.

![4-Layer System Architecture](diagrams/system_architecture.png)

---

## 2. Database Design & Data Modeling

### 2.1 Entity-Relationship Diagram (ERD)

![Entity-Relationship Diagram](diagrams/erd_schema.png)

```mermaid
erDiagram
    dim_regions ||--o{ dim_customers : "hosts"
    dim_regions ||--o{ fact_orders : "fulfills_in"
    dim_customers ||--o{ fact_orders : "places"
    dim_products ||--o{ fact_orders : "purchased_in"
    dim_customers ||--o{ fact_customer_interactions : "opens"
    dim_customers ||--|| customer_future_outcomes : "evaluated_at_cutoff"
    dim_customers ||--|| stg_customer_360 : "aggregated_into"
```

### 2.2 Logical & Physical Schema & Normalization
- **3NF Operational Layer (`sql/schema.sql`):** `dim_regions`, `dim_products`, `dim_customers`, `fact_orders`, `fact_customer_interactions`, `customer_future_outcomes`. Eliminates transitive dependencies on region currency/coordinates and product SKU metadata.
- **External Enrichment Tables:** `ext_macro_indicators` (country PK) and `ext_competitor_benchmarks` (category PK).
- **Analytical Denormalized Staging:** `stg_orders_clean` and `stg_customer_360` plus 5 pre-indexed BI views (`sql/views.sql`) optimize read performance for Streamlit and ad-hoc SQL reporting.

---

## 3. Data Flow & System Behavior

### 3.1 Context & Level-1 Data Flow Diagram (DFD)

![Level-1 Data Flow Diagram](diagrams/dfd_pipeline.png)

### 3.2 Sequence Diagram — Real-Time Decision Prediction

```mermaid
sequenceDiagram
    actor User as Operations Manager / Client
    participant UI as Streamlit Dashboard
    participant API as FastAPI /predict/customer-360
    participant Pred as AnalyticsPredictor
    participant Models as Champion .joblib Pipelines

    User->>UI: Adjust customer features & click Predict
    UI->>API: POST JSON CustomerFeaturesInput
    API->>API: Validate via Pydantic v2 schema
    API->>Pred: predict_customer_360(payload)
    Pred->>Models: Score Churn, CLV Revenue & Cluster
    Models-->>Pred: Probability, Revenue $, Cluster ID
    Pred-->>API: Risk Tier + Top Drivers + Action
    API-->>UI: HTTP 200 JSON (X-Process-Time-Ms header)
    UI-->>User: Render Gauge, Interval & Retention Playbook
```

### 3.3 Activity Diagram — Automated ETL & Quality Gate

```mermaid
flowchart TD
    A(["Start ETL Run"]) --> B["Extract SQL Tables, FX/GDP APIs & BS4 Catalog"]
    B --> C["Deduplicate Business Keys (order_code, ticket_code)"]
    C --> D["Standardize Casing & Whitespace"]
    D --> E["Clamp Domain Outliers (delivery_days, shipping, resolution)"]
    E --> F["Group-Median & Mode Imputation"]
    F --> G["Build Leak-Free Customer 360 (Cutoff <= 2025-12-31)"]
    G --> H{"Pydantic Error Rate < 0.1%?"}
    H -- Yes --> I["Persist Processed CSVs & SQL Warehouse Views"]
    H -- No --> J(["Abort & Raise Validation Alert"])
    I --> K(["Write data_quality_report.json & Complete"])
```

### 3.4 State Diagram — Customer Account Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Onboarded: Signup & First Order
    Onboarded --> LoyalGrowth: Repeat Orders & CSAT >= 3.8
    LoyalGrowth --> EnterpriseChampion: High Frequency & 2-Year Contract
    LoyalGrowth --> AtRiskHighFriction: CSAT < 3.0 or Escalation Surge
    Onboarded --> DormantSMB: Recency > 165 Days
    AtRiskHighFriction --> LoyalGrowth: Proactive CSM Intervention
    AtRiskHighFriction --> Churned: No Renewal at Cutoff
    DormantSMB --> Churned: Extended Inactivity
```

### 3.5 Class Diagram — Core Python Architecture

```mermaid
classDiagram
    class SQLConnector {
        +str database_url
        +extract_table(table_name) DataFrame
        +extract_all_raw() dict
        +execute_query(query) DataFrame
    }
    class MacroAPIConnector {
        +fetch_macro_indicators(use_cache) DataFrame
    }
    class CompetitorPriceScraper {
        +parse_catalog_html(html) list
        +scrape_competitor_benchmarks(use_cache) DataFrame
    }
    class ETLPipeline {
        +clean_customers(df) tuple
        +clean_orders(df) tuple
        +clean_interactions(df) tuple
        +build_customer_360(...) DataFrame
        +run() DataQualityReport
    }
    class AnalyticsPredictor {
        +predict_churn(payload) dict
        +predict_revenue(payload) dict
        +predict_segment(payload) dict
        +predict_customer_360(payload) dict
        +predict_batch(records) list
    }
    ETLPipeline --> SQLConnector
    ETLPipeline --> MacroAPIConnector
    ETLPipeline --> CompetitorPriceScraper
```

---

## 4. UI/UX Design & Prototyping

### 4.1 Wireframe Layout (Streamlit Executive BI Cockpit)
```
+-----------------------------------------------------------------------------+
| [HEADER] NovaMetrics Enterprise Decision Intelligence Platform               |
+---------------+-------------------------------------------------------------+
| SIDEBAR       | [Tabs]: Executive KPIs | Geo & Market | Churn & Segments |  |
| - Date Range  |         Live ML Simulator | ML Governance & DQ               |
| - Region      +-------------------------------------------------------------+
| - Segment     | [KPI 1]   [KPI 2]   [KPI 3]   [KPI 4]   [KPI 5]   [KPI 6]   |
| - Category    +------------------------------+------------------------------+
|               | Monthly Revenue & Profit     | Category Margin Bar Chart    |
|               | Trend + 3M Moving Average    | (Plotly Horizontal Bar)      |
+---------------+------------------------------+------------------------------+
```

### 4.2 UI/UX Design Guidelines
- **Color Palette:** Deep Blue (`#0F2A4A`) primary headers, Indigo/Purple (`#6366F1`) secondary accents, Cyan (`#06B6D4`) analytical highlights, Amber (`#F59E0B`) caution/trends, Emerald (`#10B981`) positive KPIs, Coral (`#EF4444`) churn alerts on a crisp `#F8FAFC` light surface.
- **Typography & Accessibility:** Clean sans-serif hierarchy, clear KPI deltas, hover tooltips on all Plotly visualizations, and CSV export buttons for operational follow-through.

---

## 5. System Deployment, Integration & API Specification

### 5.1 Technology Stack
- **Backend / ML:** Python 3.12, Pandas, NumPy, SciPy, Scikit-Learn, XGBoost, LightGBM, MLflow, Joblib, Pydantic v2.
- **Database & Scraping:** SQLAlchemy 2.0, PostgreSQL 16 / SQLite, Requests, BeautifulSoup4, Tenacity.
- **Serving & Frontend:** FastAPI, Uvicorn, Streamlit, Plotly Express, Matplotlib, Seaborn.
- **DevOps & Quality:** Docker, Docker Compose, GitHub Actions, Pytest, Coverage.py, Flake8.

### 5.2 Deployment & Component Diagram

```mermaid
flowchart LR
    subgraph Host["Docker Compose / Azure Container Apps"]
        PG[("PostgreSQL 16\n(Port 5432)")]
        MLF["MLflow Tracking UI\n(Port 5000)"]
        API["FastAPI Container\n(Port 8000)"]
        UI["Streamlit BI Container\n(Port 8501)"]
    end
    Client["Browser / External CRM"] --> UI
    Client --> API
    UI --> API
    API --> PG
    API --> MLF
```

### 5.3 REST API Endpoint Summary
| Method | Path | Request Schema | Response Schema | Purpose |
|---|---|---|---|---|
| `GET` | `/health` | — | `HealthResponse` | Liveness & model readiness probe |
| `GET` | `/api/v1/models/metadata` | — | `ModelMetadataResponse` | Champion identifiers & benchmark scores |
| `POST` | `/api/v1/predict/churn` | `CustomerFeaturesInput` | `ChurnPredictionResponse` | Churn probability & risk tier |
| `POST` | `/api/v1/predict/revenue` | `CustomerFeaturesInput` | `RevenuePredictionResponse` | 12M CLV forecast + 80% interval |
| `POST` | `/api/v1/predict/segment` | `CustomerFeaturesInput` | `SegmentPredictionResponse` | Behavioral persona assignment |
| `POST` | `/api/v1/predict/customer-360` | `CustomerFeaturesInput` | `Customer360Response` | Combined prediction + action playbook |
| `POST` | `/api/v1/predict/batch` | `BatchPredictionRequest` | `BatchPredictionResponse` | Vectorized scoring up to 500 records |

### 5.4 Scaling & Deployment Strategy
- Stateless FastAPI workers scale horizontally behind a load balancer (e.g., Azure Container Apps replicas), loading serialized `.joblib` champions once during ASGI lifespan startup for sub-20ms per-request execution.
- Scheduled batch ETL runs update PostgreSQL staging tables and trigger conditional model retraining tracked in MLflow.
