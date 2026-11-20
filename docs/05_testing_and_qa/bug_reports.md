# Bug Reports & Issue Resolution Log

**Project:** End-to-End Business Analytics Decision Platform  
**DEPI Milestone:** M6 — Testing & Quality Assurance  

---

| Bug ID | Component / File | Severity | Summary & Root Cause | Resolution & Verification | Status |
|---|---|---|---|---|---|
| **BUG-01** | `requirements.txt` / `.venv` | High | Newly published 2026 wheels (`pydantic-core==2.50.5`, `sqlalchemy==2.1.9`) triggered Windows Smart App Control DLL load blocks (`_pydantic_core`, `_collections_cy`). | Pinned established stable releases (`sqlalchemy==2.0.36`, `pydantic==2.10.6`, `pydantic-core==2.27.2`, `fastapi==0.115.8`, `mlflow==2.20.3`); verified clean import of entire stack. | Resolved |
| **BUG-02** | `src/etl/pipeline.py` | Medium | `stg_customer_360` published to SQL warehouse prior to ML clustering omitted `cluster_id` and `cluster_label`, causing `vw_customer_churn_risk` view references to depend on post-training table replacement. | Initialized default `cluster_id = -1` and `cluster_label = "Unassigned"` inside `build_customer_360()` prior to warehouse publishing. | Resolved |
| **BUG-03** | `src/ingestion/seed_database.py` | High | `Dormant_SMB` archetype had `recency_range = (165, 325)` while customer `tenure_days` could draw `< 170`, causing `numpy.random.Generator.integers` `ValueError: low >= high`. | Computed `min_tenure = max(140, prof["recency_range"][1] + 45)` in `_generate_customers()` and guarded `rec_high` bounds in `_generate_historical_activity()`. | Resolved |
| **BUG-04** | `scripts/generate_infographic_and_diagrams.py` | Low | `system_architecture.png` clipped the right border and footer strip at `1600x900` due to default `box-sizing: content-box` adding padding to viewport width, and `Path.as_uri()` rejected relative paths. | Added `* { box-sizing: border-box; }` + `overflow: hidden` in `build_system_architecture_html()` and resolved `out_path.resolve()` before `tmp_html.as_uri()`. Visually verified clean render. | Resolved |
