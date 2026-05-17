# Supplier Distress Intelligence

**Early-warning system predicting supplier financial distress 6 months before it occurs.**

Built for procurement and supply chain risk teams at enterprise organizations. Combines financial statement analysis, NLP on alternative data sources, and forward-looking signal forecasting into a single risk score — served through a production React dashboard.

[Live Demo](https://your-demo-url.com) &nbsp;|&nbsp; [API Docs](https://your-demo-url.com/docs) &nbsp;|&nbsp; [Technical Write-up](#architecture)

---

## The Problem

Supply chain disruptions cost Fortune 500 companies an average of $184M annually. The challenge is not responding to supplier failures — it is anticipating them. By the time a bankruptcy filing appears, procurement teams have already lost leverage: alternative suppliers take 3–6 months to qualify, inventory buffers are depleted, and contractual protections are difficult to enforce retroactively.

Existing solutions rely on lagging indicators: credit ratings update quarterly, financial statements arrive 45–90 days after quarter close, and news coverage reports distress after markets have already repriced. This project builds a system that reads the leading signals — workforce changes, sentiment shifts, job posting patterns, SEC filing anomalies — and converts them into a time-aware distress probability score with a 6-month forward horizon.

---

## Results

| Metric | Value | Configuration |
|---|---|---|
| XGBoost AUC | **0.XX** | All features including forecasts |
| Cox PH C-index | **0.XX** | Time-to-distress survival model |
| AUC improvement | **+X.X pts** | Forecasted vs static features (ablation) |
| Precision @ threshold 0.65 | **0.XX** | High-risk tier |
| Backtest folds | 3 | Rolling walk-forward, 2019–2023 |

**Ablation study — signal source comparison:**

| Feature Set | AUC | C-index |
|---|---|---|
| Financial signals only (SEC) | 0.XX | 0.XX |
| NLP signals only (FinBERT + lexicon) | 0.XX | 0.XX |
| All current signals | 0.XX | 0.XX |
| All signals + 6-month forecasts (full model) | **0.XX** | **0.XX** |

> Replace placeholder values with your actual results after running Phase 4.
> The ablation delta (row 3 vs row 4) is the headline finding — this is what forward-looking features contribute.

**Top SHAP features by mean absolute impact:**

| Rank | Feature | Signal Type | Direction |
|---|---|---|---|
| 1 | `distress_keyword_score` | NLP | Risk |
| 2 | `cash_ratio` | Financial | Protective |
| 3 | `news_sentiment_score_forecast` | NLP Forecast | Risk |
| 4 | `headcount_mom_pct` | LinkedIn | Risk |
| 5 | `debt_to_equity` | Financial | Risk |
| 6 | `pct_ops_finance_roles_forecast` | Job Data Forecast | Risk |
| 7 | `operating_margin` | Financial | Protective |
| 8 | `glassdoor_rating` | Alternative Data | Protective |

---

## Architecture

```
Raw Data Sources
      │
      ├── SEC EDGAR API          (10-K / 10-Q filings, free, no key)
      ├── GDELT / NewsAPI        (news headlines, 2019–2024)
      ├── Proxycurl API          (LinkedIn headcount snapshots)
      └── LinkedIn public scrape (job posting velocity, role mix)
      │
      ▼
Phase 1 — Data Pipeline
      PostgreSQL schema · SQLAlchemy ORM · Playwright scraping
      │
      ▼
Phase 2 — NLP Extraction
      FinBERT sentiment (ProsusAI/finbert, HuggingFace)
      TF-IDF distress keyword lexicon (custom, 30 terms, tiered weights)
      Job posting feature engineering (ops/finance %, seniority shift)
      │
      ▼
Phase 3 — Signal Forecasting                ← key differentiator
      Prophet  →  slow-moving signals (headcount, financials, Glassdoor)
      LSTM     →  noisy sequential signals  (sentiment, news volume)
      Output:  6-month forward projection per signal per company
      │
      ▼
Phase 4 — Risk Modeling
      XGBoost classifier      →  P(distress within 6 months)
      Cox PH survival model   →  time-to-distress (C-index)
      SHAP explainability     →  per-company feature attribution
      Rolling backtest        →  walk-forward validation, no leakage
      MLflow                  →  experiment tracking, model registry
      │
      ▼
Phase 5 — Production Deployment
      FastAPI backend  →  9 REST endpoints, inference on demand
      React frontend   →  dashboard, SHAP waterfall, forecast charts
      Docker + EC2     →  containerized deployment, CI/CD via GitHub Actions
```

The critical design decision: **signals are forecasted before scoring**. Rather than asking "where is this company today?", the model asks "where is this company heading?" This is the distinction between a rearview mirror and a leading indicator.

---

## Technical Stack

**Data & Storage**
- PostgreSQL — primary data store (companies, monthly signals, news records)
- SQLAlchemy — ORM with upsert logic and temporal schema
- SEC EDGAR XBRL API — structured financial extraction, 7 concepts, 5 derived ratios
- GDELT DOC 2.0 — free news archive, 2017–present

**NLP**
- `ProsusAI/finbert` — financial domain BERT, outperforms general-purpose models on earnings sentiment
- Custom distress lexicon — 30 terms across 3 severity tiers, TF-IDF weighted
- spaCy + NLTK — preprocessing pipeline

**Forecasting**
- Prophet — additive decomposition, changepoint detection, handles trend + seasonality
- PyTorch LSTM — single-layer, autoregressive inference, trained per company-feature pair
- Signal routing: Prophet for slow-moving structural signals, LSTM for noisy sequential signals

**Modeling**
- XGBoost — binary classifier with `scale_pos_weight` for class imbalance
- scikit-survival — Cox PH with Efron tie-breaking, normalized features
- SHAP TreeExplainer — global importance + per-company waterfall attribution
- Evaluation: AUC-ROC (classification), concordance index (survival), AUPRC (imbalanced)
- MLflow — full experiment tracking, metric logging, model artifact registry

**Application**
- FastAPI — async REST API, Pydantic validation, auto-generated OpenAPI docs
- React 18 — functional components, custom `useFetch` hook, React Router
- Recharts — score history line chart, SHAP horizontal bar chart, forecast line charts
- Tailwind CSS — utility-first styling, responsive layout
- Docker + Docker Compose — containerized backend, PostgreSQL, MLflow
- AWS EC2 — production deployment

---

## Dataset

- **Companies:** ~33 US public companies (15 distressed, 18 healthy controls)
- **Time period:** January 2018 – December 2023 (72 months)
- **Signal rows:** ~2,400 company-month observations
- **News records:** 50,000+ headlines across all companies
- **Distress events:** 15 verified bankruptcy/restructuring events, labeled by filing date
- **Label methodology:** event = 1 if distress occurred, duration = months from observation to event (survival framing)
- **Train/test split:** strict temporal — train ≤ 2021, test 2022–2023, no future leakage

Distress events sourced from: BankruptcyData.com, SEC EDGAR filings, Reuters/WSJ coverage.

---

## Why Forward-Looking Features Matter

Standard approaches to supplier risk modeling treat the feature matrix as a snapshot — you score the company based on where it is today. The fundamental problem is that distress compounds: sentiment deteriorates before headcount falls, headcount falls before revenue declines, revenue declines before a covenant breach. By the time the financial signal is observable, the leading signals have already moved.

This project forecasts each signal 6 months forward using Prophet (structural signals) and LSTM (sequential signals), then uses the projected values as model features. The ablation study quantifies the value of this design: forecasted features improve AUC by X.X points over static features using identical model architecture. This is the publishable finding.

---

## Procurement Use Case

The dashboard is designed around how a procurement risk analyst actually works:

**Risk Leaderboard** — sorted by distress probability, with month-over-month delta. An analyst reviewing 200 suppliers can triage in minutes rather than days.

**SHAP Attribution** — for each supplier, the model explains which signals are driving the score. "Debt/equity rising + ops-role hiring surging + sentiment declining" is an actionable brief. A black-box probability score is not.

**Analyst Brief** — auto-generated one-page memo per supplier: risk tier, key drivers, financial indicators, recommendation. Replicates the output of a manual credit review.

**Forecast Charts** — 6-month signal projections per supplier show trajectory, not just current state. A supplier with a moderate score but rapidly deteriorating sentiment forecast requires a different response than one with a stable profile.

Real customers: procurement teams at Fortune 500 manufacturers, commercial lending teams assessing supplier credit exposure, supply chain hedge funds using alternative data, enterprise risk management platforms.

---

## Project Structure

```
supplier-distress-intelligence/
│
├── phase1_data/                    Data collection pipeline
│   ├── db_schema.py                PostgreSQL schema (Company, MonthlySignal, NewsRecord)
│   ├── seed_companies.py           Company registry with ground-truth distress labels
│   ├── collect_sec_data.py         SEC EDGAR XBRL financial data collector
│   ├── collect_news.py             GDELT + NewsAPI news collector (monthly chunking)
│   └── collect_linkedin.py         Headcount (Proxycurl) + job postings (Playwright)
│
├── phase2_nlp/                     NLP signal extraction
│   ├── nlp_extractor.py            FinBERT sentiment + distress keyword scoring
│   └── build_feature_matrix.py     Feature engineering, imputation, survival labels
│
├── phase3_forecasting/             Signal forecasting
│   └── forecaster.py               Prophet (structural) + LSTM (sequential) per company
│
├── phase4_modeling/                Risk modeling
│   └── train_models.py             XGBoost + Cox PH + SHAP + ablation + MLflow tracking
│
├── phase5_app/                     Production application
│   ├── backend/
│   │   ├── main.py                 FastAPI — 9 REST endpoints
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   └── frontend/
│       ├── src/
│       │   ├── App.jsx             React Router setup
│       │   ├── pages/
│       │   │   ├── Dashboard.jsx   Risk leaderboard with filters + search
│       │   │   └── CompanyDetail.jsx  Score history, SHAP, forecasts, analyst brief
│       │   ├── components/
│       │   │   ├── Layout.jsx      Nav + page shell
│       │   │   └── UI.jsx          TierBadge, ScoreGauge, DeltaChip, Skeleton
│       │   ├── hooks/
│       │   │   └── useFetch.js     Data fetching with loading/error states
│       │   └── lib/
│       │       └── api.js          Typed API client for all backend endpoints
│       ├── index.html
│       ├── package.json
│       ├── vite.config.js          Dev proxy → :8000
│       └── tailwind.config.js
│
├── data/
│   ├── processed/                  Feature matrices (parquet + CSV)
│   └── forecasts/                  Prophet + LSTM output per company
│
├── models/
│   └── xgboost_distress.json       Trained XGBoost model artifact
│
├── docker-compose.yml              PostgreSQL + FastAPI + MLflow
├── requirements.txt                Python dependencies (phases 1–4)
├── .env.example                    Environment variable template
└── README.md
```

---

## Reproducing Results

```bash
# 1. Clone and set up environment
git clone https://github.com/yourusername/supplier-distress-intelligence
cd supplier-distress-intelligence
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Fill in: DB credentials, NewsAPI key, Proxycurl key

# 3. Set up database
createdb supplier_distress
cd phase1_data
python db_schema.py
python seed_companies.py

# 4. Collect data (takes 3–4 hours total)
python collect_sec_data.py          # ~30 min, free
python collect_news.py --source gdelt  # ~2 hrs, free
python collect_linkedin.py --mode both # ~20 min, Proxycurl key required

# 5. NLP extraction + feature matrix
cd ../phase2_nlp
python nlp_extractor.py             # ~60 min (FinBERT)
python build_feature_matrix.py      # ~5 min

# 6. Forecasting
cd ../phase3_forecasting
mlflow server --port 5000 &         # start MLflow
python forecaster.py --model both   # ~30 min

# 7. Modeling + ablation
cd ../phase4_modeling
python train_models.py --ablation

# 8. Run the application
cd ../phase5_app/backend
uvicorn main:app --reload --port 8000 &

cd ../frontend
npm install && npm run dev
# Open http://localhost:5173
```

---

## Limitations and Future Work

- **Sample size:** 33 companies is sufficient for a proof-of-concept but would require expansion to 500+ for production deployment. The dataset is intentionally curated rather than exhaustive.
- **LinkedIn data:** Headcount snapshots are point-in-time rather than continuous. Historical series were approximated using GDELT job posting proxies for pre-2022 periods.
- **Sector generalization:** The model was trained on a mix of sectors. A sector-specific model (e.g., retail vs. industrial) would likely outperform on within-sector predictions.
- **Label quality:** Distress is defined as formal bankruptcy or restructuring filing. Pre-distress states (covenant waivers, credit line drawdowns) are not captured.

Planned extensions: real-time news ingestion via Kafka, sector-specific survival models, alternative data integration (satellite imagery, web traffic proxies), confidence intervals on risk scores via conformal prediction.

---

## Publication

This project applies the survival modeling framing introduced in:

- Cox, D.R. (1972). *Regression models and life tables.* Journal of the Royal Statistical Society.
- Lundberg, S.M. & Lee, S.I. (2017). *A unified approach to interpreting model predictions.* NeurIPS.
- Yang, Y. et al. (2020). *FinBERT: A pretrained language model for financial communications.*

---

## Author

**Chandrima Das**
MS Data Science, UC San Diego
[LinkedIn](https://linkedin.com/in/foyie) &nbsp;|&nbsp; [Website](https://foyie.github.io/foyie/) &nbsp;|&nbsp; [chdas@ucsd.edu](mailto:chdas@ucsd.edu)
