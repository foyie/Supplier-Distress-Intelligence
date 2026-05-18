# Phase 5 — Dashboard Execution Guide
# FastAPI Backend + React Frontend

---

## Prerequisites
- Phases 1–4 complete (data collected, models trained)
- Node.js 18+ installed  →  https://nodejs.org
- Docker Desktop (optional but recommended for prod)

---

## Option A: Local dev (fastest, recommended first)

### Step 1 — Start the FastAPI backend

```bash
cd phase5_dashboard/backend

# Install backend deps
pip install -r requirements.txt

# Make sure your .env is set (same one from Phase 1)
# Key vars: DB_HOST, DB_USER, DB_PASSWORD, DB_NAME

# Start the API server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Verify it works:
```bash
curl http://localhost:8000/stats
curl http://localhost:8000/companies | python3 -m json.tool | head -60
```

Open the auto-generated API docs:
→ http://localhost:8000/docs   (Swagger UI — great to show in your README)

---

### Step 2 — Start the React frontend

Open a NEW terminal:

```bash
cd phase5_dashboard/frontend

# Install npm packages (first time ~2 min)
npm install

# Start dev server
npm run dev
```

Open: http://localhost:3000

The Vite config proxies /api → http://localhost:8000 automatically.
So the frontend hits the backend with zero CORS issues.

---

## Option B: Docker Compose (production-like, great for demos)

```bash
cd phase5_dashboard

# Build and start everything (API + React + Postgres + MLflow)
docker compose up --build

# Frontend:  http://localhost:3000
# API docs:  http://localhost:8000/docs
# MLflow UI: http://localhost:5001
```

To stop:
```bash
docker compose down
```

To rebuild after code changes:
```bash
docker compose up --build --force-recreate
```

---

## Option C: Deploy to AWS EC2 (for public demo link)

```bash
# 1. SSH into your EC2 instance (t3.small is fine)
ssh -i your-key.pem ec2-user@your-ec2-ip

# 2. Install Docker + Docker Compose
sudo yum update -y
sudo yum install docker -y
sudo service docker start
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 3. Copy your project (from local machine)
scp -r -i your-key.pem ./supplier_distress ec2-user@your-ec2-ip:~/

# 4. SSH back in and run
cd ~/supplier_distress/phase5_dashboard
docker-compose up -d --build

# 5. Open port 3000 and 8000 in EC2 security group inbound rules
# Your dashboard is now live at: http://your-ec2-ip:3000
```

For a clean domain (optional):
```bash
# Point a subdomain to your EC2 IP in your DNS provider
# Then use nginx as reverse proxy:
sudo yum install nginx -y
# Configure /etc/nginx/conf.d/supplierwatch.conf to proxy :80 → :3000
```

---

## Troubleshooting

### "No companies" — blank leaderboard
The API loads data from data/processed/feature_matrix_with_forecasts.parquet
Make sure Phase 2 and 3 have been run. Check:
```bash
ls -lh ../../data/processed/
# Should see: feature_matrix_with_forecasts.parquet
```

### "Model not found" — risk scores are 0
XGBoost model loads from models/xgboost_distress.json
Make sure Phase 4 has been run:
```bash
ls -lh ../../models/
# Should see: xgboost_distress.json
```
If missing, the API falls back to a heuristic score — dashboard still works.

### React build errors
```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

### Port conflicts
If 8000 or 3000 are taken:
```bash
# Backend on different port
uvicorn main:app --reload --port 8001

# Frontend — edit vite.config.js
server: { port: 3001, proxy: { '/api': { target: 'http://localhost:8001' } } }
```

---

## What the dashboard shows (for your README/resume)

| Page              | What it demonstrates                                  |
|-------------------|-------------------------------------------------------|
| Risk Leaderboard  | 100 suppliers ranked by 6-month distress probability |
| Tier filters      | CRITICAL / HIGH / MEDIUM / LOW with live counts      |
| Signal Timeline   | Multi-signal interactive chart per supplier          |
| Forecast tab      | 6-month Prophet + LSTM projections with CI band      |
| SHAP tab          | Per-supplier feature attribution waterfall           |
| Analyst Brief     | Auto-generated procurement risk memo                 |
| API docs          | /docs — production REST API, fully documented        |

---

## Building for production (static frontend)

```bash
cd phase5_dashboard/frontend
npm run build
# Outputs to frontend/dist/

# Serve with nginx or any static host (Netlify, Vercel, S3+CloudFront)
# Point API calls to your EC2 backend URL
```

Edit `vite.config.js` before building for prod:
```js
// Replace proxy with absolute URL in production
// Or set VITE_API_BASE env var and use import.meta.env.VITE_API_BASE in api.js
```

---

## Resume bullet — what to write after this is live

```
• Deployed FastAPI + React dashboard on AWS EC2 with Docker/CI-CD serving
  risk scores, 6-month signal forecasts, and SHAP-driven analyst briefs
  for 100+ suppliers — accessible via live demo link
```
