"""
Phase 1e — LinkedIn Signal Collector
Two sub-collectors:
  A) Headcount via Proxycurl API (structured, reliable, ~$0.01/call)
  B) Job postings via LinkedIn public search scraping (Playwright, no auth)

For a student project with ~100 companies × 36 months, Proxycurl cost ≈ $36 total.
Job posting scraping is free but requires Playwright + rotating delays.

Usage:
    python phase1_data/collect_linkedin.py --mode headcount
    python phase1_data/collect_linkedin.py --mode jobs
    python phase1_data/collect_linkedin.py --mode both
"""

import os
import time
import json
import random
import argparse
import requests
import pandas as pd
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from db_schema import get_engine, Company, MonthlySignal

load_dotenv()

PROXYCURL_KEY = os.getenv("PROXYCURL_API_KEY")


# ─────────────────────────────────────────────────────────
# A: Headcount via Proxycurl
# API docs: https://nubela.co/proxycurl/docs
# ─────────────────────────────────────────────────────────
def fetch_headcount_proxycurl(linkedin_url: str) -> dict | None:
    """
    Fetch current employee count + department breakdown.
    Returns dict with headcount and employee_count_by_role.
    """
    if not PROXYCURL_KEY:
        raise ValueError("PROXYCURL_API_KEY not set in .env")

    url = "https://nubela.co/proxycurl/api/linkedin/company"
    headers = {"Authorization": f"Bearer {PROXYCURL_KEY}"}
    params  = {
        "url":                          linkedin_url,
        "employee_count":               "include",
        "employee_count_by_role":       "include",
        "use_cache":                    "if-present",
    }
    r = requests.get(url, headers=headers, params=params, timeout=15)
    if r.status_code == 200:
        data = r.json()
        return {
            "headcount":        data.get("company_size_on_linkedin"),
            "follower_count":   data.get("follower_count"),
            "role_breakdown":   data.get("employee_count_by_role", {}),
        }
    else:
        print(f"    ⚠ Proxycurl error {r.status_code}: {r.text[:100]}")
        return None


# ─────────────────────────────────────────────────────────
# B: Job postings via Playwright (free, no auth needed)
# Scrapes public LinkedIn job search results
# ─────────────────────────────────────────────────────────
async def scrape_job_postings(company_name: str, page_limit: int = 3) -> list[dict]:
    """
    Scrape public LinkedIn job listings for a company.
    Returns list of job dicts with title, seniority, function, listed_date.

    Note: This uses public job search — no login required.
    Throttle requests: 2-4 seconds between pages.
    """
    from playwright.async_api import async_playwright

    jobs = []
    search_url = (
        f"https://www.linkedin.com/jobs/search/"
        f"?keywords={requests.utils.quote(company_name)}"
        f"&sortBy=DD"
    )

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()
        await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2000)

        for _ in range(page_limit):
            # Extract job cards
            cards = await page.query_selector_all(".base-card")
            for card in cards:
                try:
                    title = await card.query_selector(".base-search-card__title")
                    title_text = await title.inner_text() if title else ""

                    location = await card.query_selector(".job-search-card__location")
                    location_text = await location.inner_text() if location else ""

                    posted = await card.query_selector("time")
                    posted_text = await posted.get_attribute("datetime") if posted else ""

                    jobs.append({
                        "title":    title_text.strip(),
                        "location": location_text.strip(),
                        "posted":   posted_text[:10] if posted_text else "",
                    })
                except Exception:
                    continue

            # Try to load more results
            try:
                more_btn = await page.query_selector("button[aria-label='Load more results']")
                if more_btn:
                    await more_btn.click()
                    await page.wait_for_timeout(random.randint(2000, 4000))
                else:
                    break
            except Exception:
                break

        await browser.close()
    return jobs


def classify_job_roles(jobs: list[dict]) -> dict:
    """
    Classify jobs into ops/finance (warning signal) vs engineering/product.
    Rising ops/finance % is a leading indicator of cost-cutting mode.
    """
    ops_finance_keywords = {
        "operations", "procurement", "supply chain", "logistics",
        "finance", "accounting", "audit", "controller", "treasury",
        "restructuring", "turnaround", "cost reduction"
    }
    senior_keywords = {"director", "vp", "vice president", "chief", "head of", "senior manager"}

    total = len(jobs)
    if total == 0:
        return {"total": 0, "pct_ops_finance": None, "pct_senior": None}

    ops_count    = sum(1 for j in jobs if any(k in j["title"].lower() for k in ops_finance_keywords))
    senior_count = sum(1 for j in jobs if any(k in j["title"].lower() for k in senior_keywords))

    return {
        "total":            total,
        "pct_ops_finance":  ops_count    / total,
        "pct_senior":       senior_count / total,
    }


