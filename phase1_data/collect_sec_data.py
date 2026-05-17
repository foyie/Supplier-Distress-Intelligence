"""
Phase 1c — SEC EDGAR Financial Data Collector (FIXED v2)
=========================================================
Key fixes over v1:
  1. Broader concept fallback lists, including legacy/telecom-specific tags
  2. companyfacts bulk endpoint as second fallback (avoids per-concept 404s)
  3. Correct CIK overrides for post-bankruptcy ticker changes (FTR → FYBR)
  4. Extended ffill limit (12 months) so sparse annual filings fill monthly gaps
  5. Submissions-based fallback now pulls both 10-K AND 10-Q accession numbers
     and parses the R-file viewer for financial values
  6. Graceful minimum-data threshold: saves whatever rows exist (≥1 concept)

Usage:
    python collect_sec_data.py           # skip already-processed companies
    python collect_sec_data.py --force   # reprocess everyone
    python collect_sec_data.py --tickers FTR WIN SHLD PIR  # specific companies
"""

import os
import sys
import time
import math
import json
import argparse
import requests
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from db_schema import get_engine, Company, MonthlySignal

load_dotenv()

HEADERS  = {"User-Agent": "supplier-distress-project your@email.com"}
BASE_URL = "https://data.sec.gov"

# ─────────────────────────────────────────────────────────
# CIK overrides
# Some companies changed tickers or CIKs after bankruptcy.
# Map the OLD ticker (as stored in DB) → correct CIK to query.
# ─────────────────────────────────────────────────────────
CIK_OVERRIDES: dict[str, str] = {
    # Frontier Communications filed as FTR pre-bankruptcy; the reorganized
    # entity (FYBR) has a *different* CIK. We want the pre-bankruptcy filings.
    # CIK 0000020212 is the entity that filed 10-Ks through 2020.
    "FTR":  "0000020212",
    # Windstream: CIK 0001282266 is correct but keep here for clarity
    "WIN":  "0001282266",
    # Sears Holdings: CIK 0001310067 is correct
    "SHLD": "0001310067",
    # Pier 1: CIK 0000078239 is the operating entity (not holding company)
    "PIR":  "0000078239",
}

# ─────────────────────────────────────────────────────────
# Concept maps — primary + ordered fallbacks per metric
# Covers standard, legacy, and industry-specific XBRL tags
# ─────────────────────────────────────────────────────────
CONCEPT_FALLBACKS: dict[str, list[str]] = {
    "revenue": [
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueNet",
        "SalesRevenueGoodsNet",
        "RevenuesNetOfInterestExpense",
        "NetRevenues",
        "TotalRevenues",
        "OperatingRevenues",                     # telecoms (FTR, WIN)
        "TelecommunicationsRevenue",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
        "SalesRevenueServicesNet",
    ],
    "cash": [
        "CashAndCashEquivalentsAtCarryingValue",
        "CashCashEquivalentsAndShortTermInvestments",
        "CashAndCashEquivalents",
        "Cash",
        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
    ],
    "total_debt": [
        "LongTermDebtAndCapitalLeaseObligations",
        "LongTermDebt",
        "DebtAndCapitalLeaseObligations",
        "LongTermDebtNoncurrent",
        "LongTermDebtAndFinanceLeaseLiabilities",
        "LongTermNotesPayable",
    ],
    "stockholders_eq": [
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
        "LiabilitiesAndStockholdersEquity",      # last resort proxy
    ],
    "operating_income": [
        "OperatingIncomeLoss",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
        "OperatingIncomeLossFromContinuingOperations",
    ],
    "interest_expense": [
        "InterestExpense",
        "InterestAndDebtExpense",
        "InterestExpenseDebt",
        "InterestExpenseRelatedParty",
        "FinanceCostsNet",
    ],
    "current_liab": [
        "LiabilitiesCurrent",
        "LiabilitiesCurrentAndNoncurrent",
    ],
}


# ─────────────────────────────────────────────────────────
# Step 1: SEC ticker → CIK map
# ─────────────────────────────────────────────────────────
_ticker_map: dict = {}

