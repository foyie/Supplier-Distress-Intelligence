# Supplier Distress Predictor — Execution Guide

## Prerequisites
- Python 3.10+
- PostgreSQL 14+ running locally
- Git

---

## 0. One-time setup

```bash
# Clone / create project folder
cd supplier_distress

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate          # Mac/Linux
# venv\Scripts\activate           # Windows

# Install all dependencies
pip install -r requirements.txt

# Install Playwright browsers (for LinkedIn scraping)
playwright install chromium

# Install spaCy English model
python -m spacy download en_core_web_sm

# Copy and fill in your .env
cp .env.example .env
# Edit .env: add DB credentials, NewsAPI key, Proxycurl key
```

---

## 1. Set up PostgreSQL

```bash
# Create database (run in psql or pgAdmin)
createdb supplier_distress

# OR in psql:
psql -U postgres
CREATE DATABASE supplier_distress;
\q
```

---

## PHASE 1 — Data Collection (Weeks 1–2)

### 1a. Create database tables
```bash
cd phase1_data
python db_schema.py
# ✅ Expected: "All tables created successfully."
```

### 1b. Seed the company list
```bash
python seed_companies.py
# ✅ Expected: "Seeded 40 companies"
```

### 1c. Pull SEC financial data (free, no API key needed)
```bash
python collect_sec_data.py
# ⏱ Takes ~20-40 min for 40 companies (SEC rate limits)
# ✅ Expected: monthly financial rows per company
```

### 1d. Pull news articles (GDELT = free, full history)
```bash
python collect_news.py --source gdelt
# ⏱ Takes ~2-3 hours for all companies (polite throttling)
# ✅ Expected: thousands of news records per company

# Alternative: use NewsAPI for recent articles only (faster)
# python collect_news.py --source newsapi
```

### 1e. Collect LinkedIn signals
```bash
# Headcount via Proxycurl (costs ~$0.40 for 40 companies)
python collect_linkedin.py --mode headcount

# Job postings via Playwright (free, slower)
python collect_linkedin.py --mode jobs

# Or both at once
python collect_linkedin.py --mode both
# ⏱ Jobs scraping: ~10-20 min depending on throttling
```

### ✅ Phase 1 checkpoint
Open pgAdmin or run:
```sql
SELECT c.name, COUNT(ms.id) as signal_rows, COUNT(nr.id) as news_rows
FROM companies c
LEFT JOIN monthly_signals ms ON ms.company_id = c.id
LEFT JOIN news_records nr ON nr.company_id = c.id
GROUP BY c.name
ORDER BY signal_rows DESC;
```
You should see 20-36 monthly signal rows per company and 50-500+ news records.

---

## PHASE 2 — NLP Extraction (Weeks 2–3)

### 2a. Run FinBERT sentiment + distress keyword extraction
```bash
cd ../phase2_nlp
python nlp_extractor.py
# ⏱ Takes 30-90 min (FinBERT downloads ~400MB on first run)
# ✅ Expected: news_sentiment_score + distress_keyword_score populated in DB
```

### 2b. Build the feature matrix
```bash
python build_feature_matrix.py
# ⏱ Takes 2-5 min
# ✅ Expected output in data/processed/:
#   - feature_matrix_full.parquet
#   - train.parquet
#   - test.parquet
#   - feature_matrix_full.csv   (for Excel inspection)
```

### ✅ Phase 2 checkpoint
```python
import pandas as pd
df = pd.read_parquet("data/processed/feature_matrix_full.parquet")
print(df.shape)                        # should be (1000+, 25+)
print(df["label_6m"].value_counts())   # check distress rate ~20-35%
print(df.isnull().mean().sort_values(ascending=False).head(10))  # check coverage
```

---

## PHASE 3 — Signal Forecasting (Weeks 3–4)

### 3a. Start MLflow tracking server (in a separate terminal)
```bash
mlflow server --host 127.0.0.1 --port 5000
# Keep this running. Open http://localhost:5000 to see experiments.
```

