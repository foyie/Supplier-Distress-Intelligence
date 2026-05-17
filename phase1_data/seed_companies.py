"""
Phase 1b — Seed Company List
A curated list of ~40 US companies including known distress events (2018–2023)
for ground truth labels.

Changes from v1:
  - Removed 5 companies with missing XBRL data (Revlon, Rite Aid, Tupperware,
    Joann, Cineworld) — replaced with verified alternatives
  - Removed 3 duplicate Watts Water entries (all resolved to same CIK)
  - Added cleanup_duplicates() to remove any existing duplicate DB rows

Distress events sourced from:
  - BankruptcyData.com
  - S&P Capital IQ (public summaries)
  - Reuters/WSJ coverage

Usage:
    python seed_companies.py              # seed + cleanup
    python seed_companies.py --cleanup    # cleanup duplicates only
"""

import os
import argparse
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.orm import Session
from db_schema import get_engine, Company, MonthlySignal

load_dotenv()

# ─────────────────────────────────────────────────────────
# Removed (no XBRL data):
#   Revlon (REV)     → 404 companyfacts (delisted post-bankruptcy)
#   Rite Aid (RAD)   → 404 companyfacts
#   Tupperware (TUP) → 404 companyfacts
#   Joann Inc (JOAN) → 404 companyfacts
#   Cineworld (CNNWF)→ UK company, no SEC filing
#
# Removed duplicates (same CIK 0000795403):
#   "Watts Water", "Watts Water Systems", "Watts Water Technol"
#   → kept "Watts Water Tech" only
# ─────────────────────────────────────────────────────────

COMPANIES = [
    # ── Distressed companies (verified XBRL data) ─────────────────────────
    {"name": "Bed Bath & Beyond",        "ticker": "BBBY", "industry": "Retail",          "sector": "Retail",        "distress_label": True,  "distress_date": "2023-04-23"},
    {"name": "Yellow Corporation",       "ticker": "YELL", "industry": "Trucking",         "sector": "Logistics",     "distress_label": True,  "distress_date": "2023-08-06"},
    {"name": "SVB Financial",            "ticker": "SIVB", "industry": "Banking",          "sector": "Finance",       "distress_label": True,  "distress_date": "2023-03-10"},
    {"name": "Party City",               "ticker": "PRTY", "industry": "Retail",           "sector": "Retail",        "distress_label": True,  "distress_date": "2023-01-17"},
    {"name": "Avaya",                    "ticker": "AVYA", "industry": "Technology",        "sector": "Tech",          "distress_label": True,  "distress_date": "2023-02-14"},
    {"name": "Lordstown Motors",         "ticker": "RIDE", "industry": "Automotive",        "sector": "Manufacturing", "distress_label": True,  "distress_date": "2023-06-27"},
    {"name": "Mallinckrodt",             "ticker": "MNK",  "industry": "Pharma",            "sector": "Healthcare",    "distress_label": True,  "distress_date": "2020-10-12"},
    {"name": "Hertz",                    "ticker": "HTZ",  "industry": "Auto Rental",       "sector": "Services",      "distress_label": True,  "distress_date": "2020-05-22"},
    {"name": "JCPenney",                 "ticker": "JCP",  "industry": "Retail",            "sector": "Retail",        "distress_label": True,  "distress_date": "2020-05-15"},
    {"name": "Chesapeake Energy",        "ticker": "CHK",  "industry": "Energy",            "sector": "Energy",        "distress_label": True,  "distress_date": "2020-06-28"},

    # ── Replacements for the 5 failed companies ────────────────────────────
    {"name": "Frontier Communications",  "ticker": "FTR",  "industry": "Telecom",           "sector": "Services",      "distress_label": True,  "distress_date": "2019-04-14"},
    {"name": "Windstream Holdings",      "ticker": "WIN",  "industry": "Telecom",           "sector": "Services",      "distress_label": True,  "distress_date": "2019-02-25"},
    {"name": "Sears Holdings",           "ticker": "SHLD", "industry": "Retail",            "sector": "Retail",        "distress_label": True,  "distress_date": "2018-10-15"},
    {"name": "iHeartMedia",              "ticker": "IHRT", "industry": "Media",             "sector": "Media",         "distress_label": True,  "distress_date": "2018-03-14"},
    {"name": "Pier 1 Imports",           "ticker": "PIR",  "industry": "Retail",            "sector": "Retail",        "distress_label": True,  "distress_date": "2020-02-17"},

    # ── Healthy companies (control group) ──────────────────────────────────
    {"name": "Caterpillar",              "ticker": "CAT",  "industry": "Heavy Machinery",   "sector": "Manufacturing", "distress_label": False, "distress_date": None},
    {"name": "Parker Hannifin",          "ticker": "PH",   "industry": "Industrial",        "sector": "Manufacturing", "distress_label": False, "distress_date": None},
    {"name": "Fastenal",                 "ticker": "FAST", "industry": "Industrial Supply",  "sector": "Logistics",     "distress_label": False, "distress_date": None},
    {"name": "Cintas",                   "ticker": "CTAS", "industry": "Business Services",  "sector": "Services",      "distress_label": False, "distress_date": None},
    {"name": "Graco",                    "ticker": "GGG",  "industry": "Fluid Equipment",   "sector": "Manufacturing", "distress_label": False, "distress_date": None},
    {"name": "Watts Water Tech",         "ticker": "WTS",  "industry": "Water Equipment",   "sector": "Manufacturing", "distress_label": False, "distress_date": None},
    {"name": "Roper Technologies",       "ticker": "ROP",  "industry": "Industrial Tech",   "sector": "Tech",          "distress_label": False, "distress_date": None},
    {"name": "IDEX Corporation",         "ticker": "IEX",  "industry": "Pumps/Valves",      "sector": "Manufacturing", "distress_label": False, "distress_date": None},
    {"name": "Xylem",                    "ticker": "XYL",  "industry": "Water Tech",        "sector": "Manufacturing", "distress_label": False, "distress_date": None},
    {"name": "Hubbell",                  "ticker": "HUBB", "industry": "Electrical",        "sector": "Manufacturing", "distress_label": False, "distress_date": None},
    {"name": "Nordson",                  "ticker": "NDSN", "industry": "Precision Equip",   "sector": "Manufacturing", "distress_label": False, "distress_date": None},
    {"name": "Donaldson Company",        "ticker": "DCI",  "industry": "Filtration",        "sector": "Manufacturing", "distress_label": False, "distress_date": None},
    {"name": "Allegion",                 "ticker": "ALLE", "industry": "Security Products", "sector": "Manufacturing", "distress_label": False, "distress_date": None},
    {"name": "Rockwell Automation",      "ticker": "ROK",  "industry": "Automation",        "sector": "Tech",          "distress_label": False, "distress_date": None},
    {"name": "Ametek",                   "ticker": "AME",  "industry": "Electronic Inst",   "sector": "Manufacturing", "distress_label": False, "distress_date": None},
    {"name": "Sensata Technologies",     "ticker": "ST",   "industry": "Sensors",           "sector": "Tech",          "distress_label": False, "distress_date": None},
    {"name": "Belden",                   "ticker": "BDC",  "industry": "Signal Transmission","sector": "Tech",         "distress_label": False, "distress_date": None},
]

