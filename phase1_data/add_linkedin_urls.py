"""
Phase 1e-fix — Add LinkedIn URLs to existing companies
Run this once to populate the linkedin_url column so headcount
collection via Proxycurl works.

URLs are the public company LinkedIn pages (no auth needed to view).

Usage:
    python add_linkedin_urls.py
"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(__file__))
from db_schema import get_engine, Company

load_dotenv()

# ─────────────────────────────────────────────────────────
# LinkedIn company page URLs
# Format: https://www.linkedin.com/company/<slug>/
# Find slug by searching company on LinkedIn and copying the URL
# ─────────────────────────────────────────────────────────
LINKEDIN_URLS = {
    # ── Distressed ─────────────────────────────────────────
    "Bed Bath & Beyond":       "https://www.linkedin.com/company/bed-bath-and-beyond/",
    "Yellow Corporation":      "https://www.linkedin.com/company/yellow-corporation/",
    "SVB Financial":           "https://www.linkedin.com/company/silicon-valley-bank/",
    "Party City":              "https://www.linkedin.com/company/party-city/",
    "Avaya":                   "https://www.linkedin.com/company/avaya/",
    "Lordstown Motors":        "https://www.linkedin.com/company/lordstownmotors/",
    "Mallinckrodt":            "https://www.linkedin.com/company/mallinckrodt-pharmaceuticals/",
    "Hertz":                   "https://www.linkedin.com/company/hertz/",
    "JCPenney":                "https://www.linkedin.com/company/jcpenney/",
    "Chesapeake Energy":       "https://www.linkedin.com/company/chesapeake-energy/",
    "Frontier Communications": "https://www.linkedin.com/company/frontier-communications/",
    "Windstream Holdings":     "https://www.linkedin.com/company/windstream/",
    "Sears Holdings":          "https://www.linkedin.com/company/sears/",
    "iHeartMedia":             "https://www.linkedin.com/company/iheartmedia/",
    "Pier 1 Imports":          "https://www.linkedin.com/company/pier-1-imports/",

    # ── Healthy ────────────────────────────────────────────
    "Caterpillar":             "https://www.linkedin.com/company/caterpillar-inc-/",
    "Parker Hannifin":         "https://www.linkedin.com/company/parker-hannifin/",
    "Fastenal":                "https://www.linkedin.com/company/fastenal/",
    "Cintas":                  "https://www.linkedin.com/company/cintas/",
    "Graco":                   "https://www.linkedin.com/company/graco-inc-/",
    "Watts Water Tech":        "https://www.linkedin.com/company/watts-water-technologies/",
    "Roper Technologies":      "https://www.linkedin.com/company/roper-technologies/",
    "IDEX Corporation":        "https://www.linkedin.com/company/idex-corporation/",
    "Xylem":                   "https://www.linkedin.com/company/xylem-inc/",
    "Hubbell":                 "https://www.linkedin.com/company/hubbell-incorporated/",
    "Nordson":                 "https://www.linkedin.com/company/nordson-corporation/",
    "Donaldson Company":       "https://www.linkedin.com/company/donaldson-company/",
    "Allegion":                "https://www.linkedin.com/company/allegion/",
    "Rockwell Automation":     "https://www.linkedin.com/company/rockwell-automation/",
    "Ametek":                  "https://www.linkedin.com/company/ametek-inc-/",
    "Sensata Technologies":    "https://www.linkedin.com/company/sensata-technologies/",
    "Belden":                  "https://www.linkedin.com/company/belden/",
}


def add_linkedin_urls():
    engine = get_engine()
    updated = 0
    skipped = 0
    not_found = []

    with Session(engine) as session:
        companies = session.query(Company).all()

        for company in companies:
            url = LINKEDIN_URLS.get(company.name)
            if not url:
                not_found.append(company.name)
                continue
            if company.linkedin_url == url:
                skipped += 1
                continue
            company.linkedin_url = url
            updated += 1

        session.commit()

    print(f"✅ Updated {updated} companies with LinkedIn URLs")
    print(f"   Already set: {skipped}")
    if not_found:
        print(f"\n⚠  No URL found for {len(not_found)} companies:")
        for name in not_found:
            print(f"   - {name}")
        print("\n   Add their LinkedIn URLs to LINKEDIN_URLS dict above and re-run.")


if __name__ == "__main__":
    add_linkedin_urls()
