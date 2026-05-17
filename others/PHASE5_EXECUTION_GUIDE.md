# Phase 5 — Execution Guide
# FastAPI Backend + React Frontend

---

## Prerequisites
- Phases 1–4 complete (models/ and data/ directories populated)
- Node.js 18+ installed  →  https://nodejs.org
- Docker Desktop installed (optional, for containerized run)

---

## Option A — Run locally (recommended while developing)

### Step 1 — Start the FastAPI backend

```bash
# From project root
cd phase5_app/backend

# Install backend deps (separate from phase 1-4 deps)
pip install -r requirements.txt

# Start the server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Expected output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

Test it works:
```bash
curl http://localhost:8000/api/health
# → {"status":"ok","timestamp":"..."}

curl http://localhost:8000/api/meta/stats
# → {"total_companies":33,"high_risk":...}

curl http://localhost:8000/api/companies | python -m json.tool | head -40
# → ranked company list with scores
```

---

### Step 2 — Start the React frontend

Open a NEW terminal tab:

```bash
cd phase5_app/frontend

# Install dependencies (first time only, takes ~1 min)
npm install

# Start dev server
npm run dev
```

Expected output:
```
  VITE v5.x.x  ready in 300ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: http://192.168.x.x:5173/
```

Open http://localhost:5173 in your browser.

---

### Step 3 — Verify all tabs work

On the Dashboard:
- [ ] Stats cards show company counts
- [ ] Risk leaderboard loads with scores
- [ ] Search and filters work
- [ ] Clicking a row navigates to company detail

On Company Detail:
- [ ] Overview tab: score gauge + score history chart
- [ ] SHAP tab: horizontal bar chart with feature attribution
- [ ] Forecasts tab: 6-month signal projection charts
- [ ] Analyst Brief tab: auto-generated memo with metrics

---

## Option B — Run with Docker Compose (production-like)

```bash
# From project root
docker-compose up --build

# Access:
# Dashboard  → http://localhost:5173
# API        → http://localhost:8000
# MLflow     → http://localhost:5000
# pgAdmin    → connect to localhost:5432
```

Note: First build takes 3-5 min. Subsequent starts are instant.

To stop:
```bash
docker-compose down          # stop containers
docker-compose down -v       # stop + wipe DB volumes (full reset)
```

---

## Step 4 — Build for production (deploy to AWS)

### 4a. Build React static files
```bash
cd phase5_app/frontend
npm run build
# Output: phase5_app/frontend/dist/
```

### 4b. Serve static files from FastAPI (optional)
Add to `main.py` before the routes:
```python
from fastapi.staticfiles import StaticFiles
app.mount("/", StaticFiles(directory="../frontend/dist", html=True), name="static")
```

Then everything runs on port 8000 — one server, no CORS needed.

### 4c. Deploy to AWS EC2

```bash
# 1. Launch EC2 instance (t3.medium, Ubuntu 22.04)
# 2. SSH in and install Docker
ssh -i your-key.pem ubuntu@your-ec2-ip

# Install Docker on EC2
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker ubuntu
logout  # then SSH back in

# 3. Copy project files (from your Mac)
# Exit EC2 first, run from local:
rsync -avz --exclude='venv' --exclude='node_modules' --exclude='.git' \
  ./ ubuntu@your-ec2-ip:~/supplier_distress/

# 4. SSH back in and start
ssh -i your-key.pem ubuntu@your-ec2-ip
cd ~/supplier_distress
docker-compose up -d --build

# 5. Open port 8000 in EC2 security group (AWS Console)
# Your app is now live at: http://your-ec2-ip:8000
```

---

## Troubleshooting

### "Model not found" on API startup
```bash
# Make sure you ran Phase 4 first
cd phase4_modeling
python train_models.py
# Check: ls -la ../models/
# Should see: xgboost_distress.json
```

### "feature_matrix_with_forecasts.parquet not found"
```bash
# Falls back to feature_matrix_full.parquet automatically
# Run Phase 3 to add forecasted features:
cd phase3_forecasting
python forecaster.py --model both
```

### CORS errors in browser console
```bash
# Make sure backend is running on :8000
# Check vite.config.js has proxy pointing to :8000
# Try restarting both servers
```

### React blank page
```bash
# Check browser console for errors
# Make sure npm install completed without errors
# Try: npm install && npm run dev
```

### Slow SHAP computation on company detail page
```bash
# SHAP recomputes on every /api/company/{id}/shap request
# Add caching to main.py if needed:
# pip install cachetools
# Use @lru_cache on get_shap_values()
```

---

## Final project structure
```
supplier_distress/
├── phase1_data/        ← data collection
├── phase2_nlp/         ← NLP extraction + feature matrix
├── phase3_forecasting/ ← Prophet + LSTM forecasts
├── phase4_modeling/    ← XGBoost + Cox PH + SHAP
├── phase5_app/
│   ├── backend/
│   │   ├── main.py         ← FastAPI app (9 endpoints)
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   └── frontend/
│       ├── src/
│       │   ├── App.jsx
│       │   ├── pages/
│       │   │   ├── Dashboard.jsx      ← leaderboard + filters
│       │   │   └── CompanyDetail.jsx  ← score + SHAP + forecast + brief
│       │   ├── components/
│       │   │   ├── Layout.jsx
│       │   │   └── UI.jsx
│       │   ├── hooks/useFetch.js
│       │   └── lib/api.js
│       ├── index.html
│       ├── package.json
│       ├── vite.config.js
│       └── tailwind.config.js
├── models/
│   └── xgboost_distress.json
├── data/
│   ├── processed/      ← feature matrices
│   └── forecasts/      ← Prophet + LSTM outputs
├── docker-compose.yml
└── requirements.txt
```

---

## Resume bullet (fill in your actual numbers)
```
Supplier Distress Predictor | FinBERT, Prophet, LSTM, XGBoost, Cox Survival, FastAPI, React

• Built early-warning system predicting supplier distress 6 months ahead using NLP
  signals (FinBERT sentiment, distress lexicon) + SEC financials across [X] companies —
  achieving XGBoost AUC [0.XX] and Cox C-index [0.XX]

• Engineered forward-looking features via Prophet + LSTM signal forecasting —
  ablation showed forecasted features improved AUC by [X] points over static signals

• Deployed production React dashboard + FastAPI backend on AWS EC2 with Docker/CI-CD;
  auto-generates SHAP-driven analyst briefs per supplier
```