# Names to remove from DB (duplicates + failed companies)
REMOVE_NAMES = [
    "Revlon",
    "Rite Aid",
    "Tupperware",
    "Joann Inc",
    "Cineworld",
    "Envision Healthcare",
    "Diamond Sports Group",
    "Monitronics",
    "Wesco Aircraft",
    "Neiman Marcus",
    "Watts Water",           # duplicate of Watts Water Tech
    "Watts Water Systems",   # duplicate
    "Watts Water Technol",   # duplicate
]


# ─────────────────────────────────────────────────────────
# Cleanup: remove bad/duplicate companies from DB
# ─────────────────────────────────────────────────────────
def cleanup_duplicates(session: Session):
    """
    Remove companies that had no XBRL data or were duplicates.
    Cascades to monthly_signals and news_records via company_id.
    """
    removed = 0
    for name in REMOVE_NAMES:
        company = session.query(Company).filter_by(name=name).first()
        if not company:
            continue

        # Delete child rows first (no cascade set in schema)
        session.query(MonthlySignal).filter_by(company_id=company.id).delete()

        # Import NewsRecord here to avoid circular import at top level
        from db_schema import NewsRecord
        session.query(NewsRecord).filter_by(company_id=company.id).delete()

        session.delete(company)
        removed += 1

    session.commit()
    print(f"🗑  Removed {removed} companies (duplicates + failed XBRL)")


# ─────────────────────────────────────────────────────────
# Seed: insert new companies
# ─────────────────────────────────────────────────────────
def seed_companies(session: Session):
    existing = {c.name for c in session.query(Company).all()}
    added = 0
    for c in COMPANIES:
        if c["name"] in existing:
            continue
        company = Company(
            name           = c["name"],
            ticker         = c.get("ticker"),
            industry       = c.get("industry"),
            sector         = c.get("sector"),
            distress_label = c.get("distress_label", False),
            distress_date  = c.get("distress_date"),
        )
        session.add(company)
        added += 1
    session.commit()
    print(f"✅ Seeded {added} new companies ({len(existing)} already existed)")


# ─────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────
def print_summary(session: Session):
    all_companies = session.query(Company).all()
    distressed    = [c for c in all_companies if c.distress_label]
    healthy       = [c for c in all_companies if not c.distress_label]
    print(f"\n📊 Company registry summary:")
    print(f"   Total:      {len(all_companies)}")
    print(f"   Distressed: {len(distressed)}  ({len(distressed)/len(all_companies):.0%})")
    print(f"   Healthy:    {len(healthy)}  ({len(healthy)/len(all_companies):.0%})")


# ─────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────
def main(cleanup_only: bool = False):
    engine = get_engine()
    with Session(engine) as session:
        print("🔧 Cleaning up duplicates and failed companies...")
        cleanup_duplicates(session)

        if not cleanup_only:
            print("🌱 Seeding company list...")
            seed_companies(session)

        print_summary(session)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cleanup", action="store_true",
                        help="Run cleanup only, don't seed new companies")
    args = parser.parse_args()
    main(cleanup_only=args.cleanup)
