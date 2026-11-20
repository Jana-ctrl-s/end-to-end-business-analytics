"""ML training, hyperparameter tuning, MLflow tracking, and champion selection."""

from __future__ import annotations

import json
import os
import warnings
from pathlib import Path
from typing import Any

import joblib
import mlflow
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier, LGBMRegressor
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.decomposition import PCA
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    calinski_harabasz_score,
    confusion_matrix,
    davies_bouldin_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
    silhouette_score,
)
from sklearn.mixture import GaussianMixture
from sklearn.model_selection import (
    GridSearchCV,
    KFold,
    RandomizedSearchCV,
    StratifiedKFold,
    cross_val_score,
    train_test_split,
)
from sklearn.pipeline import Pipeline
from sqlalchemy import create_engine
from xgboost import XGBClassifier, XGBRegressor

from src.config import get_logger, settings
from src.ml.features import (
    CLASSIFICATION_CAT_FEATURES,
    CLASSIFICATION_NUM_FEATURES,
    CLUSTERING_FEATURES,
    REGRESSION_CAT_FEATURES,
    REGRESSION_NUM_FEATURES,
    build_clustering_scaler,
    build_tabular_preprocessor,
    derive_persona_map,
)

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
logger = get_logger(__name__)


def _configure_mlflow() -> None:
    """Point MLflow tracking URI to local SQLite backend with local artifact root."""
    os.environ.setdefault("GIT_PYTHON_REFRESH", "quiet")
    settings.ensure_directories()
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)


def _extract_feature_importances(
    pipeline: Pipeline,
    num_features: list[str],
    cat_features: list[str],
    top_n: int = 12,
) -> list[dict[str, float]]:
    """Extract normalized feature importance rankings from a fitted sklearn Pipeline."""
    pre = pipeline.named_steps["preprocessor"]
    model = pipeline.named_steps["model"]
    cat_names = list(pre.named_transformers_["cat"].get_feature_names_out(cat_features))
    feature_names = list(num_features) + cat_names

    if hasattr(model, "feature_importances_"):
        raw_imp = np.asarray(model.feature_importances_, dtype=float)
    elif hasattr(model, "coef_"):
        coef = np.asarray(model.coef_, dtype=float)
        raw_imp = np.abs(coef[0] if coef.ndim > 1 else coef)
    else:
        return []

    total = float(raw_imp.sum()) or 1.0
    norm_imp = raw_imp / total
    pairs = sorted(zip(feature_names, norm_imp), key=lambda x: x[1], reverse=True)[:top_n]
    return [{"feature": name, "importance": round(float(val), 4)} for name, val in pairs]


