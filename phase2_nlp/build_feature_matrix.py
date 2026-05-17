"""
Phase 2b — Feature Matrix Builder
Reads all monthly_signals rows from the DB and assembles a clean
feature matrix ready for Phase 3 (forecasting) and Phase 4 (modeling).

Handles:
  - Missing value imputation strategy per feature type
  - Temporal sorting (company, year, month)
  - Label assignment (months-to-distress target for survival modeling)
  - Train/test split by time (strict: no future data leaks)
  - Saves to data/processed/ as parquet + CSV

Usage:
    python phase2_nlp/build_feature_matrix.py
"""

import os
import sys
import math
import numpy as np
import pandas as pd
from datetime import date
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "phase1_data"))
from db_schema import get_engine, Company, MonthlySignal

load_dotenv()

PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
os.makedirs(PROCESSED_DIR, exist_ok=True)

# ─────────────────────────────────────────────────────────
# Feature columns (from monthly_signals table)
# ─────────────────────────────────────────────────────────
FEATURE_COLS = [
    # LinkedIn
    "headcount",
    "headcount_mom_pct",
    "headcount_3m_trend",
    # Job postings
    "job_postings_total",
    "job_postings_mom_pct",
    "pct_ops_finance_roles",
    "pct_senior_roles",
    # Glassdoor
    "glassdoor_rating",
    "glassdoor_rating_mom",
    # NLP
    "news_sentiment_score",
    "news_volume",
    "distress_keyword_score",
    # Financial
    "revenue_qoq_pct",
    "cash_ratio",
    "debt_to_equity",
    "operating_margin",
    "interest_coverage",
]

# Columns that represent change/delta (impute with 0, not forward-fill)
DELTA_COLS = [
    "headcount_mom_pct", "headcount_3m_trend",
    "job_postings_mom_pct", "glassdoor_rating_mom",
    "revenue_qoq_pct",
]


# ─────────────────────────────────────────────────────────
# Load raw signals from DB
# ─────────────────────────────────────────────────────────
def load_signals_from_db(engine) -> pd.DataFrame:
    """Load all monthly_signals joined with company metadata."""
    query = """
        SELECT
            ms.*,
            c.name           AS company_name,
            c.industry,
            c.sector,
            c.distress_label,
            c.distress_date
        FROM monthly_signals ms
        JOIN companies c ON c.id = ms.company_id
        ORDER BY ms.company_id, ms.year, ms.month
    """
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)

    # Create a proper date column
    df["date"] = pd.to_datetime(
        df["year"].astype(str) + "-" + df["month"].astype(str).str.zfill(2) + "-01"
    )
    df["distress_date"] = pd.to_datetime(df["distress_date"])
    return df


# ─────────────────────────────────────────────────────────
# Imputation strategy per feature type
# ─────────────────────────────────────────────────────────
def impute_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Impute missing values per company:
      - Ratio/level features: forward-fill then backfill (use last known value)
      - Delta features: fill with 0 (no change is the safe assumption)
      - Remaining NaN: fill with column median across all companies
    """
    result_dfs = []

    for company_id, group in df.groupby("company_id"):
        group = group.sort_values("date").copy()

        for col in FEATURE_COLS:
            if col not in group.columns:
                group[col] = np.nan
                continue

            if col in DELTA_COLS:
                group[col] = group[col].fillna(0)
            else:
                group[col] = group[col].ffill().bfill()

        result_dfs.append(group)

    df_imputed = pd.concat(result_dfs, ignore_index=True)

    # Final pass: fill remaining NaN with column median
    for col in FEATURE_COLS:
        if col in df_imputed.columns:
            median = df_imputed[col].median()
            df_imputed[col] = df_imputed[col].fillna(median if not math.isnan(median) else 0)

    return df_imputed


# ─────────────────────────────────────────────────────────
# Survival modeling labels
# ─────────────────────────────────────────────────────────
def add_survival_labels(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add two columns for survival modeling:
      - event: 1 if this company experienced distress, 0 otherwise
      - duration: months from this row to the distress event
                  (or months from this row to end of observation period)

    This enables Cox PH and other survival models that need (event, duration).
    """
    OBSERVATION_END = pd.Timestamp("2024-01-01")

    rows = []
    for company_id, group in df.groupby("company_id"):
        group = group.copy().sort_values("date")
        distress_date = group["distress_date"].iloc[0]
        has_distress  = bool(group["distress_label"].iloc[0])

        for _, row in group.iterrows():
            current_date = row["date"]

            if has_distress and pd.notna(distress_date):
                if current_date >= distress_date:
                    # Post-distress rows — exclude from training
                    continue
                delta_months = (
                    (distress_date.year - current_date.year) * 12
                    + (distress_date.month - current_date.month)
                )
                event    = 1
                duration = max(delta_months, 1)
            else:
                delta_months = (
                    (OBSERVATION_END.year - current_date.year) * 12
                    + (OBSERVATION_END.month - current_date.month)
                )
                event    = 0
                duration = max(delta_months, 1)

            row_dict = row.to_dict()
            row_dict["event"]    = event
            row_dict["duration"] = duration
            rows.append(row_dict)

    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────
