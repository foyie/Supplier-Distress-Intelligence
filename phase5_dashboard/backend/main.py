"""
Phase 5 — FastAPI Backend
Serves risk scores, signal timelines, forecasts, SHAP values,
and auto-generated analyst briefs to the React frontend.

Run:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

import os
import sys
import json
import math
import joblib
import numpy as np
import pandas as pd
from datetime import date, datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "phase1_data"))

# ─────────────────────────────────────────────────────────
# Get absolute paths — works from any directory
BASE_DIR      = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
FORECAST_DIR  = os.path.join(BASE_DIR, "data", "forecasts")
MODELS_DIR    = os.path.join(BASE_DIR, "models")

print(f"📁 BASE_DIR: {BASE_DIR}")
print(f"📁 PROCESSED_DIR: {PROCESSED_DIR}")
print(f"📁 MODELS_DIR: {MODELS_DIR}")
print(f"✓ Feature matrix exists: {os.path.exists(os.path.join(PROCESSED_DIR, 'feature_matrix_full.parquet'))}")
print(f"✓ XGBoost model exists: {os.path.exists(os.path.join(MODELS_DIR, 'xgboost_distress.json'))}")
print(f"✓ Forecasts exist: {os.path.exists(os.path.join(FORECAST_DIR, 'all_forecasts.parquet'))}")

app = FastAPI(
    title="Supplier Distress API",
    description="Early-warning risk intelligence for supply chain teams",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────
# Load data at startup (cache in memory)
# ─────────────────────────────────────────────────────────
_cache = {}

def load_cache():
    global _cache

    # Feature matrix
    matrix_path = os.path.join(PROCESSED_DIR, "feature_matrix_with_forecasts.parquet")
    if not os.path.exists(matrix_path):
        matrix_path = os.path.join(PROCESSED_DIR, "feature_matrix_full.parquet")
    df = pd.read_parquet(matrix_path)
    df["date"] = pd.to_datetime(df["date"])
    _cache["matrix"] = df

    # Forecasts
    fc_path = os.path.join(FORECAST_DIR, "all_forecasts.parquet")
    if os.path.exists(fc_path):
        _cache["forecasts"] = pd.read_parquet(fc_path)
    else:
        _cache["forecasts"] = pd.DataFrame()

    # XGBoost model
    try:
        from xgboost import XGBClassifier
        model = XGBClassifier()
        model.load_model(os.path.join(MODELS_DIR, "xgboost_distress.json"))
        _cache["model"] = model
    except Exception as e:
        print(f"⚠ Could not load XGBoost model: {e}")
        _cache["model"] = None

    # SHAP values (pre-computed if available)
    shap_path = os.path.join(MODELS_DIR, "shap_values.json")
    if os.path.exists(shap_path):
        with open(shap_path) as f:
            _cache["shap"] = json.load(f)
    else:
        _cache["shap"] = {}

    # Ablation results
    abl_path = os.path.join(MODELS_DIR, "ablation_results.json")
    if os.path.exists(abl_path):
        with open(abl_path) as f:
            _cache["ablation"] = json.load(f)
    else:
        _cache["ablation"] = {}

    print("✅ Data loaded into cache")


@app.on_event("startup")
def startup_event():
    load_cache()


# ─────────────────────────────────────────────────────────
# Helper: compute risk score from latest features
# ─────────────────────────────────────────────────────────
# FEATURE_COLS = [
#     "headcount", "headcount_mom_pct", "headcount_3m_trend",
#     "job_postings_total", "job_postings_mom_pct",
#     "pct_ops_finance_roles", "pct_senior_roles",
#     "glassdoor_rating", "glassdoor_rating_mom",
#     "news_sentiment_score", "news_volume", "distress_keyword_score",
#     "revenue_qoq_pct", "cash_ratio", "debt_to_equity",
#     "operating_margin", "interest_coverage",
# ]
FEATURE_COLS = [
    "headcount", "headcount_mom_pct", "headcount_3m_trend",
    "job_postings_total", "job_postings_mom_pct",
    "pct_ops_finance_roles", "pct_senior_roles",
    "glassdoor_rating", "glassdoor_rating_mom",
    "news_sentiment_score", "news_volume", "distress_keyword_score",
    "revenue_qoq_pct", "cash_ratio", "debt_to_equity",
    "operating_margin", "interest_coverage",
    # Forecasted features
    "headcount_forecast",
    "glassdoor_rating_forecast",
    "cash_ratio_forecast",
    "debt_to_equity_forecast",
    "news_sentiment_score_forecast",
    "distress_keyword_score_forecast",
    "pct_ops_finance_roles_forecast",
]
def get_risk_tier(score: float) -> str:
    if score >= 0.65:  return "CRITICAL"
    if score >= 0.45:  return "HIGH"
    if score >= 0.25:  return "MEDIUM"
    return "LOW"

def get_risk_color(tier: str) -> str:
    return {"CRITICAL": "#FF3B3B", "HIGH": "#FF8C00",
            "MEDIUM": "#F5C518", "LOW": "#22C55E"}.get(tier, "#888")

def safe_float(v):
    if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
        return None
    return round(float(v), 4)

def compute_risk_score(company_id: int) -> dict:
    """Compute current risk score for a company from latest feature row."""
    df = _cache["matrix"]
    company_rows = df[df["company_id"] == company_id].sort_values("date")
    if company_rows.empty:
        return {"score": 0.0, "tier": "LOW", "delta": 0.0}

    latest = company_rows.iloc[-1]
    prev   = company_rows.iloc[-2] if len(company_rows) > 1 else None

    model = _cache.get("model")

    # Try to use model, but fall back to heuristic if feature mismatch
    score = None
    if model is not None:
        try:
            feat_cols = [c for c in FEATURE_COLS if c in company_rows.columns]
            X = latest[feat_cols].values.reshape(1, -1)
            X = np.nan_to_num(X, nan=0.0)
            score = float(model.predict_proba(X)[0][1])
        except Exception as e:
            print(f"  ⚠ Model prediction failed ({str(e)[:50]}), using heuristic")
            score = None

    # Fall back to heuristic if model fails or not available
    if score is None:
        score = _heuristic_score(latest)

    delta = 0.0
    if prev is not None and model is not None:
        try:
            feat_cols = [c for c in FEATURE_COLS if c in company_rows.columns]
            X_prev = prev[feat_cols].values.reshape(1, -1)
            X_prev = np.nan_to_num(X_prev, nan=0.0)
            prev_score = float(model.predict_proba(X_prev)[0][1])
            delta = round((score - prev_score) * 100, 1)
        except Exception:
            delta = 0.0

    tier = get_risk_tier(score)
    return {
        "score": round(score * 100, 1),
        "tier":  tier,
        "color": get_risk_color(tier),
        "delta": delta,
    }


def _heuristic_score(row) -> float:
    """Simple weighted fallback score when model isn't loaded."""
    score = 0.0
    weights = {
        "distress_keyword_score": 0.25,
        "news_sentiment_score":   -0.20,
        "cash_ratio":             -0.15,
        "debt_to_equity":         0.15,
        "headcount_mom_pct":      -0.10,
        "operating_margin":       -0.15,
    }
    for col, w in weights.items():
        val = row.get(col)
        if val is not None and not (isinstance(val, float) and math.isnan(val)):
            score += float(val) * w
    return max(0.0, min(1.0, 0.3 + score))