def _load_ticker_map() -> dict:
    global _ticker_map
    if _ticker_map:
        return _ticker_map
    url = "https://www.sec.gov/files/company_tickers.json"
    r = requests.get(url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    for entry in r.json().values():
        ticker = entry["ticker"].upper()
        cik    = str(entry["cik_str"]).zfill(10)
        _ticker_map[ticker] = cik
    print(f"  📋 Loaded {len(_ticker_map):,} tickers from SEC")
    return _ticker_map

def get_cik(ticker: str) -> str | None:
    """Return CIK for ticker, respecting manual overrides."""
    t = ticker.upper()
    if t in CIK_OVERRIDES:
        return CIK_OVERRIDES[t]
    try:
        return _load_ticker_map().get(t)
    except Exception as e:
        print(f"  ⚠ CIK lookup error for {ticker}: {e}")
    return None


# ─────────────────────────────────────────────────────────
# Step 2a: Fetch one XBRL concept — companyconcept API
# ─────────────────────────────────────────────────────────
def fetch_concept(cik: str, concept: str, taxonomy: str = "us-gaap") -> pd.DataFrame:
    url = f"{BASE_URL}/api/xbrl/companyconcept/{cik}/{taxonomy}/{concept}.json"
    r   = requests.get(url, headers=HEADERS, timeout=15)
    if r.status_code != 200:
        return pd.DataFrame()

    rows = []
    for unit_key in ["USD", "shares", "pure"]:
        unit_data = r.json().get("units", {}).get(unit_key, [])
        for entry in unit_data:
            if entry.get("form") in ("10-K", "10-Q") and "end" in entry:
                rows.append({
                    "end_date": pd.to_datetime(entry["end"]),
                    "value":    entry.get("val"),
                    "form":     entry.get("form"),
                })
        if rows:
            break

    if not rows:
        return pd.DataFrame()

    df = (pd.DataFrame(rows)
            .dropna(subset=["value"])
            .sort_values("end_date")
            .drop_duplicates("end_date", keep="last"))
    return df

def fetch_concept_with_fallback(cik: str, key: str) -> pd.DataFrame:
    """Try every concept name for a given metric key."""
    for concept in CONCEPT_FALLBACKS.get(key, []):
        df = fetch_concept(cik, concept)
        if not df.empty:
            return df
        time.sleep(0.25)
    return pd.DataFrame()


# ─────────────────────────────────────────────────────────
# Step 2b: companyfacts bulk fallback
# Fetches ALL us-gaap facts in one call, then extracts what we need.
# Useful when companyconcept returns 404 for individual concepts.
# ─────────────────────────────────────────────────────────
def fetch_companyfacts_bulk(cik: str) -> dict[str, pd.DataFrame]:
    """
    Returns a dict of metric_key → DataFrame for whatever concepts exist.
    Empty dict if the endpoint fails.
    """
    url = f"{BASE_URL}/api/xbrl/companyfacts/{cik}.json"
    r   = requests.get(url, headers=HEADERS, timeout=30)
    if r.status_code != 200:
        return {}

    usgaap = r.json().get("facts", {}).get("us-gaap", {})
    results: dict[str, pd.DataFrame] = {}

    for key, concepts in CONCEPT_FALLBACKS.items():
        for concept in concepts:
            if concept not in usgaap:
                continue
            rows = []
            for unit_key in ["USD", "shares", "pure"]:
                unit_data = usgaap[concept].get("units", {}).get(unit_key, [])
                for entry in unit_data:
                    if entry.get("form") in ("10-K", "10-Q") and "end" in entry:
                        rows.append({
                            "end_date": pd.to_datetime(entry["end"]),
                            "value":    entry.get("val"),
                            "form":     entry.get("form"),
                        })
                if rows:
                    break
            if rows:
                df = (pd.DataFrame(rows)
                        .dropna(subset=["value"])
                        .sort_values("end_date")
                        .drop_duplicates("end_date", keep="last"))
                results[key] = df
                break   # found a working concept for this key

    return results


# ─────────────────────────────────────────────────────────
# Step 2c: Submissions-based fallback
# Walks actual 10-K/10-Q filings and reads the R2.htm interactive
# viewer tables that SEC hosts for every XBRL filing.
# This works even when companyconcept returns 404 for old filings.
# ─────────────────────────────────────────────────────────
def _parse_r_viewer_value(text: str, label_keywords: list[str]) -> float | None:
    """
    Very lightweight scraper for SEC's interactive R*.htm viewer pages.
    Looks for a labelled row and grabs the first numeric value after it.
    """
    import re
    text_lower = text.lower()
    for kw in label_keywords:
        idx = text_lower.find(kw.lower())
        if idx == -1:
            continue
        snippet = text[idx:idx+500]
        numbers = re.findall(r"[\$]?\s*([\-]?\d[\d,]*(?:\.\d+)?)", snippet)
        for n in numbers:
            try:
                val = float(n.replace(",", ""))
                if abs(val) > 1:          # skip single-digit noise
                    return val
            except ValueError:
                continue
    return None

def fetch_via_submissions(cik: str) -> dict[str, pd.DataFrame]:
    """
    Parse financial data from actual SEC filings via the submissions endpoint.
    Returns dict of metric_key → DataFrame (may be sparse).
    """
    sub_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    r = requests.get(sub_url, headers=HEADERS, timeout=15)
    if r.status_code != 200:
        return {}

    subs  = r.json()
    recent = subs.get("filings", {}).get("recent", {})
    forms      = recent.get("form", [])
    dates      = recent.get("filingDate", [])
    accessions = recent.get("accessionNumber", [])

    # Collect up to 20 10-K and 10-Q filings
    target_forms = {"10-K", "10-Q"}
    filings = [
        (d, f, a)
        for d, f, a in zip(dates, forms, accessions)
        if f in target_forms
    ][:20]

    if not filings:
        return {}

    # Metric → search keywords in the R-viewer HTML
    metric_keywords: dict[str, list[str]] = {
        "revenue":         ["total revenues", "net revenues", "revenues", "operating revenues"],
        "cash":            ["cash and cash equivalents", "cash equivalents"],
        "total_debt":      ["long-term debt", "total debt", "long term debt"],
        "stockholders_eq": ["total stockholders", "stockholders' equity", "shareholders' equity"],
        "operating_income":["operating income", "income from operations"],
        "interest_expense":["interest expense"],
        "current_liab":    ["total current liabilities", "current liabilities"],
    }

    cik_int = str(int(cik))
    records: dict[str, list[dict]] = {k: [] for k in metric_keywords}

    for filing_date, form, acc in filings:
        acc_clean = acc.replace("-", "")
        # Try R2.htm and R3.htm — these are the income statement / balance sheet
        for r_page in ["R2.htm", "R3.htm", "R4.htm", "R5.htm"]:
            url = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_clean}/{r_page}"
            try:
                rr = requests.get(url, headers=HEADERS, timeout=10)
                if rr.status_code != 200:
                    continue
                html = rr.text
                end_date = pd.to_datetime(filing_date)
                for key, keywords in metric_keywords.items():
                    val = _parse_r_viewer_value(html, keywords)
                    if val is not None:
                        records[key].append({"end_date": end_date, "value": val, "form": form})
                time.sleep(0.3)
            except Exception:
                continue
        time.sleep(0.5)

    result: dict[str, pd.DataFrame] = {}
    for key, rows in records.items():
        if rows:
            df = (pd.DataFrame(rows)
                    .sort_values("end_date")
                    .drop_duplicates("end_date", keep="last"))
            result[key] = df

    return result


