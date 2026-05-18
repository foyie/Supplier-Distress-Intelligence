"""
Phase 4 — Risk Modeling Pipeline
Trains two complementary models:
  A) XGBoost classifier: P(distress within 6 months) — outputs probability score
  B) Cox PH survival model: time-to-distress — outputs hazard ratio + C-index

Also runs:
  - SHAP explainability (per-company feature attribution)
  - Ablation study (current features vs forecasted features)
  - MLflow experiment tracking (all runs logged)
  - Full backtest with rolling time-split

Usage:
    python phase4_modeling/train_models.py
    python phase4_modeling/train_models.py --ablation   # run ablation study
"""

import os
import sys
import math
import json
import argparse
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")   # non-interactive backend for server environments
import matplotlib.pyplot as plt
import seaborn as sns

warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "phase1_data"))
PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
MODELS_DIR    = os.path.join(os.path.dirname(__file__), "..", "models")
PLOTS_DIR     = os.path.join(os.path.dirname(__file__), "..", "data", "plots")
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(PLOTS_DIR, exist_ok=True)

import mlflow
import mlflow.sklearn
import mlflow.xgboost

mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000"))


# ─────────────────────────────────────────────────────────
# Feature column sets
# ─────────────────────────────────────────────────────────
# CURRENT_FEATURES = [
#     "headcount", "headcount_mom_pct", "headcount_3m_trend",
#     "job_postings_total", "job_postings_mom_pct",
#     "pct_ops_finance_roles", "pct_senior_roles",
#     "glassdoor_rating", "glassdoor_rating_mom",
#     "news_sentiment_score", "news_volume", "distress_keyword_score",
#     "revenue_qoq_pct", "cash_ratio", "debt_to_equity",
#     "operating_margin", "interest_coverage",
# ]

# FORECAST_FEATURES = [
#     "headcount_forecast",
#     "glassdoor_rating_forecast",
#     "cash_ratio_forecast",
#     "debt_to_equity_forecast",
#     "news_sentiment_score_forecast",
#     "distress_keyword_score_forecast",
#     "pct_ops_finance_roles_forecast",
# ]
CURRENT_FEATURES = [
    "headcount", "headcount_mom_pct", "headcount_3m_trend",
    "job_postings_total", "job_postings_mom_pct",
    "pct_ops_finance_roles", "pct_senior_roles",
    "glassdoor_rating", "glassdoor_rating_mom",
    "news_sentiment_score", "news_volume", "distress_keyword_score",
    "revenue_qoq_pct", "cash_ratio", "debt_to_equity",
    "operating_margin", "interest_coverage",
]

FORECAST_FEATURES = [
    "headcount_forecast",
    "glassdoor_rating_forecast",
    "cash_ratio_forecast",
    "debt_to_equity_forecast",
    "news_sentiment_score_forecast",
    "distress_keyword_score_forecast",
    "pct_ops_finance_roles_forecast",
]

# FEATURE_COLS = CURRENT_FEATURES + FORECAST_FEATURES

ALL_FEATURES = CURRENT_FEATURES + FORECAST_FEATURES