# Binary classification label (distress within 6 months)
# ─────────────────────────────────────────────────────────
def add_binary_label(df: pd.DataFrame, horizon_months: int = 6) -> pd.DataFrame:
    """
    Add binary label: will this company enter distress within the next N months?
    Used for XGBoost classifier (as a complement to survival modeling).
    """
    df["label_6m"] = (
        (df["event"] == 1) & (df["duration"] <= horizon_months)
    ).astype(int)
    return df


# ─────────────────────────────────────────────────────────
# Train / test split — STRICT temporal split
# Train: 2019-2021 | Test: 2022-2023
# No data from the future can appear in training
# ─────────────────────────────────────────────────────────
def temporal_split(df: pd.DataFrame):
    train = df[df["year"] <= 2021].copy()
    test  = df[df["year"].between(2022, 2023)].copy()
    print(f"  Train: {len(train):,} rows | Test: {len(test):,} rows")
    print(f"  Train distress rate: {train['label_6m'].mean():.1%}")
    print(f"  Test  distress rate: {test['label_6m'].mean():.1%}")
    return train, test


# ─────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────
def build_feature_matrix():
    print("📐 Building feature matrix...")
    engine = get_engine()

    print("  Loading signals from DB...")
    df = load_signals_from_db(engine)
    print(f"  Loaded {len(df):,} rows for {df['company_id'].nunique()} companies")

    print("  Imputing missing values...")
    df = impute_features(df)

    print("  Adding survival labels...")
    df = add_survival_labels(df)

    print("  Adding binary classification labels...")
    df = add_binary_label(df, horizon_months=6)

    print("  Splitting train/test...")
    train, test = temporal_split(df)

    # Save outputs
    df.to_parquet(os.path.join(PROCESSED_DIR, "feature_matrix_full.parquet"), index=False)
    train.to_parquet(os.path.join(PROCESSED_DIR, "train.parquet"), index=False)
    test.to_parquet(os.path.join(PROCESSED_DIR, "test.parquet"),  index=False)

    # Also save CSV for easy inspection
    df.to_csv(os.path.join(PROCESSED_DIR, "feature_matrix_full.csv"), index=False)

    print(f"\n✅ Feature matrix saved to {PROCESSED_DIR}/")
    print(f"   Full matrix: {len(df):,} rows × {len(FEATURE_COLS)} features")
    print(f"   Files: feature_matrix_full.parquet, train.parquet, test.parquet")

    # Quick feature coverage report
    coverage = df[FEATURE_COLS].notna().mean().sort_values(ascending=False)
    print("\n📊 Feature coverage (% non-null):")
    for col, pct in coverage.items():
        bar = "█" * int(pct * 20)
        print(f"  {col:<30} {bar:<20} {pct:.0%}")

    return df, train, test


if __name__ == "__main__":
    build_feature_matrix()