# ─────────────────────────────────────────────────────────
# Step 3: Build monthly financial features
# Tries strategies in order: companyconcept → companyfacts → submissions
# ─────────────────────────────────────────────────────────
def build_financial_features(cik: str, ticker: str = "") -> pd.DataFrame:
    series: dict[str, pd.Series] = {}

    # ── Strategy 1: per-concept API (works for most companies) ────────────
    print(f"    [strategy 1] companyconcept API...")
    for key in CONCEPT_FALLBACKS:
        df = fetch_concept_with_fallback(cik, key)
        if not df.empty:
            s = df.set_index("end_date")["value"]
            series[key] = s
        time.sleep(0.2)

    # ── Strategy 2: companyfacts bulk (one request, all concepts) ─────────
    if len(series) < 2:
        print(f"    [strategy 2] companyfacts bulk endpoint...")
        bulk = fetch_companyfacts_bulk(cik)
        for key, df in bulk.items():
            if key not in series and not df.empty:
                series[key] = df.set_index("end_date")["value"]

    # ── Strategy 3: submissions R-viewer scraping ──────────────────────────
    if len(series) < 2:
        print(f"    [strategy 3] submissions R-viewer scraping...")
        sub_data = fetch_via_submissions(cik)
        for key, df in sub_data.items():
            if key not in series and not df.empty:
                series[key] = df.set_index("end_date")["value"]

    if not series:
        return pd.DataFrame()

    # Report what was found
    found = list(series.keys())
    missing = [k for k in CONCEPT_FALLBACKS if k not in series]
    print(f"    ✓ Found: {found}")
    if missing:
        print(f"    ✗ Missing: {missing}")

    # ── Resample to monthly, forward-fill up to 12 months ─────────────────
    # limit=12 (up from 3) so annual 10-K data fills the whole year
    combined = pd.DataFrame({
        k: s.resample("ME").last().ffill(limit=12)
        for k, s in series.items()
    })

    # ── Derived ratios ─────────────────────────────────────────────────────
    def safe_col(col):
        return combined[col].replace(0, float("nan")) if col in combined else pd.Series(
            float("nan"), index=combined.index)

    if "cash" in combined and "current_liab" in combined:
        combined["cash_ratio"]       = combined["cash"] / safe_col("current_liab")
    if "total_debt" in combined and "stockholders_eq" in combined:
        combined["debt_to_equity"]   = combined["total_debt"] / safe_col("stockholders_eq")
    if "operating_income" in combined and "revenue" in combined:
        combined["operating_margin"] = combined["operating_income"] / safe_col("revenue")
    if "operating_income" in combined and "interest_expense" in combined:
        combined["interest_coverage"]= combined["operating_income"] / safe_col("interest_expense")
    if "revenue" in combined:
        combined["revenue_qoq_pct"]  = combined["revenue"].pct_change(3) * 100

    combined["year"]  = combined.index.year
    combined["month"] = combined.index.month

    derived_cols = ["year", "month", "cash_ratio", "debt_to_equity",
                    "operating_margin", "interest_coverage", "revenue_qoq_pct"]
    keep = [c for c in derived_cols if c in combined.columns]

    # Keep rows that have at least one derived ratio (not all NaN)
    ratio_cols = [c for c in keep if c not in ("year", "month")]
    if not ratio_cols:
        return pd.DataFrame()

    return combined[keep].dropna(how="all", subset=ratio_cols)