# ─────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "ok", "message": "Supplier Distress API v1.0"}


# ── /companies — ranked leaderboard ──────────────────────
@app.get("/companies")
def get_companies(
    sector: Optional[str]   = Query(None),
    tier:   Optional[str]   = Query(None),
    sort:   str             = Query("score"),
    limit:  int             = Query(50),
):
    df = _cache["matrix"]

    # Get one row per company (latest)
    latest = (
        df.sort_values("date")
        .groupby("company_id")
        .last()
        .reset_index()
    )

    results = []
    for _, row in latest.iterrows():
        company_id   = int(row["company_id"])
        risk         = compute_risk_score(company_id)
        company_name = row.get("company_name", f"Company {company_id}")
        company_sector = row.get("sector", "Unknown")

        if sector and company_sector != sector:
            continue
        if tier and risk["tier"] != tier:
            continue

        results.append({
            "id":       company_id,
            "name":     company_name,
            "industry": row.get("industry", ""),
            "sector":   company_sector,
            "score":    risk["score"],
            "tier":     risk["tier"],
            "color":    risk["color"],
            "delta":    risk["delta"],
            "distress_label": bool(row.get("distress_label", False)),
            "headcount":      safe_float(row.get("headcount")),
            "glassdoor_rating": safe_float(row.get("glassdoor_rating")),
            "cash_ratio":     safe_float(row.get("cash_ratio")),
            "news_sentiment": safe_float(row.get("news_sentiment_score")),
        })

    # Sort
    reverse = sort in ("score", "delta")
    results.sort(key=lambda x: x.get(sort, 0) or 0, reverse=reverse)
    return results[:limit]


