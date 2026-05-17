"""
Phase 3 — Signal Forecasting (Prophet + LSTM)
Forecasts each signal 6 months into the future per company.
Forecasted values are then used as features for the risk model in Phase 4.

Why forecast first, then model?
  → Risk score based on WHERE a company is heading, not where it is today.
  → Ablation study: compare risk model AUC using current vs forecasted features.

Prophet handles: headcount, financial ratios, glassdoor_rating
  → Slow-moving, trend + seasonality structure → Prophet is ideal

LSTM handles: sentiment, news_volume, distress_keyword_score
  → Noisier, sequential signals with momentum → LSTM captures non-linear dynamics

Usage:
    python phase3_forecasting/forecaster.py --model prophet   # only Prophet
    python phase3_forecasting/forecaster.py --model lstm      # only LSTM
    python phase3_forecasting/forecaster.py --model both      # run all
"""

import os
import sys
import math
import argparse
import warnings
import numpy as np
import pandas as pd
from tqdm import tqdm

warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "phase1_data"))
PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
FORECAST_DIR  = os.path.join(os.path.dirname(__file__), "..", "data", "forecasts")
os.makedirs(FORECAST_DIR, exist_ok=True)

FORECAST_HORIZON = 6   # months ahead to forecast

# ─────────────────────────────────────────────────────────
# Feature routing: which model handles which signals
# ─────────────────────────────────────────────────────────
PROPHET_FEATURES = [
    "headcount",
    "glassdoor_rating",
    "cash_ratio",
    "debt_to_equity",
    "operating_margin",
    "interest_coverage",
]

LSTM_FEATURES = [
    "news_sentiment_score",
    "news_volume",
    "distress_keyword_score",
    "headcount_mom_pct",
    "pct_ops_finance_roles",
]


# ─────────────────────────────────────────────────────────
# Prophet Forecaster
# ─────────────────────────────────────────────────────────
def forecast_prophet(
    series: pd.Series,
    horizon: int = FORECAST_HORIZON
) -> pd.DataFrame:
    """
    Forecast a single time series using Prophet.
    Input: pd.Series with DatetimeIndex (monthly frequency)
    Returns: DataFrame with columns [ds, yhat, yhat_lower, yhat_upper]
    """
    from prophet import Prophet

    # Prophet requires columns: ds (datetime), y (value)
    df = pd.DataFrame({
        "ds": series.index,
        "y":  series.values,
    }).dropna()

    if len(df) < 6:
        return pd.DataFrame()   # need at least 6 points

    # Fit
    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=False,
        daily_seasonality=False,
        seasonality_mode="additive",
        interval_width=0.80,
        changepoint_prior_scale=0.15,   # slightly flexible for business signals
    )
    model.fit(df, iter=500)

    # Predict
    future = model.make_future_dataframe(periods=horizon, freq="MS")
    forecast = model.predict(future)

    # Return only the forecast period
    forecast_only = forecast.tail(horizon)[["ds", "yhat", "yhat_lower", "yhat_upper"]]
    return forecast_only.reset_index(drop=True)


def run_prophet_for_all_companies(df: pd.DataFrame) -> pd.DataFrame:
    """
    Run Prophet on each PROPHET_FEATURE for each company.
    Returns DataFrame with company_id, year, month, feature_name, forecasted_value.
    """
    all_rows = []
    companies = df["company_id"].unique()

    for company_id in tqdm(companies, desc="Prophet per company"):
        company_df = df[df["company_id"] == company_id].copy()
        company_df = company_df.sort_values("date").set_index("date")

        for feature in PROPHET_FEATURES:
            if feature not in company_df.columns:
                continue
            series = company_df[feature].dropna()
            if series.empty:
                continue

            # Resample to monthly start
            series = series.resample("MS").mean()

            forecast = forecast_prophet(series, horizon=FORECAST_HORIZON)
            if forecast.empty:
                continue

            for _, row in forecast.iterrows():
                all_rows.append({
                    "company_id":       company_id,
                    "year":             row["ds"].year,
                    "month":            row["ds"].month,
                    "feature":          f"{feature}_forecast",
                    "value":            row["yhat"],
                    "value_lower":      row["yhat_lower"],
                    "value_upper":      row["yhat_upper"],
                    "model":            "prophet",
                })

    return pd.DataFrame(all_rows)


