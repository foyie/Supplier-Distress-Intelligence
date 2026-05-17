"""
Phase 5 — FastAPI Backend
Serves risk scores, forecasts, SHAP values, and analyst briefs
to the React frontend.

Endpoints:
  GET  /api/companies              → ranked list with risk scores
  GET  /api/company/{id}           → full company deep-dive
  GET  /api/company/{id}/forecast  → 6-month signal projections
  GET  /api/company/{id}/shap      → SHAP feature attribution
  GET  /api/company/{id}/brief     → auto-generated analyst memo
  GET  /api/meta/stats             → dashboard summary stats

Usage:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

import os
import sys
import math
import json
import joblib
import numpy as np
import pandas as pd
from datetime import date, datetime
from typing import Optional
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

load_dotenv()

# ─────────────────────────────────────────────────────────
# Fix paths: work from any directory (root or phase5_app/backend)
# ─────────────────────────────────────────────────────────
BACKEND_DIR   = os.path.dirname(os.path.abspath(__file__))
PHASE5_DIR    = os.path.dirname(BACKEND_DIR)
PROJECT_ROOT  = os.path.dirname(PHASE5_DIR)

# If we're running from phase5_app/backend, BASE_DIR is 2 levels up
# If we're running from root with: cd phase5_app/backend && uvicorn, same thing
BASE_DIR      = PROJECT_ROOT

sys.path.insert(0, os.path.join(BASE_DIR, "phase1_data"))
from db_schema import get_engine, Company, MonthlySignal

MODELS_DIR    = os.path.join(BASE_DIR, "models")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
FORECAST_DIR  = os.path.join(BASE_DIR, "data", "forecasts")
PLOTS_DIR     = os.path.join(BASE_DIR, "data", "plots")

# ─────────────────────────────────────────────────────────
# App setup
# ─────────────────────────────────────────────────────────
app = FastAPI(
    title="Supplier Distress API",
    description="Early-warning system for supplier financial distress",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_xgb_model    = None
_feature_cols = None
_feature_matrix = None
_forecast_df  = None
_shap_values  = None

FEATURE_COLS = [
    "headcount", "headcount_mom_pct", "headcount_3m_trend",
    "job_postings_total", "job_postings_mom_pct",
    "pct_ops_finance_roles", "pct_senior_roles",
    "glassdoor_rating", "glassdoor_rating_mom",
    "news_sentiment_score", "news_volume", "distress_keyword_score",
    "revenue_qoq_pct", "cash_ratio", "debt_to_equity",
    "operating_margin", "interest_coverage",
    # forecasted
    "headcount_forecast", "glassdoor_rating_forecast",
    "cash_ratio_forecast", "debt_to_equity_forecast",
    "news_sentiment_score_forecast", "distress_keyword_score_forecast",
    "pct_ops_finance_roles_forecast",
]

FEATURE_LABELS = {
    "headcount":                    "Headcount",
    "headcount_mom_pct":            "Headcount MoM %",
    "headcount_3m_trend":           "Headcount 3M Trend",
    "job_postings_total":           "Job Postings",
    "pct_ops_finance_roles":        "Ops/Finance Role %",
    "glassdoor_rating":             "Glassdoor Rating",
    "news_sentiment_score":         "News Sentiment",
    "distress_keyword_score":       "Distress Keyword Score",
    "cash_ratio":                   "Cash Ratio",
    "debt_to_equity":               "Debt / Equity",
    "operating_margin":             "Operating Margin",
    "interest_coverage":            "Interest Coverage",
    "revenue_qoq_pct":              "Revenue QoQ %",
    "headcount_forecast":           "Headcount Forecast",
    "news_sentiment_score_forecast":"Sentiment Forecast",
    "distress_keyword_score_forecast": "Distress Score Forecast",
}


def load_model():
    global _xgb_model
    if _xgb_model is None:
        from xgboost import XGBClassifier
        model = XGBClassifier()
        model_path = os.path.join(MODELS_DIR, "xgboost_distress.json")
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Model not found at {model_path}. Run Phase 4 first."
            )
        model.load_model(model_path)
        _xgb_model = model
    return _xgb_model


def load_feature_matrix():
    global _feature_matrix
    if _feature_matrix is None:
        path = os.path.join(PROCESSED_DIR, "feature_matrix_with_forecasts.parquet")
        if not os.path.exists(path):
            path = os.path.join(PROCESSED_DIR, "feature_matrix_full.parquet")
        _feature_matrix = pd.read_parquet(path)
        _feature_matrix["date"] = pd.to_datetime(_feature_matrix["date"])
    return _feature_matrix


def load_forecasts():
    global _forecast_df
    if _forecast_df is None:
        path = os.path.join(FORECAST_DIR, "all_forecasts.parquet")
        if os.path.exists(path):
            _forecast_df = pd.read_parquet(path)
        else:
            _forecast_df = pd.DataFrame()
    return _forecast_df


def get_shap_values(model, X: pd.DataFrame):
    global _shap_values
    import shap
    explainer = shap.TreeExplainer(model)
    return explainer.shap_values(X)


def get_available_features(df: pd.DataFrame) -> list[str]:
    return [f for f in FEATURE_COLS if f in df.columns]


# ─────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────
def risk_tier(score: float) -> str:
    if score >= 0.65:   return "HIGH"
    if score >= 0.35:   return "MEDIUM"
    return "LOW"


def safe_float(v) -> Optional[float]:
    if v is None:
        return None
    try:
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else round(f, 4)
    except Exception:
        return None


def score_company(company_id: int, df: pd.DataFrame, model) -> dict:
    """Score a company using its most recent feature row."""
    company_df = df[df["company_id"] == company_id].sort_values("date")
    if company_df.empty:
        return {"score": None, "prev_score": None}

    feat_cols   = get_available_features(company_df)
    latest      = company_df.iloc[[-1]][feat_cols].fillna(0)
    score       = float(model.predict_proba(latest)[0][1])

    prev_score  = None
    if len(company_df) >= 2:
        prev    = company_df.iloc[[-2]][feat_cols].fillna(0)
        prev_score = float(model.predict_proba(prev)[0][1])

    return {"score": round(score, 4), "prev_score": round(prev_score, 4) if prev_score else None}


# ─────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────
@app.get("/api/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.get("/api/companies")
def list_companies(
    sector:   Optional[str] = Query(None),
    tier:     Optional[str] = Query(None),
    sort_by:  str           = Query("score", enum=["score", "score_change", "name"]),
):
    """
    Returns all companies with their latest risk scores, tier, and delta.
    Supports filtering by sector and risk tier.
    """
    engine = get_engine()
    model  = load_model()
    df     = load_feature_matrix()

    with Session(engine) as session:
        companies = session.query(Company).all()
        results   = []

        for c in companies:
            scored = score_company(c.id, df, model)
            if scored["score"] is None:
                continue

            score      = scored["score"]
            prev_score = scored["prev_score"]
            delta      = round(score - prev_score, 4) if prev_score is not None else 0
            tier_val   = risk_tier(score)

            if sector and c.sector != sector:
                continue
            if tier and tier_val != tier.upper():
                continue

            results.append({
                "id":           c.id,
                "name":         c.name,
                "ticker":       c.ticker,
                "industry":     c.industry,
                "sector":       c.sector,
                "score":        score,
                "score_pct":    round(score * 100, 1),
                "prev_score":   prev_score,
                "delta":        delta,
                "tier":         tier_val,
                "distress_label": c.distress_label,
                "distress_date":  str(c.distress_date) if c.distress_date else None,
            })

        # Sort
        if sort_by == "score":
            results.sort(key=lambda x: x["score"], reverse=True)
        elif sort_by == "score_change":
            results.sort(key=lambda x: abs(x["delta"]), reverse=True)
        elif sort_by == "name":
            results.sort(key=lambda x: x["name"])

        return {"companies": results, "total": len(results)}


@app.get("/api/company/{company_id}")
def get_company(company_id: int):
    """Full company deep-dive: score + signal history + metadata."""
    engine = get_engine()
    model  = load_model()
    df     = load_feature_matrix()

    with Session(engine) as session:
        company = session.query(Company).filter_by(id=company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        scored      = score_company(company_id, df, model)
        company_df  = df[df["company_id"] == company_id].sort_values("date")
        feat_cols   = get_available_features(company_df)

        # Score history (all months)
        score_history = []
        for _, row in company_df.iterrows():
            row_feat = row[feat_cols].fillna(0).values.reshape(1, -1)
            s = float(model.predict_proba(pd.DataFrame([row[feat_cols].fillna(0)], columns=feat_cols))[0][1])
            score_history.append({
                "date":  row["date"].strftime("%Y-%m"),
                "score": round(s, 4),
                "score_pct": round(s * 100, 1),
            })

        # Latest signal values
        latest_row = company_df.iloc[-1] if not company_df.empty else None
        signals = {}
        if latest_row is not None:
            for col in feat_cols:
                signals[col] = safe_float(latest_row.get(col))

        return {
            "id":             company.id,
            "name":           company.name,
            "ticker":         company.ticker,
            "industry":       company.industry,
            "sector":         company.sector,
            "score":          scored["score"],
            "score_pct":      round((scored["score"] or 0) * 100, 1),
            "prev_score":     scored["prev_score"],
            "delta":          round((scored["score"] or 0) - (scored["prev_score"] or 0), 4),
            "tier":           risk_tier(scored["score"] or 0),
            "distress_label": company.distress_label,
            "distress_date":  str(company.distress_date) if company.distress_date else None,
            "score_history":  score_history,
            "latest_signals": signals,
        }


@app.get("/api/company/{company_id}/forecast")
def get_forecast(company_id: int):
    """6-month forward signal projections from Prophet + LSTM."""
    forecast_df = load_forecasts()
    if forecast_df.empty:
        return {"forecasts": [], "message": "No forecasts available. Run Phase 3 first."}

    company_forecasts = forecast_df[forecast_df["company_id"] == company_id]
    if company_forecasts.empty:
        return {"forecasts": [], "message": "No forecasts for this company."}

    result = []
    for feature in company_forecasts["feature"].unique():
        feature_df = company_forecasts[company_forecasts["feature"] == feature].sort_values(
            ["year", "month"]
        )
        result.append({
            "feature":       feature,
            "feature_label": FEATURE_LABELS.get(feature.replace("_forecast", ""), feature),
            "model":         feature_df["model"].iloc[0] if "model" in feature_df.columns else "unknown",
            "values": [
                {
                    "date":        f"{int(r['year'])}-{int(r['month']):02d}",
                    "value":       safe_float(r["value"]),
                    "value_lower": safe_float(r.get("value_lower")),
                    "value_upper": safe_float(r.get("value_upper")),
                }
                for _, r in feature_df.iterrows()
            ],
        })

    return {"company_id": company_id, "forecasts": result}


@app.get("/api/company/{company_id}/shap")
def get_shap(company_id: int):
    """SHAP feature attribution for most recent prediction."""
    model = load_model()
    df    = load_feature_matrix()

    company_df = df[df["company_id"] == company_id].sort_values("date")
    if company_df.empty:
        raise HTTPException(status_code=404, detail="No data for this company")

    feat_cols = get_available_features(company_df)
    latest    = company_df.iloc[[-1]][feat_cols].fillna(0)

    shap_vals = get_shap_values(model, latest)[0]

    result = []
    for col, val in zip(feat_cols, shap_vals):
        result.append({
            "feature":       col,
            "feature_label": FEATURE_LABELS.get(col, col),
            "shap_value":    round(float(val), 5),
            "feature_value": safe_float(latest[col].iloc[0]),
            "direction":     "risk" if val > 0 else "protective",
        })

    result.sort(key=lambda x: abs(x["shap_value"]), reverse=True)
    return {"company_id": company_id, "shap": result[:15]}  # top 15


@app.get("/api/company/{company_id}/brief")
def get_brief(company_id: int):
    """Auto-generate a one-page analyst memo for a company."""
    engine = get_engine()
    model  = load_model()
    df     = load_feature_matrix()

    with Session(engine) as session:
        company = session.query(Company).filter_by(id=company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

    scored      = score_company(company_id, df, model)
    score       = scored["score"] or 0
    tier        = risk_tier(score)
    company_df  = df[df["company_id"] == company_id].sort_values("date")
    feat_cols   = get_available_features(company_df)

    # Get SHAP for key drivers
    if not company_df.empty:
        latest    = company_df.iloc[[-1]][feat_cols].fillna(0)
        shap_vals = get_shap_values(model, latest)[0]
        top_drivers = sorted(
            zip(feat_cols, shap_vals),
            key=lambda x: abs(x[1]), reverse=True
        )[:3]
        driver_text = ", ".join(
            FEATURE_LABELS.get(f, f) for f, _ in top_drivers if _ > 0
        ) or "multiple signals"
        protective_text = ", ".join(
            FEATURE_LABELS.get(f, f) for f, _ in top_drivers if _ < 0
        ) or "stable fundamentals"
    else:
        driver_text     = "insufficient data"
        protective_text = "insufficient data"

    # Latest financials
    signals = {}
    if not company_df.empty:
        row = company_df.iloc[-1]
        for col in feat_cols:
            signals[col] = safe_float(row.get(col))

    # Compose memo
    tier_language = {
        "HIGH":   "elevated and warrants immediate procurement review",
        "MEDIUM": "moderate and merits continued monitoring",
        "LOW":    "low with no immediate concerns flagged",
    }

    brief = {
        "company":     company.name,
        "ticker":      company.ticker,
        "sector":      company.sector,
        "industry":    company.industry,
        "generated":   date.today().isoformat(),
        "score":       round(score * 100, 1),
        "tier":        tier,
        "summary": (
            f"{company.name} carries a distress risk score of {round(score*100,1)}/100, "
            f"placing it in the {tier} risk tier. The overall risk level is "
            f"{tier_language.get(tier, 'uncertain')}."
        ),
        "key_risk_drivers": driver_text,
        "protective_factors": protective_text,
        "financials": {
            "cash_ratio":       signals.get("cash_ratio"),
            "debt_to_equity":   signals.get("debt_to_equity"),
            "operating_margin": signals.get("operating_margin"),
            "revenue_qoq_pct":  signals.get("revenue_qoq_pct"),
        },
        "sentiment": {
            "news_sentiment_score":   signals.get("news_sentiment_score"),
            "distress_keyword_score": signals.get("distress_keyword_score"),
            "glassdoor_rating":       signals.get("glassdoor_rating"),
        },
        "recommendation": (
            "Initiate alternative supplier qualification and request updated financials."
            if tier == "HIGH" else
            "Schedule quarterly review and flag for procurement watch list."
            if tier == "MEDIUM" else
            "No immediate action required. Standard annual review cycle."
        ),
    }

    return brief


@app.get("/api/meta/stats")
def get_stats():
    """Summary stats for the dashboard header."""
    engine = get_engine()
    model  = load_model()
    df     = load_feature_matrix()

    with Session(engine) as session:
        companies = session.query(Company).all()

    scores = []
    for c in companies:
        scored = score_company(c.id, df, model)
        if scored["score"] is not None:
            scores.append(scored["score"])

    if not scores:
        return {}

    tiers = [risk_tier(s) for s in scores]
    return {
        "total_companies":  len(scores),
        "high_risk":        tiers.count("HIGH"),
        "medium_risk":      tiers.count("MEDIUM"),
        "low_risk":         tiers.count("LOW"),
        "mean_score":       round(float(np.mean(scores)) * 100, 1),
        "last_updated":     date.today().isoformat(),
    }


@app.get("/api/meta/sectors")
def get_sectors():
    engine = get_engine()
    with Session(engine) as session:
        sectors = [r[0] for r in session.query(Company.sector).distinct().all() if r[0]]
    return {"sectors": sorted(sectors)}