# ── /company/:id — full company detail ───────────────────
@app.get("/company/{company_id}")
def get_company(company_id: int):
    df = _cache["matrix"]
    rows = df[df["company_id"] == company_id].sort_values("date")

    if rows.empty:
        raise HTTPException(status_code=404, detail="Company not found")

    latest = rows.iloc[-1]
    risk   = compute_risk_score(company_id)

    return {
        "id":             company_id,
        "name":           latest.get("company_name", f"Company {company_id}"),
        "industry":       latest.get("industry", ""),
        "sector":         latest.get("sector", ""),
        "distress_label": bool(latest.get("distress_label", False)),
        "distress_date":  str(latest.get("distress_date", "")) if pd.notna(latest.get("distress_date")) else None,
        "risk":           risk,
        "latest_signals": {
            "headcount":            safe_float(latest.get("headcount")),
            "headcount_mom_pct":    safe_float(latest.get("headcount_mom_pct")),
            "glassdoor_rating":     safe_float(latest.get("glassdoor_rating")),
            "news_sentiment_score": safe_float(latest.get("news_sentiment_score")),
            "distress_keyword_score": safe_float(latest.get("distress_keyword_score")),
            "cash_ratio":           safe_float(latest.get("cash_ratio")),
            "debt_to_equity":       safe_float(latest.get("debt_to_equity")),
            "operating_margin":     safe_float(latest.get("operating_margin")),
            "pct_ops_finance_roles":safe_float(latest.get("pct_ops_finance_roles")),
        },
    }


# ── /company/:id/signals — full historical signal timeline ──
@app.get("/company/{company_id}/signals")
def get_signals(company_id: int):
    df = _cache["matrix"]
    rows = df[df["company_id"] == company_id].sort_values("date")

    if rows.empty:
        raise HTTPException(status_code=404, detail="Company not found")

    signal_cols = [
        "date", "year", "month",
        "headcount", "headcount_mom_pct",
        "glassdoor_rating", "news_sentiment_score",
        "news_volume", "distress_keyword_score",
        "cash_ratio", "debt_to_equity", "operating_margin",
        "pct_ops_finance_roles", "job_postings_total",
    ]
    available = [c for c in signal_cols if c in rows.columns]
    result_df = rows[available].copy()
    result_df["date"] = result_df["date"].dt.strftime("%Y-%m-%d")

    # Replace NaN with None for JSON
    result_df = result_df.where(pd.notna(result_df), None)
    result = result_df.to_dict(orient="records")

    # Double-check for any remaining NaN
    for record in result:
        for key in record:
            if isinstance(record[key], float) and math.isnan(record[key]):
                record[key] = None

    return result


# ── /company/:id/forecast — 6-month signal projections ───
@app.get("/company/{company_id}/forecast")
def get_forecast(company_id: int):
    fc = _cache.get("forecasts", pd.DataFrame())
    if fc.empty:
        return {"forecasts": [], "message": "No forecasts available — run Phase 3 first"}

    company_fc = fc[fc["company_id"] == company_id].copy()
    if company_fc.empty:
        return {"forecasts": [], "message": "No forecasts for this company"}

    company_fc["date"] = pd.to_datetime(
        company_fc["year"].astype(str) + "-" +
        company_fc["month"].astype(str).str.zfill(2) + "-01"
    ).dt.strftime("%Y-%m-%d")

    company_fc["value"]       = company_fc["value"].apply(safe_float)
    company_fc["value_lower"] = company_fc["value_lower"].apply(
        lambda x: safe_float(x) if pd.notna(x) else None
    )
    company_fc["value_upper"] = company_fc["value_upper"].apply(
        lambda x: safe_float(x) if pd.notna(x) else None
    )

    # Replace NaN with None for JSON serialization
    result = company_fc[["date","feature","value","value_lower","value_upper","model"]].to_dict(orient="records")

    # Clean up any remaining NaN values
    for record in result:
        for key in record:
            if isinstance(record[key], float) and math.isnan(record[key]):
                record[key] = None

    return result


# ── /company/:id/shap — SHAP feature attribution ─────────
@app.get("/company/{company_id}/shap")
def get_shap(company_id: int):
    shap_data = _cache.get("shap", {})
    key = str(company_id)

    if key in shap_data:
        return shap_data[key]

    # Compute on the fly if model is loaded
    model = _cache.get("model")
    df    = _cache["matrix"]
    rows  = df[df["company_id"] == company_id].sort_values("date")

    if rows.empty:
        return {"shap_values": [], "message": "Company not found"}

    if model is None:
        return {
            "shap_values": [],
            "message": "XGBoost model not loaded. Run Phase 4: python phase4_modeling/train_models.py"
        }

    try:
        import shap as shap_lib
        feat_cols = [c for c in FEATURE_COLS if c in rows.columns]
        latest    = rows.iloc[-1][feat_cols].values.reshape(1, -1)
        latest    = np.nan_to_num(latest, nan=0.0)

        explainer   = shap_lib.TreeExplainer(model)
        shap_values = explainer.shap_values(latest)[0]

        result = sorted([
            {"feature": feat_cols[i], "value": round(float(shap_values[i]), 5)}
            for i in range(len(feat_cols))
        ], key=lambda x: abs(x["value"]), reverse=True)

        return {"shap_values": result[:15]}
    except Exception as e:
        return {
            "shap_values": [],
            "error": f"SHAP computation failed: {str(e)[:100]}"
        }