# ─────────────────────────────────────────────────────────
# LSTM Forecaster
# ─────────────────────────────────────────────────────────
class LSTMForecaster:
    """
    Lightweight single-layer LSTM for univariate time series forecasting.
    Trained per company-feature pair to capture individual dynamics.

    Architecture: LSTM(hidden=32) → Linear(1)
    Input window: last 12 months → predict next 1 month, rolled 6 times
    """

    def __init__(self, input_window: int = 12, hidden_size: int = 32):
        self.input_window = input_window
        self.hidden_size  = hidden_size
        self.model        = None
        self.scaler_mean  = None
        self.scaler_std   = None

    def _build_model(self):
        import torch.nn as nn

        class LSTMNet(nn.Module):
            def __init__(self, hidden):
                super().__init__()
                self.lstm   = nn.LSTM(input_size=1, hidden_size=hidden, batch_first=True)
                self.linear = nn.Linear(hidden, 1)

            def forward(self, x):
                out, _ = self.lstm(x)
                return self.linear(out[:, -1, :])

        return LSTMNet(self.hidden_size)

    def _normalize(self, values: np.ndarray) -> np.ndarray:
        self.scaler_mean = values.mean()
        self.scaler_std  = values.std() if values.std() > 1e-8 else 1.0
        return (values - self.scaler_mean) / self.scaler_std

    def _denormalize(self, values: np.ndarray) -> np.ndarray:
        return values * self.scaler_std + self.scaler_mean

    def fit(self, series: np.ndarray, epochs: int = 50, lr: float = 1e-3):
        import torch
        import torch.nn as nn

        norm = self._normalize(series)
        self.model = self._build_model()
        optimizer  = torch.optim.Adam(self.model.parameters(), lr=lr)
        criterion  = nn.MSELoss()

        # Create sliding window dataset
        X, y = [], []
        for i in range(len(norm) - self.input_window):
            X.append(norm[i : i + self.input_window])
            y.append(norm[i + self.input_window])

        if len(X) < 3:
            return False   # not enough data

        X = torch.tensor(np.array(X), dtype=torch.float32).unsqueeze(-1)  # [N, T, 1]
        y = torch.tensor(np.array(y), dtype=torch.float32).unsqueeze(-1)  # [N, 1]

        self.model.train()
        for epoch in range(epochs):
            optimizer.zero_grad()
            pred = self.model(X)
            loss = criterion(pred, y)
            loss.backward()
            optimizer.step()

        return True

    def predict(self, series: np.ndarray, steps: int = FORECAST_HORIZON) -> np.ndarray:
        """Autoregressively predict `steps` months ahead."""
        import torch

        norm    = (series - self.scaler_mean) / self.scaler_std
        window  = list(norm[-self.input_window:])
        preds   = []

        self.model.eval()
        with torch.no_grad():
            for _ in range(steps):
                x   = torch.tensor(window[-self.input_window:], dtype=torch.float32)
                x   = x.unsqueeze(0).unsqueeze(-1)  # [1, T, 1]
                out = self.model(x).item()
                preds.append(out)
                window.append(out)

        return self._denormalize(np.array(preds))


def run_lstm_for_all_companies(df: pd.DataFrame) -> pd.DataFrame:
    """
    Run LSTM on each LSTM_FEATURE for each company.
    Returns same format as Prophet output.
    """
    all_rows = []
    companies = df["company_id"].unique()

    for company_id in tqdm(companies, desc="LSTM per company"):
        company_df = df[df["company_id"] == company_id].copy()
        company_df = company_df.sort_values("date")

        # Use the last known date as the forecast start
        if company_df.empty:
            continue
        last_date = company_df["date"].max()

        for feature in LSTM_FEATURES:
            if feature not in company_df.columns:
                continue

            series_vals = company_df.set_index("date")[feature].dropna()
            series_vals = series_vals.resample("MS").mean().dropna()

            if len(series_vals) < 15:
                continue   # not enough history for LSTM

            forecaster = LSTMForecaster(input_window=12, hidden_size=32)
            success = forecaster.fit(series_vals.values, epochs=80, lr=1e-3)
            if not success:
                continue

            forecasted_values = forecaster.predict(series_vals.values, steps=FORECAST_HORIZON)

            for i, val in enumerate(forecasted_values):
                future_date = last_date + pd.DateOffset(months=i + 1)
                all_rows.append({
                    "company_id": company_id,
                    "year":       future_date.year,
                    "month":      future_date.month,
                    "feature":    f"{feature}_forecast",
                    "value":      float(val),
                    "value_lower": None,
                    "value_upper": None,
                    "model":      "lstm",
                })

    return pd.DataFrame(all_rows)