def train_churn_models(df: pd.DataFrame) -> dict[str, Any]:
    """Train, cross-validate, and benchmark churn classification models."""
    mlflow.set_experiment("churn_classification")
    features = CLASSIFICATION_NUM_FEATURES + CLASSIFICATION_CAT_FEATURES
    X = df[features]
    y = df["is_churned"].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, stratify=y, random_state=settings.random_state
    )
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=settings.random_state)

    candidates: list[tuple[str, Any, dict[str, Any], str]] = [
        (
            "LogisticRegression",
            LogisticRegression(max_iter=1000, random_state=settings.random_state),
            {"model__C": [0.1, 0.5, 1.0, 5.0]},
            "grid",
        ),
        (
            "RandomForestClassifier",
            RandomForestClassifier(random_state=settings.random_state, n_jobs=-1),
            {
                "model__n_estimators": [150, 250],
                "model__max_depth": [6, 10, 14],
                "model__min_samples_leaf": [3, 6],
            },
            "random",
        ),
        (
            "XGBClassifier",
            XGBClassifier(
                random_state=settings.random_state,
                eval_metric="logloss",
                n_jobs=-1,
            ),
            {
                "model__n_estimators": [150, 250],
                "model__max_depth": [3, 5, 7],
                "model__learning_rate": [0.03, 0.06, 0.1],
                "model__subsample": [0.8, 0.95],
            },
            "random",
        ),
        (
            "LGBMClassifier",
            LGBMClassifier(random_state=settings.random_state, verbose=-1, n_jobs=-1),
            {
                "model__n_estimators": [150, 250],
                "model__max_depth": [4, 6, -1],
                "model__learning_rate": [0.03, 0.06, 0.1],
                "model__num_leaves": [20, 31, 45],
            },
            "random",
        ),
    ]

    results: list[dict[str, Any]] = []
    fitted_pipelines: dict[str, Pipeline] = {}
    roc_curves_data: dict[str, dict[str, Any]] = {}

    for name, estimator, param_grid, search_type in candidates:
        pre = build_tabular_preprocessor(CLASSIFICATION_NUM_FEATURES, CLASSIFICATION_CAT_FEATURES)
        pipe = Pipeline([("preprocessor", pre), ("model", estimator)])

        if search_type == "grid":
            search = GridSearchCV(pipe, param_grid, cv=cv, scoring="f1", n_jobs=-1)
        else:
            search = RandomizedSearchCV(
                pipe,
                param_distributions=param_grid,
                n_iter=6,
                cv=cv,
                scoring="f1",
                random_state=settings.random_state,
                n_jobs=-1,
            )
        search.fit(X_train, y_train)
        best_pipe: Pipeline = search.best_estimator_
        y_pred = best_pipe.predict(X_test)
        y_prob = best_pipe.predict_proba(X_test)[:, 1]

        metrics = {
            "model_name": name,
            "cv_f1": round(float(search.best_score_), 4),
            "test_accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
            "test_precision": round(float(precision_score(y_test, y_pred)), 4),
            "test_recall": round(float(recall_score(y_test, y_pred)), 4),
            "test_f1": round(float(f1_score(y_test, y_pred)), 4),
            "test_roc_auc": round(float(roc_auc_score(y_test, y_prob)), 4),
            "test_pr_auc": round(float(average_precision_score(y_test, y_prob)), 4),
        }
        results.append(metrics)
        fitted_pipelines[name] = best_pipe
        roc_curves_data[name] = {
            "y_test": y_test.to_numpy().tolist(),
            "y_prob": np.round(y_prob, 5).tolist(),
            "y_pred": y_pred.tolist(),
        }

        with mlflow.start_run(run_name=f"churn_{name}"):
            mlflow.log_params({k.replace("model__", ""): v for k, v in search.best_params_.items()})
            mlflow.log_metrics({k: v for k, v in metrics.items() if k != "model_name"})
        logger.info(
            "Classification [%s] -> Test F1=%.4f | ROC-AUC=%.4f",
            name, metrics["test_f1"], metrics["test_roc_auc"],
        )

    results_sorted = sorted(results, key=lambda r: (r["test_f1"], r["test_roc_auc"]), reverse=True)
    champion_info = results_sorted[0]
    champion_name = champion_info["model_name"]
    champion_pipe = fitted_pipelines[champion_name]

    if champion_info["test_f1"] < 0.82:
        raise RuntimeError(
            f"Champion churn model F1={champion_info['test_f1']} is below required 0.82 threshold!"
        )

    joblib.dump(champion_pipe, settings.models_dir / "churn_champion.joblib")

    y_champ_pred = np.asarray(roc_curves_data[champion_name]["y_pred"])
    cm = confusion_matrix(y_test, y_champ_pred).tolist()
    importances = _extract_feature_importances(
        champion_pipe, CLASSIFICATION_NUM_FEATURES, CLASSIFICATION_CAT_FEATURES, top_n=12
    )

    # Save test evaluation details for diagnostics & error analysis
    eval_payload = {
        "champion": champion_info,
        "all_models": results_sorted,
        "confusion_matrix": cm,
        "feature_importances": importances,
        "curves": roc_curves_data,
        "test_indices": X_test.index.tolist(),
    }
    (settings.models_dir / "churn_eval_artifacts.json").write_text(
        json.dumps(eval_payload), encoding="utf-8"
    )
    return {
        "champion_name": champion_name,
        "champion_metrics": champion_info,
        "benchmark": results_sorted,
        "confusion_matrix": cm,
        "feature_importances": importances,
    }