# ── /company/:id/brief — auto-generated analyst memo ──────
@app.get("/company/{company_id}/brief")
def get_brief(company_id: int):
    df   = _cache["matrix"]
    rows = df[df["company_id"] == company_id].sort_values("date")

    if rows.empty:
        raise HTTPException(status_code=404, detail="Company not found")

    latest = rows.iloc[-1]
    risk   = compute_risk_score(company_id)
    name   = latest.get("company_name", f"Company {company_id}")
    tier   = risk["tier"]
    score  = risk["score"]

    # Build signal summaries for the brief
    signals = []

    sentiment = safe_float(latest.get("news_sentiment_score"))
    if sentiment is not None:
        label = "positive" if sentiment > 0.1 else ("negative" if sentiment < -0.1 else "neutral")
        signals.append(f"News sentiment is {label} ({sentiment:+.2f})")

    distress_kw = safe_float(latest.get("distress_keyword_score"))
    if distress_kw is not None and distress_kw > 0.3:
        signals.append(f"Elevated distress keyword frequency detected (score: {distress_kw:.2f})")

    hc_mom = safe_float(latest.get("headcount_mom_pct"))
    if hc_mom is not None and hc_mom < -3:
        signals.append(f"Headcount declining ({hc_mom:+.1f}% MoM)")
    elif hc_mom is not None and hc_mom > 3:
        signals.append(f"Headcount growing ({hc_mom:+.1f}% MoM)")

    cash = safe_float(latest.get("cash_ratio"))
    if cash is not None and cash < 0.5:
        signals.append(f"Low cash ratio ({cash:.2f}) — potential liquidity concern")

    de = safe_float(latest.get("debt_to_equity"))
    if de is not None and de > 2.0:
        signals.append(f"High leverage (D/E: {de:.1f}x)")

    ops_pct = safe_float(latest.get("pct_ops_finance_roles"))
    if ops_pct is not None and ops_pct > 0.4:
        signals.append(f"Rising ops/finance hiring mix ({ops_pct:.0%}) — cost-cutting signal")

    margin = safe_float(latest.get("operating_margin"))
    if margin is not None and margin < 0:
        signals.append(f"Negative operating margin ({margin:.1%})")

    rec = {
        "CRITICAL": "Immediate escalation recommended. Consider alternative sourcing or contract renegotiation.",
        "HIGH":     "Enhanced monitoring advised. Schedule supplier review within 30 days.",
        "MEDIUM":   "Flag for quarterly review. Monitor key signals for deterioration.",
        "LOW":      "No action required. Continue standard monitoring cadence.",
    }.get(tier, "Monitor as standard.")

    return {
        "company_id":    company_id,
        "company_name":  name,
        "generated_at":  datetime.now().strftime("%B %d, %Y"),
        "risk_tier":     tier,
        "risk_score":    score,
        "industry":      latest.get("industry", ""),
        "sector":        latest.get("sector", ""),
        "signal_summary": signals,
        "recommendation": rec,
        "disclaimer": "This brief is generated by an ML model for analytical purposes only.",
    }


# ── /sectors — available sectors for filtering ────────────
@app.get("/sectors")
def get_sectors():
    df = _cache["matrix"]
    sectors = sorted(df["sector"].dropna().unique().tolist())
    return sectors


# ── /stats — dashboard summary stats ─────────────────────
@app.get("/stats")
def get_stats():
    df = _cache["matrix"]
    latest = df.sort_values("date").groupby("company_id").last().reset_index()
    total  = len(latest)

    risk_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for _, row in latest.iterrows():
        risk = compute_risk_score(int(row["company_id"]))
        tier = risk["tier"]
        if tier in risk_counts:
            risk_counts[tier] += 1

    abl = _cache.get("ablation", {})
    best_auc = max(
        [v.get("auc", 0) for v in abl.values()],
        default=0.0
    )

    return {
        "total_companies": total,
        "risk_distribution": risk_counts,
        "model_auc":   round(best_auc, 4),
        "last_updated": datetime.now().strftime("%Y-%m-%d"),
        "data_coverage_months": int(df["date"].nunique()),
    }


# ── /ablation — ablation study results ───────────────────
@app.get("/ablation")
def get_ablation():
    return _cache.get("ablation", {})