# ─────────────────────────────────────────────────────────
# Merge forecasted features back into the feature matrix
# ─────────────────────────────────────────────────────────
def merge_forecasts_into_matrix(
    base_df: pd.DataFrame,
    forecast_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Pivot forecast_df wide and join to base_df.
    Adds columns like: headcount_forecast, news_sentiment_score_forecast, etc.
    """
    if forecast_df.empty:
        return base_df

    pivot = forecast_df.pivot_table(
        index=["company_id", "year", "month"],
        columns="feature",
        values="value",
        aggfunc="mean"
    ).reset_index()

    merged = base_df.merge(pivot, on=["company_id", "year", "month"], how="left")
    return merged


# ─────────────────────────────────────────────────────────
# Ablation: evaluate whether forecasted features improve AUC
# (run after Phase 4 modeling — this is the publishable finding)
# ─────────────────────────────────────────────────────────
def ablation_report(results: dict):
    """
    Print a comparison table: current features vs forecasted features.
    Input: dict of {label: {auc: float, cindex: float}}
    """
    print("\n📊 Ablation Study — Current vs Forecasted Features")
    print("─" * 50)
    print(f"{'Configuration':<30} {'AUC':>8} {'C-index':>10}")
    print("─" * 50)
    for label, metrics in results.items():
        auc    = f"{metrics.get('auc', 0):.4f}"
        cindex = f"{metrics.get('cindex', 0):.4f}"
        print(f"{label:<30} {auc:>8} {cindex:>10}")
    print("─" * 50)


# ─────────────────────────────────────────────────────────
# Main runner
# ─────────────────────────────────────────────────────────
def main(model_choice: str = "both"):
    print("🔮 Phase 3 — Signal Forecasting\n")

    # Load feature matrix from Phase 2
    matrix_path = os.path.join(PROCESSED_DIR, "feature_matrix_full.parquet")
    if not os.path.exists(matrix_path):
        raise FileNotFoundError(
            "Feature matrix not found. Run phase2_nlp/build_feature_matrix.py first."
        )

    df = pd.read_parquet(matrix_path)
    df["date"] = pd.to_datetime(df["date"])
    print(f"  Loaded {len(df):,} rows for {df['company_id'].nunique()} companies")

    all_forecasts = []

    if model_choice in ("prophet", "both"):
        print("\n🔵 Running Prophet forecasts...")
        prophet_forecasts = run_prophet_for_all_companies(df)
        print(f"  Generated {len(prophet_forecasts):,} Prophet forecast rows")
        prophet_forecasts.to_parquet(
            os.path.join(FORECAST_DIR, "prophet_forecasts.parquet"), index=False
        )
        all_forecasts.append(prophet_forecasts)

    if model_choice in ("lstm", "both"):
        print("\n🟠 Running LSTM forecasts...")
        lstm_forecasts = run_lstm_for_all_companies(df)
        print(f"  Generated {len(lstm_forecasts):,} LSTM forecast rows")
        lstm_forecasts.to_parquet(
            os.path.join(FORECAST_DIR, "lstm_forecasts.parquet"), index=False
        )
        all_forecasts.append(lstm_forecasts)

    if all_forecasts:
        combined_forecasts = pd.concat(all_forecasts, ignore_index=True)
        combined_forecasts.to_parquet(
            os.path.join(FORECAST_DIR, "all_forecasts.parquet"), index=False
        )

        # Merge forecasts into the feature matrix and save
        print("\n  Merging forecasted features into feature matrix...")
        df_with_forecasts = merge_forecasts_into_matrix(df, combined_forecasts)
        df_with_forecasts.to_parquet(
            os.path.join(PROCESSED_DIR, "feature_matrix_with_forecasts.parquet"),
            index=False
        )
        print(f"  Saved: feature_matrix_with_forecasts.parquet")
        print(f"  New feature columns: {[c for c in df_with_forecasts.columns if 'forecast' in c]}")

    print("\n✅ Phase 3 complete. Forecasts saved to data/forecasts/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=["prophet", "lstm", "both"], default="both")
    args = parser.parse_args()
    main(model_choice=args.model)