# ─────────────────────────────────────────────────────────
# Compute month-over-month deltas from snapshot history
# ─────────────────────────────────────────────────────────
def compute_headcount_features(snapshots: list[dict]) -> pd.DataFrame:
    """
    Given a list of {year, month, headcount} snapshots,
    compute MoM % change and 3-month rolling slope.
    """
    df = pd.DataFrame(snapshots).sort_values(["year", "month"])
    df["headcount_mom_pct"] = df["headcount"].pct_change() * 100
    df["headcount_3m_trend"] = df["headcount"].rolling(3).apply(
        lambda x: (x.iloc[-1] - x.iloc[0]) / max(x.iloc[0], 1) * 100,
        raw=False
    )
    return df


# ─────────────────────────────────────────────────────────
# Upsert into monthly_signals
# ─────────────────────────────────────────────────────────
def upsert_linkedin_signals(session: Session, company_id: int, features: pd.DataFrame):
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

        if "headcount"          in row: existing.headcount          = _safe(row, "headcount")
        if "headcount_mom_pct"  in row: existing.headcount_mom_pct  = _safe(row, "headcount_mom_pct")
        if "headcount_3m_trend" in row: existing.headcount_3m_trend = _safe(row, "headcount_3m_trend")
        if "total"              in row: existing.job_postings_total  = _safe(row, "total")
        if "pct_ops_finance"    in row: existing.pct_ops_finance_roles = _safe(row, "pct_ops_finance")
        if "pct_senior"         in row: existing.pct_senior_roles    = _safe(row, "pct_senior")

    session.commit()


def _safe(row, col):
    import math
    v = row.get(col)
    if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
        return None
    return float(v)


# ─────────────────────────────────────────────────────────
# Main runner
# ─────────────────────────────────────────────────────────
import asyncio

def collect_headcount(session: Session, companies: list):
    """Collect current headcount for all companies via Proxycurl."""
    today = date.today()
    for company in companies:
        if not company.linkedin_url:
            print(f"  ⚠ No LinkedIn URL for {company.name} — skipping")
            continue
        print(f"  → {company.name}")
        result = fetch_headcount_proxycurl(company.linkedin_url)
        if result and result.get("headcount"):
            snapshot = pd.DataFrame([{
                "year":     today.year,
                "month":    today.month,
                "headcount": result["headcount"]
            }])
            upsert_linkedin_signals(session, company.id, snapshot)
            print(f"    ✅ Headcount: {result['headcount']:,}")
        time.sleep(1)


def collect_jobs(session: Session, companies: list):
    """Scrape current job postings for all companies."""
    for company in companies:
        print(f"  → {company.name}")
        try:
            jobs = asyncio.run(scrape_job_postings(company.name))
            stats = classify_job_roles(jobs)
            today = date.today()

            # Guard: bankrupt/defunct companies may return 0 jobs → pct fields are None
            if stats["total"] == 0:
                print(f"    ⚠ 0 jobs found (company may be defunct) — skipping DB write")
                time.sleep(random.uniform(3, 6))
                continue

            snapshot = pd.DataFrame([{
                "year":            today.year,
                "month":           today.month,
                "total":           stats["total"],
                "pct_ops_finance": stats["pct_ops_finance"],
                "pct_senior":      stats["pct_senior"],
            }])
            upsert_linkedin_signals(session, company.id, snapshot)

            # Safe formatting: pct_ops_finance is guaranteed non-None here (total > 0)
            ops_pct = stats["pct_ops_finance"] or 0
            print(f"    ✅ {stats['total']} jobs | {ops_pct:.0%} ops/finance")
        except Exception as e:
            print(f"    ⚠ Error: {e}")
        time.sleep(random.uniform(3, 6))


def main(mode: str):
    engine = get_engine()
    with Session(engine) as session:
        companies = session.query(Company).all()
        print(f"🔗 LinkedIn collection ({mode}) for {len(companies)} companies...\n")

        if mode in ("headcount", "both"):
            print("── Headcount ─────────────────────────────────")
            collect_headcount(session, companies)

        if mode in ("jobs", "both"):
            print("\n── Job Postings ──────────────────────────────")
            collect_jobs(session, companies)

    print("\n✅ LinkedIn collection complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["headcount", "jobs", "both"], default="both")
    args = parser.parse_args()
    main(args.mode)