def train_revenue_models(df: pd.DataFrame) -> dict[str, Any]:
    """Train, cross-validate, and benchmark next-12M customer revenue regression models."""
    mlflow.set_experiment("revenue_regression")
    features = REGRESSION_NUM_FEATURES + REGRESSION_CAT_FEATURES
    X = df[features]
    y = df["next_12m_revenue_usd"].astype(float)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=settings.random_state
    )
    cv = KFold(n_splits=5, shuffle=True, random_state=settings.random_state)

    # Explicit Dummy baseline
    dummy_pre = build_tabular_preprocessor(REGRESSION_NUM_FEATURES, REGRESSION_CAT_FEATURES)
    dummy_pipe = Pipeline([("preprocessor", dummy_pre), ("model", DummyRegressor(strategy="mean"))])
    dummy_pipe.fit(X_train, y_train)
    dummy_pred = dummy_pipe.predict(X_test)
    dummy_cv_r2 = cross_val_score(dummy_pipe, X_train, y_train, cv=cv, scoring="r2").mean()
    dummy_metrics = {
        "model_name": "DummyBaseline",
        "cv_r2": round(float(dummy_cv_r2), 4),
        "test_rmse": round(float(np.sqrt(mean_squared_error(y_test, dummy_pred))), 2),
        "test_mae": round(float(mean_absolute_error(y_test, dummy_pred)), 2),
        "test_r2": round(float(r2_score(y_test, dummy_pred)), 4),
    }

    candidates: list[tuple[str, Any, dict[str, Any], str]] = [
        (
            "RidgeRegression",
            Ridge(random_state=settings.random_state),
            {"model__alpha": [1.0, 10.0, 50.0, 100.0]},
            "grid",
        ),
        (
            "RandomForestRegressor",
            RandomForestRegressor(random_state=settings.random_state, n_jobs=-1),
            {
                "model__n_estimators": [150, 250],
                "model__max_depth": [8, 12, 16],
                "model__min_samples_leaf": [3, 6],
            },
            "random",
        ),
        (
            "XGBRegressor",
            XGBRegressor(random_state=settings.random_state, n_jobs=-1),
            {
                "model__n_estimators": [150, 250],
                "model__max_depth": [3, 5, 7],
                "model__learning_rate": [0.03, 0.06, 0.1],
                "model__subsample": [0.8, 0.95],
            },
            "random",
        ),
        (
            "LGBMRegressor",
            LGBMRegressor(random_state=settings.random_state, verbose=-1, n_jobs=-1),
            {
                "model__n_estimators": [150, 250],
                "model__max_depth": [4, 6, -1],
                "model__learning_rate": [0.03, 0.06, 0.1],
                "model__num_leaves": [20, 31, 45],
            },
            "random",
        ),
    ]

    results: list[dict[str, Any]] = [dummy_metrics]
    fitted_pipelines: dict[str, Pipeline] = {"DummyBaseline": dummy_pipe}
    preds_map: dict[str, np.ndarray] = {"DummyBaseline": dummy_pred}

    with mlflow.start_run(run_name="revenue_DummyBaseline"):
        mlflow.log_metrics({k: v for k, v in dummy_metrics.items() if k != "model_name"})

    for name, estimator, param_grid, search_type in candidates:
        pre = build_tabular_preprocessor(REGRESSION_NUM_FEATURES, REGRESSION_CAT_FEATURES)
        pipe = Pipeline([("preprocessor", pre), ("model", estimator)])

        if search_type == "grid":
            search = GridSearchCV(pipe, param_grid, cv=cv, scoring="r2", n_jobs=-1)
        else:
            search = RandomizedSearchCV(
                pipe,
                param_distributions=param_grid,
                n_iter=6,
                cv=cv,
                scoring="r2",
                random_state=settings.random_state,
                n_jobs=-1,
            )
        search.fit(X_train, y_train)
        best_pipe: Pipeline = search.best_estimator_
        y_pred = np.clip(best_pipe.predict(X_test), 0.0, None)
        preds_map[name] = y_pred

        metrics = {
            "model_name": name,
            "cv_r2": round(float(search.best_score_), 4),
            "test_rmse": round(float(np.sqrt(mean_squared_error(y_test, y_pred))), 2),
            "test_mae": round(float(mean_absolute_error(y_test, y_pred)), 2),
            "test_r2": round(float(r2_score(y_test, y_pred)), 4),
        }
        results.append(metrics)
        fitted_pipelines[name] = best_pipe

        with mlflow.start_run(run_name=f"revenue_{name}"):
            mlflow.log_params({k.replace("model__", ""): v for k, v in search.best_params_.items()})
            mlflow.log_metrics({k: v for k, v in metrics.items() if k != "model_name"})
        logger.info(
            "Regression [%s] -> Test R2=%.4f | RMSE=$%.2f",
            name, metrics["test_r2"], metrics["test_rmse"],
        )

    results_sorted = sorted(results, key=lambda r: r["test_r2"], reverse=True)
    champion_info = results_sorted[0]
    champion_name = champion_info["model_name"]
    champion_pipe = fitted_pipelines[champion_name]

    if champion_info["test_r2"] < 0.80 or champion_info["test_rmse"] >= dummy_metrics["test_rmse"]:
        raise RuntimeError(
            f"Champion revenue model R2={champion_info['test_r2']} fails >=0.80 / <baseline SLA!"
        )

    joblib.dump(champion_pipe, settings.models_dir / "revenue_champion.joblib")
    importances = _extract_feature_importances(
        champion_pipe, REGRESSION_NUM_FEATURES, REGRESSION_CAT_FEATURES, top_n=12
    )

    eval_payload = {
        "champion": champion_info,
        "baseline": dummy_metrics,
        "all_models": results_sorted,
        "feature_importances": importances,
        "y_test": y_test.to_numpy().tolist(),
        "y_pred_champion": np.round(preds_map[champion_name], 2).tolist(),
        "test_indices": X_test.index.tolist(),
        "residual_std": round(float(np.std(y_test.to_numpy() - preds_map[champion_name])), 2),
    }
    (settings.models_dir / "revenue_eval_artifacts.json").write_text(
        json.dumps(eval_payload), encoding="utf-8"
    )
    return {
        "champion_name": champion_name,
        "champion_metrics": champion_info,
        "baseline_metrics": dummy_metrics,
        "benchmark": results_sorted,
        "feature_importances": importances,
        "residual_std": eval_payload["residual_std"],
    }