### 3b. Run Prophet + LSTM forecasting
```bash
cd ../phase3_forecasting

# Run both models (recommended)
python forecaster.py --model both

# Or run separately to debug
python forecaster.py --model prophet   # faster (~5 min)
python forecaster.py --model lstm      # slower (~20-40 min)

# ✅ Expected output in data/forecasts/:
#   - prophet_forecasts.parquet
#   - lstm_forecasts.parquet
#   - all_forecasts.parquet
# And in data/processed/:
#   - feature_matrix_with_forecasts.parquet
```

### ✅ Phase 3 checkpoint
```python
import pandas as pd
forecasts = pd.read_parquet("data/forecasts/all_forecasts.parquet")
print(forecasts["model"].value_counts())        # prophet vs lstm counts
print(forecasts["feature"].unique())            # which features were forecasted
print(forecasts.groupby("model")["value"].describe())  # sanity check values
```

---

## PHASE 4 — Modeling (Weeks 4–6)

### 4a. Train full model (XGBoost + Cox PH + SHAP)
```bash
cd ../phase4_modeling
python train_models.py
# ⏱ Takes 10-20 min
# ✅ Expected:
#   XGBoost AUC: ~0.78-0.84
#   Cox C-index: ~0.70-0.76
#   Models saved to models/
#   SHAP plots saved to data/plots/
```

### 4b. Run ablation study (the publishable finding)
```bash
python train_models.py --ablation
# ✅ Expected: table comparing 4 feature configurations
# KEY RESULT: forecasted features should improve AUC by 3-8 points
# This is your headline result for the resume and README
```

### ✅ Phase 4 checkpoint — view in MLflow
Open http://localhost:5000
- Click "supplier_distress_main" experiment
- Compare runs: xgboost_full, cox_ph_full, ablation configs
- Download SHAP plots from artifacts tab

---

## Tips for when things go wrong

### PostgreSQL connection errors
```bash
# Check PostgreSQL is running
brew services start postgresql@14    # Mac
sudo service postgresql start        # Linux

# Test connection
psql -U postgres -d supplier_distress -c "SELECT COUNT(*) FROM companies;"
```

### FinBERT memory errors (low RAM)
In `phase2_nlp/nlp_extractor.py`, reduce batch size:
```python
BATCH = 8   # change from 32
```

### GDELT returning empty results
GDELT can be slow during peak hours. Try:
```python
time.sleep(3)   # increase sleep between requests in collect_news.py
```
Or fall back to NewsAPI for recent data + manually download GDELT CSVs
from https://gdelt.github.io for historical.

### Prophet convergence warnings
Normal for short series (<12 months). The model still produces
a forecast — warnings don't indicate failure.

### LSTM overfitting (train AUC >> test AUC)
Reduce epochs or increase dropout:
```python
forecaster = LSTMForecaster(input_window=12, hidden_size=16)   # smaller
forecaster.fit(series, epochs=30)   # fewer epochs
```

---

## Project structure after all phases
```
supplier_distress/
├── phase1_data/
│   ├── db_schema.py
│   ├── seed_companies.py
│   ├── collect_sec_data.py
│   ├── collect_news.py
│   └── collect_linkedin.py
├── phase2_nlp/
│   ├── nlp_extractor.py
│   └── build_feature_matrix.py
├── phase3_forecasting/
│   └── forecaster.py
├── phase4_modeling/
│   └── train_models.py
├── data/
│   ├── raw/
│   ├── processed/          ← parquet feature matrices
│   ├── forecasts/          ← Prophet + LSTM outputs
│   └── plots/              ← SHAP visualizations
├── models/
│   └── xgboost_distress.json
├── requirements.txt
└── .env
```

---

## Resume bullets you can fill in after running
After you have real results, update the template in the build plan:

```
• Built early-warning system predicting supplier distress 6 months ahead
  using NLP signals (FinBERT sentiment, distress lexicon) + SEC financials
  across [X] companies — achieving XGBoost AUC [YOUR RESULT]

• Engineered forward-looking features via Prophet + LSTM signal forecasting —
  ablation showed forecasted features improved AUC by [X] points over static signals

• Combined XGBoost classifier + Cox PH survival model (C-index [YOUR RESULT])
  with SHAP explainability; deployed FastAPI + React dashboard on AWS
```
