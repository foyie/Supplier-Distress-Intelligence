# Multi-stage build: Backend + minimal runtime

FROM python:3.11-slim as builder

WORKDIR /build

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the necessary modules for FastAPI
COPY phase1_data/db_schema.py ./phase1_data/
COPY phase4_modeling/train_models.py ./phase4_modeling/
COPY models/ ./models/
COPY data/ ./data/

# ─────────────────────────────────────────────────────────
# Runtime image
# ─────────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy app code
COPY phase5_backend/main.py ./main.py
COPY phase1_data/db_schema.py ./phase1_data/
COPY models/ ./models/

# Copy .env (should be provided at runtime via docker run -e)
ENV DATABASE_URL="postgresql://user:password@db:5432/supplier_distress"
ENV MLFLOW_TRACKING_URI="http://mlflow:5000"

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Start FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