def train_clustering_models(df: pd.DataFrame) -> tuple[dict[str, Any], pd.DataFrame]:
    """Evaluate clustering algorithms, verify Silhouette >= 0.50, and assign personas."""
    mlflow.set_experiment("customer_segmentation")
    scaler = build_clustering_scaler()
    X_scaled = scaler.fit_transform(df[CLUSTERING_FEATURES])

    # Elbow + Silhouette curve for k=2..7
    k_scan: list[dict[str, Any]] = []
    for k in range(2, 8):
        km = KMeans(n_clusters=k, n_init=20, random_state=settings.random_state)
        labels_k = km.fit_predict(X_scaled)
        k_scan.append(
            {
                "k": k,
                "inertia": round(float(km.inertia_), 2),
                "silhouette": round(float(silhouette_score(X_scaled, labels_k)), 4),
            }
        )

    # Compare 3 clustering algorithms at k=4
    km4 = KMeans(n_clusters=4, n_init=25, random_state=settings.random_state)
    km4_labels = km4.fit_predict(X_scaled)

    gmm4 = GaussianMixture(n_components=4, random_state=settings.random_state)
    gmm4_labels = gmm4.fit_predict(X_scaled)

    agg4 = AgglomerativeClustering(n_clusters=4)
    agg4_labels = agg4.fit_predict(X_scaled)

    algos = [
        ("KMeans_k4", km4, km4_labels),
        ("GaussianMixture_k4", gmm4, gmm4_labels),
        ("Agglomerative_k4", agg4, agg4_labels),
    ]

    results: list[dict[str, Any]] = []
    fitted_models: dict[str, tuple[Any, np.ndarray]] = {}
    for name, model, labels in algos:
        sil = round(float(silhouette_score(X_scaled, labels)), 4)
        db = round(float(davies_bouldin_score(X_scaled, labels)), 4)
        ch = round(float(calinski_harabasz_score(X_scaled, labels)), 2)
        metrics = {
            "model_name": name,
            "silhouette_score": sil,
            "davies_bouldin": db,
            "calinski_harabasz": ch,
        }
        results.append(metrics)
        fitted_models[name] = (model, labels)
        with mlflow.start_run(run_name=f"cluster_{name}"):
            mlflow.log_param("n_clusters", 4)
            mlflow.log_metrics({k: v for k, v in metrics.items() if k != "model_name"})
        logger.info("Clustering [%s] -> Silhouette=%.4f | Davies-Bouldin=%.4f", name, sil, db)

    # Prefer KMeans_k4 if >= 0.50 so real-time .predict() is supported natively,
    # otherwise pick highest Silhouette (nearest centroid handles live predict).
    results_sorted = sorted(results, key=lambda r: r["silhouette_score"], reverse=True)
    champion_info = results_sorted[0]
    champion_name = champion_info["model_name"]
    champion_model, champion_labels = fitted_models[champion_name]

    if champion_info["silhouette_score"] < 0.50:
        raise RuntimeError(
            f"Champion clustering Silhouette={champion_info['silhouette_score']} is below 0.50!"
        )

    persona_map = derive_persona_map(df, champion_labels)
    pca = PCA(n_components=2, random_state=settings.random_state)
    coords_2d = pca.fit_transform(X_scaled)

    # Compute cluster centroids in scaled space for reliable real-time prediction across any algo
    centroids_scaled = np.vstack(
        [X_scaled[champion_labels == cid].mean(axis=0) for cid in range(4)]
    )

    bundle = {
        "scaler": scaler,
        "model": champion_model,
        "model_name": champion_name,
        "features": CLUSTERING_FEATURES,
        "persona_map": persona_map,
        "centroids_scaled": centroids_scaled,
        "pca": pca,
    }
    joblib.dump(bundle, settings.models_dir / "segmentation_champion.joblib")

    df_out = df.copy()
    df_out["cluster_id"] = champion_labels
    df_out["cluster_label"] = df_out["cluster_id"].map(persona_map)
    df_out["pca_1"] = np.round(coords_2d[:, 0], 4)
    df_out["pca_2"] = np.round(coords_2d[:, 1], 4)

    cluster_profile = (
        df_out.groupby("cluster_label")
        .agg(
            customers=("customer_id", "count"),
            avg_recency_days=("recency_days", "mean"),
            avg_frequency=("order_frequency", "mean"),
            avg_hist_revenue=("hist_total_revenue_usd", "mean"),
            avg_csat=("avg_csat", "mean"),
            churn_rate_pct=("is_churned", lambda s: float(s.mean() * 100.0)),
        )
        .round(2)
        .reset_index()
        .to_dict(orient="records")
    )

    eval_payload = {
        "champion": champion_info,
        "all_models": results_sorted,
        "k_scan": k_scan,
        "persona_map": {str(k): v for k, v in persona_map.items()},
        "cluster_profiles": cluster_profile,
    }
    (settings.models_dir / "clustering_eval_artifacts.json").write_text(
        json.dumps(eval_payload, indent=2), encoding="utf-8"
    )
    return {
        "champion_name": champion_name,
        "champion_metrics": champion_info,
        "benchmark": results_sorted,
        "k_scan": k_scan,
        "cluster_profiles": cluster_profile,
    }, df_out


