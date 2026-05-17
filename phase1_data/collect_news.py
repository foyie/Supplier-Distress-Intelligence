"""
Phase 1d — News Data Collector (NewsAPI)
Pulls news headlines + descriptions for each company covering 2019–2024.
Stores raw articles for NLP processing in Phase 2.

Free tier: 100 requests/day → use GDELT fallback for bulk historical pulls.
GDELT is fully free and covers 2017–present.

Usage:
    python phase1_data/collect_news.py --source newsapi   # use NewsAPI (limited)
    python phase1_data/collect_news.py --source gdelt     # use GDELT (recommended for history)
"""

import os
import time
import argparse
import requests
import pandas as pd
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from db_schema import get_engine, Company, NewsRecord

load_dotenv()

NEWS_API_KEY = os.getenv("NEWS_API_KEY")


# ─────────────────────────────────────────────────────────
# Source A: NewsAPI (100 req/day free, 1 month lookback only)
# Good for: recent articles during active data collection
# ─────────────────────────────────────────────────────────
def fetch_newsapi(company_name: str, from_date: str, to_date: str) -> list[dict]:
    """
    Pull articles mentioning a company name within a date range.
    NewsAPI free tier only supports last 30 days — use GDELT for history.
    """
    if not NEWS_API_KEY:
        raise ValueError("NEWS_API_KEY not set in .env")

    url = "https://newsapi.org/v2/everything"
    params = {
        "q":        f'"{company_name}"',
        "from":     from_date,
        "to":       to_date,
        "language": "en",
        "sortBy":   "publishedAt",
        "pageSize": 100,
        "apiKey":   NEWS_API_KEY,
    }
    r = requests.get(url, params=params, timeout=10)
    if r.status_code != 200:
        print(f"    ⚠ NewsAPI error {r.status_code}: {r.text[:100]}")
        return []

    articles = r.json().get("articles", [])
    return [
        {
            "title":       a.get("title", ""),
            "description": a.get("description", ""),
            "source":      a.get("source", {}).get("name", ""),
            "url":         a.get("url", ""),
            "published":   a.get("publishedAt", "")[:10],
        }
        for a in articles if a.get("title")
    ]


# ─────────────────────────────────────────────────────────
# Source B: GDELT (fully free, full history from 2017)
# Recommended for historical backfill
# Docs: https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/
# ─────────────────────────────────────────────────────────
def fetch_gdelt(company_name: str, from_date: str, to_date: str) -> list[dict]:
    """
    Query GDELT DOC 2.0 API for news articles mentioning a company.
    Returns up to 250 articles per call. Paginate via date chunking.
    """
    url = "https://api.gdeltproject.org/api/v2/doc/doc"

    # Convert dates to GDELT format: YYYYMMDDHHMMSS
    start = from_date.replace("-", "") + "000000"
    end   = to_date.replace("-", "")   + "235959"

    params = {
        "query":      f'"{company_name}"',
        "mode":       "artlist",
        "maxrecords": 250,
        "startdatetime": start,
        "enddatetime":   end,
        "format":     "json",
        "timespan":   None,   # explicit start/end overrides this
    }
    # Remove None params
    params = {k: v for k, v in params.items() if v is not None}

    try:
        r = requests.get(url, params=params, timeout=20)
        if r.status_code != 200:
            return []
        data = r.json()
        articles = data.get("articles", [])
        return [
            {
                "title":       a.get("title", ""),
                "description": "",   # GDELT doesn't return body text
                "source":      a.get("domain", ""),
                "url":         a.get("url", ""),
                "published":   a.get("seendate", "")[:8],  # YYYYMMDD
            }
            for a in articles if a.get("title")
        ]
    except Exception as e:
        print(f"    ⚠ GDELT error: {e}")
        return []


# ─────────────────────────────────────────────────────────
# Iterate monthly chunks to avoid API limits
# ─────────────────────────────────────────────────────────
def collect_news_for_company(
    company: Company,
    source: str = "gdelt",
    start_year: int = 2019,
    end_year: int = 2024
) -> list[dict]:
    """Collect news month-by-month for a company to avoid API timeouts."""
    all_articles = []
    current = date(start_year, 1, 1)
    end     = date(end_year, 12, 31)

    while current <= end:
        month_end = min(current + relativedelta(months=1) - timedelta(days=1), end)
        from_str  = current.strftime("%Y-%m-%d")
        to_str    = month_end.strftime("%Y-%m-%d")

        if source == "newsapi":
            articles = fetch_newsapi(company.name, from_str, to_str)
        else:
            articles = fetch_gdelt(company.name, from_str, to_str)

        all_articles.extend(articles)
        current += relativedelta(months=1)
        time.sleep(1.5)  # be polite

    return all_articles


# ─────────────────────────────────────────────────────────
# Normalize published date across sources
# ─────────────────────────────────────────────────────────
def parse_date(raw: str) -> date | None:
    for fmt in ("%Y-%m-%d", "%Y%m%d", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(raw[:len(fmt.replace("%Y","2024").replace("%m","01").replace("%d","01").replace("%H","00").replace("%M","00").replace("%S","00"))], fmt).date()
        except Exception:
            continue
    return None


def save_news_records(session: Session, company_id: int, articles: list[dict]):
    """Deduplicate by URL before inserting."""
    existing_urls = {
        r.url for r in session.query(NewsRecord.url)
        .filter_by(company_id=company_id).all()
    }
    new_count = 0
    for a in articles:
        url = a.get("url", "")
        if url in existing_urls:
            continue
        record = NewsRecord(
            company_id  = company_id,
            published   = parse_date(a.get("published", "")),
            title       = a.get("title", "")[:500],
            description = a.get("description", "")[:1000] if a.get("description") else None,
            source      = a.get("source", "")[:200],
            url         = url[:500],
        )
        session.add(record)
        existing_urls.add(url)
        new_count += 1

    session.commit()
    return new_count


# ─────────────────────────────────────────────────────────
# Main runner
# ─────────────────────────────────────────────────────────
def collect_all_news(source: str = "gdelt"):
    engine = get_engine()
    with Session(engine) as session:
        companies = session.query(Company).all()
        print(f"📰 Pulling news for {len(companies)} companies via {source.upper()}...")

        for company in companies:
            print(f"\n  → {company.name}")
            articles = collect_news_for_company(company, source=source)
            saved = save_news_records(session, company.id, articles)
            print(f"    ✅ {saved} new articles saved ({len(articles)} total fetched)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=["newsapi", "gdelt"], default="gdelt")
    args = parser.parse_args()
    collect_all_news(source=args.source)