# ─────────────────────────────────────────────────────────
# Data loading
# ─────────────────────────────────────────────────────────
def load_data(use_forecasts: bool = True) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load train/test split. Use forecasted feature matrix if available."""
    if use_forecasts:
        path = os.path.join(PROCESSED_DIR, "feature_matrix_with_forecasts.parquet")
        if not os.path.exists(path):
            print("  ⚠ Forecasted matrix not found, falling back to current features only")
            path = os.path.join(PROCESSED_DIR, "feature_matrix_full.parquet")
    else:
        path = os.path.join(PROCESSED_DIR, "feature_matrix_full.parquet")

    df = pd.read_parquet(path)
    train = df[df["year"] <= 2021].copy()
    test  = df[df["year"].between(2022, 2023)].copy()
    return train, test


def get_feature_cols(df: pd.DataFrame, feature_set: list[str]) -> list[str]:
    """Return only feature columns that actually exist in the DataFrame."""
    return [f for f in feature_set if f in df.columns]


# ─────────────────────────────────────────────────────────
# A: XGBoost Classifier
# ─────────────────────────────────────────────────────────
def train_xgboost(
    train: pd.DataFrame,
    test: pd.DataFrame,
    feature_cols: list[str],
    run_name: str = "xgboost_default"
) -> tuple:
    """
    Train XGBoost binary classifier: label_6m (distress within 6 months).
    Returns: (model, auc_score, feature_importance_df)
    """
    from xgboost import XGBClassifier
    from sklearn.metrics import roc_auc_score, average_precision_score, classification_report
    from sklearn.utils.class_weight import compute_sample_weight
    from imblearn.over_sampling import SMOTE

    X_train = train[feature_cols].fillna(0)
    y_train = train["label_6m"]
    X_test  = test[feature_cols].fillna(0)
    y_test  = test["label_6m"]

    # Handle class imbalance: use SMOTE + scale_pos_weight
    pos_ratio = (y_train == 0).sum() / (y_train == 1).sum()

    with mlflow.start_run(run_name=run_name, nested=True):
        model = XGBClassifier(
            n_estimators       = 300,
            max_depth          = 4,
            learning_rate      = 0.05,
            subsample          = 0.8,
            colsample_bytree   = 0.8,
            scale_pos_weight   = pos_ratio,    # handles class imbalance
            eval_metric        = "auc",
            early_stopping_rounds = 20,
            random_state       = 42,
            n_jobs             = -1,
        )

        model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            verbose=False,
        )

        # Evaluate
        y_prob = model.predict_proba(X_test)[:, 1]
        auc    = roc_auc_score(y_test, y_prob)
        auprc  = average_precision_score(y_test, y_prob)

        # Log to MLflow
        mlflow.log_params({
            "n_estimators":  300,
            "max_depth":     4,
            "learning_rate": 0.05,
            "features_used": len(feature_cols),
        })
        mlflow.log_metrics({"auc": auc, "auprc": auprc})
        mlflow.xgboost.log_model(model, artifact_path="xgboost_model")

        print(f"\n  XGBoost Results [{run_name}]")
        print(f"    AUC:   {auc:.4f}")
        print(f"    AUPRC: {auprc:.4f}")

        # Feature importance
        importance_df = pd.DataFrame({
            "feature":   feature_cols,
            "importance": model.feature_importances_,
        }).sort_values("importance", ascending=False)

        mlflow.log_metric("best_auc", auc)

    return model, auc, importance_df


# ─────────────────────────────────────────────────────────
# B: Cox Proportional Hazards Survival Model
# ─────────────────────────────────────────────────────────
def train_cox_survival(
    train: pd.DataFrame,
    test: pd.DataFrame,
    feature_cols: list[str],
    run_name: str = "cox_ph_default"
) -> tuple:
    """
    Train Cox PH model using scikit-survival.
    Target: (event, duration) where event=1 means distress occurred.
    Returns: (model, c_index)
    """
    from sksurv.linear_model import CoxPHSurvivalAnalysis
    from sksurv.metrics import concordance_index_censored
    import sklearn.preprocessing as pp

    # scikit-survival requires structured array for y
    def make_survival_target(df: pd.DataFrame):
        return np.array(
            [(bool(e), float(d)) for e, d in zip(df["event"], df["duration"])],
            dtype=[("event", "?"), ("duration", "<f8")]
        )

    X_train = train[feature_cols].fillna(0)
    y_train = make_survival_target(train)
    X_test  = test[feature_cols].fillna(0)
    y_test  = make_survival_target(test)

    # Normalize features (Cox PH is sensitive to scale)
    scaler  = pp.StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s  = scaler.transform(X_test)

    with mlflow.start_run(run_name=run_name, nested=True):
        model = CoxPHSurvivalAnalysis(alpha=0.01, ties="efron", n_iter=200)
        model.fit(X_train_s, y_train)

        # C-index (concordance index) — equivalent of AUC for survival
        risk_scores = model.predict(X_test_s)
        events      = y_test["event"]
        durations   = y_test["duration"]
        c_index, *_ = concordance_index_censored(events, durations, risk_scores)

        mlflow.log_metrics({"c_index": c_index})
        mlflow.sklearn.log_model(model, artifact_path="cox_model")

        # Coefficient interpretation
        coef_df = pd.DataFrame({
            "feature": feature_cols,
            "coef":    model.coef_,
            "exp_coef": np.exp(model.coef_),   # hazard ratio
        }).sort_values("exp_coef", ascending=False)

        print(f"\n  Cox PH Results [{run_name}]")
        print(f"    C-index: {c_index:.4f}")
        print("\n    Top hazard factors (exp(coef) > 1 = increases risk):")
        print(coef_df.head(8).to_string(index=False))

    return model, c_index, coef_df


# ─────────────────────────────────────────────────────────
# C: SHAP Explainability
# ─────────────────────────────────────────────────────────
def run_shap_analysis(
    model,
    X_test: pd.DataFrame,
    feature_cols: list[str],
    company_names: pd.Series,
    top_n_companies: int = 5
):
    """
    Compute SHAP values for XGBoost model.
    Saves:
      - Global feature importance bar plot
      - Waterfall charts for top-N riskiest companies
    """
    import shap

    explainer   = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_test[feature_cols].fillna(0))

    # ── Global summary plot ──────────────────────────────
    plt.figure(figsize=(10, 6))
    shap.summary_plot(
        shap_values, X_test[feature_cols],
        plot_type="bar", show=False,
        max_display=15
    )
    plt.title("SHAP Feature Importance — Supplier Distress Model")
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, "shap_global_importance.png"), dpi=150)
    plt.close()
    mlflow.log_artifact(os.path.join(PLOTS_DIR, "shap_global_importance.png"))
    print("\n  ✅ SHAP global importance plot saved")

    # ── Per-company waterfall for top-N highest risk ─────
    risk_scores = model.predict_proba(X_test[feature_cols].fillna(0))[:, 1]
    top_indices = np.argsort(risk_scores)[::-1][:top_n_companies]

    for rank, idx in enumerate(top_indices):
        company_name = company_names.iloc[idx] if idx < len(company_names) else f"Company_{idx}"
        shap_vals    = shap_values[idx]

        shap_df = pd.DataFrame({
            "feature":    feature_cols,
            "shap_value": shap_vals,
        }).sort_values("shap_value", key=abs, ascending=False).head(10)

        fig, ax = plt.subplots(figsize=(9, 5))
        colors = ["#E05252" if v > 0 else "#5270E0" for v in shap_df["shap_value"]]
        ax.barh(shap_df["feature"], shap_df["shap_value"], color=colors)
        ax.axvline(0, color="black", linewidth=0.8)
        ax.set_title(f"SHAP Waterfall — {company_name} (Risk #{rank+1})")
        ax.set_xlabel("SHAP value (impact on distress probability)")
        plt.tight_layout()

        fname = f"shap_waterfall_{company_name.replace(' ', '_')}.png"
        plt.savefig(os.path.join(PLOTS_DIR, fname), dpi=150)
        plt.close()

    print(f"  ✅ SHAP waterfall plots saved for top {top_n_companies} companies")

    # Return mean absolute SHAP per feature
    return pd.DataFrame({
        "feature":    feature_cols,
        "mean_abs_shap": np.abs(shap_values).mean(axis=0)
    }).sort_values("mean_abs_shap", ascending=False)


# ─────────────────────────────────────────────────────────
# D: Ablation Study
# ─────────────────────────────────────────────────────────
def run_ablation_study(train: pd.DataFrame, test: pd.DataFrame):
    """
    Compare four configurations:
      1. Financial features only
      2. NLP features only
      3. All current features (no forecasting)
      4. All features including forecasts (full model)

    Reports AUC and C-index for each.
    """
    print("\n🔬 Running ablation study...")

    financial_cols = [
        "revenue_qoq_pct", "cash_ratio", "debt_to_equity",
        "operating_margin", "interest_coverage"
    ]
    nlp_cols = [
        "news_sentiment_score", "news_volume",
        "distress_keyword_score"
    ]

    configs = {
        "financial_only":   financial_cols,
        "nlp_only":         nlp_cols,
        "all_current":      CURRENT_FEATURES,
        "with_forecasts":   ALL_FEATURES,
    }

    results = {}
    with mlflow.start_run(run_name="ablation_study"):
        for config_name, feature_set in configs.items():
            feat_cols = get_feature_cols(train, feature_set)
            if len(feat_cols) < 2:
                print(f"  ⚠ Skipping {config_name} — insufficient features")
                continue

            print(f"\n  [{config_name}] features: {len(feat_cols)}")
            _, auc, _      = train_xgboost(train, test, feat_cols, run_name=f"xgb_{config_name}")
            _, c_index, _  = train_cox_survival(train, test, feat_cols, run_name=f"cox_{config_name}")

            results[config_name] = {"auc": auc, "c_index": c_index}
            mlflow.log_metrics({
                f"{config_name}_auc":     auc,
                f"{config_name}_cindex":  c_index,
            })

    # Print summary
    print("\n" + "─" * 55)
    print(f"{'Configuration':<25} {'AUC':>10} {'C-index':>10}")
    print("─" * 55)
    for config, metrics in results.items():
        print(f"  {config:<23} {metrics['auc']:>10.4f} {metrics['c_index']:>10.4f}")
    print("─" * 55)

    # Save results
    with open(os.path.join(MODELS_DIR, "ablation_results.json"), "w") as f:
        json.dump(results, f, indent=2)

    return results


# ─────────────────────────────────────────────────────────
# E: Rolling backtest (temporal cross-validation)
# ─────────────────────────────────────────────────────────
def rolling_backtest(df: pd.DataFrame, feature_cols: list[str]):
    """
    Walk-forward validation:
      Fold 1: Train 2019-2020 | Test 2021
      Fold 2: Train 2019-2021 | Test 2022
      Fold 3: Train 2019-2022 | Test 2023

    Ensures no temporal leakage. Reports AUC per fold.
    """
    from xgboost import XGBClassifier
    from sklearn.metrics import roc_auc_score

    folds = [
        (2020, 2021), (2021, 2022), (2022, 2023)
    ]

    print("\n📅 Rolling backtest:")
    fold_results = []

    for train_end, test_year in folds:
        train = df[df["year"] <= train_end].copy()
        test  = df[df["year"] == test_year].copy()

        if test["label_6m"].sum() == 0:
            print(f"  Fold {test_year}: ⚠ No positive cases in test — skipping")
            continue

        feat_cols = get_feature_cols(train, feature_cols)
        pos_ratio = (train["label_6m"] == 0).sum() / max((train["label_6m"] == 1).sum(), 1)

        model = XGBClassifier(
            n_estimators=200, max_depth=4,
            scale_pos_weight=pos_ratio,
            random_state=42, n_jobs=-1
        )
        model.fit(train[feat_cols].fillna(0), train["label_6m"])
        y_prob = model.predict_proba(test[feat_cols].fillna(0))[:, 1]
        auc    = roc_auc_score(test["label_6m"], y_prob)

        print(f"  Train ≤ {train_end} | Test {test_year}: AUC = {auc:.4f}")
        fold_results.append({"train_end": train_end, "test_year": test_year, "auc": auc})

    mean_auc = np.mean([r["auc"] for r in fold_results])
    print(f"\n  Mean AUC across folds: {mean_auc:.4f}")
    return fold_results


# ─────────────────────────────────────────────────────────
# Main runner
# ─────────────────────────────────────────────────────────
def main(run_ablation: bool = False):
    print("🤖 Phase 4 — Risk Modeling\n")

    train, test = load_data(use_forecasts=True)
    print(f"  Train: {len(train):,} rows | Test: {len(test):,} rows")
    print(f"  Train distress rate: {train['label_6m'].mean():.1%}")

    feat_cols = get_feature_cols(train, ALL_FEATURES)
    print(f"  Feature columns available: {len(feat_cols)}")

    with mlflow.start_run(run_name="supplier_distress_main"):

        # ── XGBoost ─────────────────────────────────────
        print("\n🔵 Training XGBoost classifier...")
        xgb_model, xgb_auc, importance_df = train_xgboost(
            train, test, feat_cols, run_name="xgboost_full"
        )
        xgb_model.save_model(os.path.join(MODELS_DIR, "xgboost_distress.json"))

        # ── Cox PH ──────────────────────────────────────
        print("\n🟠 Training Cox PH survival model...")
        cox_model, c_index, coef_df = train_cox_survival(
            train, test, feat_cols, run_name="cox_ph_full"
        )

        # ── SHAP ────────────────────────────────────────
        print("\n🟣 Running SHAP analysis...")
        shap_df = run_shap_analysis(
            xgb_model,
            test,
            feat_cols,
            company_names=test.get("company_name", pd.Series(range(len(test)))),
            top_n_companies=5
        )

        # ── Rolling backtest ─────────────────────────────
        print("\n📅 Rolling backtest...")
        backtest_results = rolling_backtest(
            pd.concat([train, test]),
            feat_cols
        )

        # ── Log summary ──────────────────────────────────
        mlflow.log_metrics({
            "final_xgb_auc": xgb_auc,
            "final_c_index":  c_index,
        })

        print("\n" + "═" * 50)
        print("  FINAL RESULTS")
        print("═" * 50)
        print(f"  XGBoost AUC:   {xgb_auc:.4f}")
        print(f"  Cox C-index:   {c_index:.4f}")
        print(f"  Models saved:  {MODELS_DIR}/")
        print(f"  SHAP plots:    {PLOTS_DIR}/")
        print("═" * 50)

    # ── Ablation (optional) ─────────────────────────────
    if run_ablation:
        run_ablation_study(train, test)

    print("\n✅ Phase 4 complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ablation", action="store_true",
                        help="Run ablation study comparing feature configurations")
    args = parser.parse_args()
    main(run_ablation=args.ablation)
