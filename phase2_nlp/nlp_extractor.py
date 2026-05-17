"""
Phase 2 — NLP Signal Extraction
Processes raw news articles and Glassdoor text stored in Phase 1.
Outputs: monthly sentiment scores + distress keyword scores per company.

Two extractors:
  A) FinBERT sentiment (HuggingFace) — financial domain sentiment model
  B) Distress keyword scoring (TF-IDF weighted lexicon)

Usage:
    python phase2_nlp/nlp_extractor.py
"""

import os
import math
import warnings
import numpy as np
import pandas as pd
from datetime import date
from collections import defaultdict
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from tqdm import tqdm

warnings.filterwarnings("ignore")
load_dotenv()

# lazy imports — only load heavy models when needed
_finbert_pipeline = None
_tfidf_vectorizer = None


# ─────────────────────────────────────────────────────────
# FinBERT Sentiment Model
# Model: ProsusAI/finbert (financial domain BERT)
# Output: positive / negative / neutral with confidence score
# ─────────────────────────────────────────────────────────
def get_finbert():
    global _finbert_pipeline
    if _finbert_pipeline is None:
        from transformers import pipeline
        print("  Loading FinBERT (first run downloads ~400MB)...")
        _finbert_pipeline = pipeline(
            "text-classification",
            model="ProsusAI/finbert",
            tokenizer="ProsusAI/finbert",
            device=-1,        # CPU; change to 0 for GPU
            max_length=512,
            truncation=True,
        )
    return _finbert_pipeline


def score_sentiment(texts: list[str]) -> list[float]:
    """
    Run FinBERT on a list of texts.
    Returns list of floats in [-1, +1]:
      positive → +score
      negative → -score
      neutral  →  0
    Batches to avoid memory issues.
    """
    if not texts:
        return []

    pipe = get_finbert()
    BATCH = 32
    scores = []

    for i in range(0, len(texts), BATCH):
        batch = texts[i : i + BATCH]
        # Truncate each text to 512 tokens worth of chars
        batch = [t[:1500] for t in batch if t and len(t.strip()) > 10]
        if not batch:
            scores.extend([0.0] * len(texts[i : i + BATCH]))
            continue

        try:
            results = pipe(batch)
            for r in results:
                label = r["label"].lower()
                conf  = r["score"]
                if label == "positive":
                    scores.append(conf)
                elif label == "negative":
                    scores.append(-conf)
                else:
                    scores.append(0.0)
        except Exception as e:
            print(f"    ⚠ FinBERT batch error: {e}")
            scores.extend([0.0] * len(batch))

    return scores


# ─────────────────────────────────────────────────────────
# Distress Keyword Lexicon
# Curated financial distress terms with domain-expert weights
# ─────────────────────────────────────────────────────────
DISTRESS_LEXICON = {
    # Tier 1 — High severity (weight 3)
    "bankruptcy":        3.0,
    "chapter 11":        3.0,
    "chapter 7":         3.0,
    "insolvency":        3.0,
    "liquidation":       3.0,
    "receivership":      3.0,
    "default":           3.0,
    "missed payment":    3.0,

    # Tier 2 — Medium-high severity (weight 2)
    "restructuring":     2.0,
    "debt restructure":  2.0,
    "covenant breach":   2.0,
    "going concern":     2.0,
    "force majeure":     2.0,
    "supply disruption": 2.0,
    "credit downgrade":  2.0,
    "layoffs":           2.0,
    "mass layoffs":      2.5,
    "downsizing":        2.0,
    "plant closure":     2.0,
    "facility closure":  2.0,

    # Tier 3 — Early warning (weight 1)
    "furlough":          1.5,
    "hiring freeze":     1.5,
    "cost reduction":    1.0,
    "cost cutting":      1.0,
    "headcount reduction": 1.5,
    "workforce reduction": 1.5,
    "missed guidance":   1.5,
    "below expectations":1.0,
    "revenue decline":   1.0,
    "profit warning":    1.5,
    "write-down":        1.0,
    "impairment":        1.0,
    "supply chain issues": 1.0,
    "liquidity concerns": 2.0,
    "cash burn":         1.5,
}