# ─────────────────────────────────────────────────────────
# Step 4: Write to DB
# ─────────────────────────────────────────────────────────
def _safe_float(row, col):
    v = row.get(col)
    if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
        return None
    return float(v)

def upsert_financial_signals(session: Session, company_id: int, features: pd.DataFrame):
    for _, row in features.iterrows():
        existing = session.query(MonthlySignal).filter_by(
            company_id=company_id, year=int(row["year"]), month=int(row["month"])
        ).first()

        if existing is None:
            existing = MonthlySignal(
                company_id=company_id, year=int(row["year"]), month=int(row["month"])
            )
            session.add(existing)

        for col in ["cash_ratio", "debt_to_equity", "operating_margin",
                    "interest_coverage", "revenue_qoq_pct"]:
            if col in row:
                setattr(existing, col, _safe_float(row, col))

    session.commit()


# ─────────────────────────────────────────────────────────
# Main runner
# ─────────────────────────────────────────────────────────
def collect_all_sec_data(force: bool = False, tickers: list[str] | None = None):
    """
    Pull SEC financial data for all companies with tickers.

    Args:
        force:   if True, reprocess companies that already have signal rows.
        tickers: if provided, only process these tickers (e.g. ["FTR", "PIR"]).
    """
    engine = get_engine()
    with Session(engine) as session:
        query = session.query(Company).filter(Company.ticker.isnot(None))
        if tickers:
            query = query.filter(Company.ticker.in_([t.upper() for t in tickers]))
        companies = query.all()

        label = f"({', '.join(tickers)})" if tickers else "all"
        print(f"\n📊 Pulling SEC data for {len(companies)} companies {label}...\n")

        success, skipped, failed = 0, 0, 0

        for company in companies:
            # ── Skip if already processed ────────────────────────────────
            if not force:
                existing_count = session.query(MonthlySignal).filter_by(
                    company_id=company.id
                ).count()
                if existing_count > 0:
                    print(f"  ↩ {company.name} — already has {existing_count} rows, skipping")
                    skipped += 1
                    continue

            print(f"\n  → {company.name} ({company.ticker})")
            cik = get_cik(company.ticker)
            if not cik:
                print(f"    ⚠ Ticker '{company.ticker}' not found in SEC registry")
                failed += 1
                continue

            print(f"    CIK: {cik}")
            features = build_financial_features(cik, ticker=company.ticker)

            if features.empty:
                print(f"    ⚠ No financial data returned from any strategy")
                failed += 1
                continue

            # Filter to 2018–2024 window
            mask     = (features["year"] >= 2018) & (features["year"] <= 2024)
            features = features[mask]

            if features.empty:
                print(f"    ⚠ Data exists but none in 2018–2024 window")
                failed += 1
                continue

            upsert_financial_signals(session, company.id, features)
            print(f"    ✅ Saved {len(features)} monthly rows")
            success += 1
            time.sleep(1.2)

    print(f"\n{'='*50}")
    print(f"✅ SEC collection complete:")
    print(f"   {success} processed  |  {skipped} skipped  |  {failed} failed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true",
                        help="Reprocess companies that already have signal rows")
    parser.add_argument("--tickers", nargs="+", metavar="TICKER",
                        help="Only process specific tickers, e.g. --tickers FTR WIN SHLD PIR")
    args = parser.parse_args()
    collect_all_sec_data(force=args.force, tickers=args.tickers)