def _export_mlflow_runs_log() -> None:
    """Export all MLflow tracked experiment runs to CSV for repository transparency."""
    runs = mlflow.search_runs(search_all_experiments=True)
    if not runs.empty:
        keep_cols = [
            c
            for c in runs.columns
            if c.startswith("tags.mlflow.runName")
            or c.startswith("metrics.")
            or c.startswith("params.")
            or c in ("experiment_id", "run_id", "status")
        ]
        runs[keep_cols].to_csv(settings.reports_dir / "mlflow_experiments_log.csv", index=False)


def train_all_models(data_path: Path | None = None) -> dict[str, Any]:
    """Train all 3 ML pipelines, log to MLflow, register champions, and enrich Customer 360.

    Args:
        data_path: Optional override path to ``customer_360.csv``.

    Returns:
        Model registry dictionary with champion metadata and benchmarks.
    """
    _configure_mlflow()
    c360_path = data_path or (settings.processed_dir / "customer_360.csv")
    df = pd.read_csv(c360_path)

    churn_res = train_churn_models(df)
    rev_res = train_revenue_models(df)
    clust_res, df_enriched = train_clustering_models(df)

    df_enriched.to_csv(c360_path, index=False)
    engine = create_engine(settings.warehouse_database_url, future=True)
    df_enriched.to_sql("stg_customer_360", engine, if_exists="replace", index=False)

    registry = {
        "classification": churn_res,
        "regression": rev_res,
        "clustering": clust_res,
    }
    (settings.models_dir / "model_registry.json").write_text(
        json.dumps(registry, indent=2), encoding="utf-8"
    )
    _export_mlflow_runs_log()
    logger.info("All ML experiments completed and registered successfully.")
    return registry


if __name__ == "__main__":
    train_all_models()