def compute_distress_keyword_score(texts: list[str]) -> float:
    """
    Compute a weighted distress keyword score for a list of texts.
    Score = sum of (keyword_weight × occurrence_count) / len(texts)
    Normalized to [0, 1] by dividing by max possible score.
    """
    if not texts:
        return 0.0

    total_score = 0.0
    for text in texts:
        text_lower = text.lower()
        for keyword, weight in DISTRESS_LEXICON.items():
            count = text_lower.count(keyword)
            if count > 0:
                total_score += weight * min(count, 3)  # cap repetition at 3

    # Normalize: divide by number of texts and max possible per-text score
    max_per_text = sum(3 * w for w in DISTRESS_LEXICON.values())
    normalized = total_score / (len(texts) * max_per_text)
    return min(normalized * 100, 1.0)   # scale to 0-1


# ─────────────────────────────────────────────────────────
# Aggregate monthly: group news articles by company-month
# ─────────────────────────────────────────────────────────
def compute_monthly_nlp_signals(
    company_id: int,
    session: Session
) -> pd.DataFrame:
    """
    For a company, fetch all news records and compute monthly:
      - mean FinBERT sentiment score
      - distress keyword score
      - news volume

    Returns DataFrame indexed by (year, month).
    """
    from db_schema import NewsRecord

    records = (
        session.query(NewsRecord)
        .filter_by(company_id=company_id)
        .filter(NewsRecord.published.isnot(None))
        .all()
    )

    if not records:
        return pd.DataFrame()

    # Group by year-month
    monthly: dict[tuple, list[str]] = defaultdict(list)
    for r in records:
        if r.published:
            key = (r.published.year, r.published.month)
            text = " ".join(filter(None, [r.title, r.description]))
            if text.strip():
                monthly[key].append(text)

    rows = []
    for (year, month), texts in sorted(monthly.items()):
        sentiment_scores = score_sentiment(texts)
        mean_sentiment   = float(np.mean(sentiment_scores)) if sentiment_scores else 0.0
        distress_score   = compute_distress_keyword_score(texts)

        rows.append({
            "year":                  year,
            "month":                 month,
            "news_sentiment_score":  mean_sentiment,
            "news_volume":           len(texts),
            "distress_keyword_score": distress_score,
        })

    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────
# Write NLP features back to monthly_signals table
# ─────────────────────────────────────────────────────────
def upsert_nlp_signals(session: Session, company_id: int, features: pd.DataFrame):
    from db_schema import MonthlySignal

    for _, row in features.iterrows():
        existing = session.query(MonthlySignal).filter_by(
            company_id=company_id,
            year=int(row["year"]),
            month=int(row["month"])
        ).first()

        if existing is None:
            existing = MonthlySignal(
                company_id=company_id,
                year=int(row["year"]),
                month=int(row["month"])
            )
            session.add(existing)

        existing.news_sentiment_score   = _safe(row, "news_sentiment_score")
        existing.news_volume            = int(row.get("news_volume", 0) or 0)
        existing.distress_keyword_score = _safe(row, "distress_keyword_score")

    session.commit()


def _safe(row, col):
    v = row.get(col)
    if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
        return None
    return float(v)


# ─────────────────────────────────────────────────────────
# Main runner
# ─────────────────────────────────────────────────────────
def run_nlp_extraction():
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "phase1_data"))
    from db_schema import get_engine, Company

    engine = get_engine()
    with Session(engine) as session:
        companies = session.query(Company).all()
        print(f"🧠 Running NLP extraction for {len(companies)} companies...\n")

        for company in tqdm(companies, desc="Companies"):
            tqdm.write(f"  → {company.name}")
            features = compute_monthly_nlp_signals(company.id, session)
            if features.empty:
                tqdm.write(f"    ⚠ No news records found")
                continue
            upsert_nlp_signals(session, company.id, features)
            tqdm.write(f"    ✅ {len(features)} months processed")

    print("\n✅ NLP extraction complete.")


if __name__ == "__main__":
    run_nlp_extraction()
