"""
Phase 1a — Database Schema
Run this FIRST to create all tables in PostgreSQL.

Usage:
    python phase1_data/db_schema.py
"""

import os
from dotenv import load_dotenv
from sqlalchemy import (
    create_engine, Column, Integer, String, Float,
    Date, Text, Boolean, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship

load_dotenv()

Base = declarative_base()


def get_engine():
    url = (
        f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    )
    return create_engine(url, echo=False)


# ─────────────────────────────────────────────────────────
# Core company registry
# ─────────────────────────────────────────────────────────
class Company(Base):
    __tablename__ = "companies"

    id              = Column(Integer, primary_key=True)
    name            = Column(String(255), nullable=False)
    ticker          = Column(String(20))                  # for SEC pulls
    industry        = Column(String(100))
    sector          = Column(String(100))
    country         = Column(String(100), default="US")
    linkedin_url    = Column(Text)
    glassdoor_url   = Column(Text)
    distress_label  = Column(Boolean, default=False)      # ground truth
    distress_date   = Column(Date, nullable=True)         # when distress event occurred

    signals         = relationship("MonthlySignal", back_populates="company")
    news_records    = relationship("NewsRecord",    back_populates="company")


# ─────────────────────────────────────────────────────────
# Monthly aggregated feature row (one per company per month)
# ─────────────────────────────────────────────────────────
class MonthlySignal(Base):
    __tablename__ = "monthly_signals"
    __table_args__ = (UniqueConstraint("company_id", "year", "month"),)

    id                      = Column(Integer, primary_key=True)
    company_id              = Column(Integer, ForeignKey("companies.id"), nullable=False)
    year                    = Column(Integer, nullable=False)
    month                   = Column(Integer, nullable=False)   # 1–12

    # ── LinkedIn headcount ──────────────────────────────
    headcount               = Column(Integer)
    headcount_mom_pct       = Column(Float)     # month-over-month % change
    headcount_3m_trend      = Column(Float)     # slope over 3 months

    # ── Job postings ────────────────────────────────────
    job_postings_total      = Column(Integer)
    job_postings_mom_pct    = Column(Float)
    pct_ops_finance_roles   = Column(Float)     # warning: rising ops/finance %
    pct_senior_roles        = Column(Float)     # warning: losing senior roles

    # ── Glassdoor ───────────────────────────────────────
    glassdoor_rating        = Column(Float)
    glassdoor_rating_mom    = Column(Float)
    glassdoor_review_count  = Column(Integer)

    # ── News / NLP (populated in Phase 2) ───────────────
    news_sentiment_score    = Column(Float)     # FinBERT: -1 to +1
    news_volume             = Column(Integer)
    distress_keyword_score  = Column(Float)     # TF-IDF weighted distress lexicon hit

    # ── SEC financial ratios ─────────────────────────────
    revenue_qoq_pct         = Column(Float)     # quarter-over-quarter revenue growth
    cash_ratio              = Column(Float)     # cash / current liabilities
    debt_to_equity          = Column(Float)
    operating_margin        = Column(Float)
    interest_coverage       = Column(Float)

    company = relationship("Company", back_populates="signals")


# ─────────────────────────────────────────────────────────
# Raw news articles (for NLP processing in Phase 2)
# ─────────────────────────────────────────────────────────
class NewsRecord(Base):
    __tablename__ = "news_records"

    id          = Column(Integer, primary_key=True)
    company_id  = Column(Integer, ForeignKey("companies.id"), nullable=False)
    published   = Column(Date)
    title       = Column(Text)
    description = Column(Text)
    source      = Column(String(200))
    url         = Column(Text)

    company = relationship("Company", back_populates="news_records")


# ─────────────────────────────────────────────────────────
def create_all_tables():
    engine = get_engine()
    Base.metadata.create_all(engine)
    print("✅ All tables created successfully.")
    return engine


if __name__ == "__main__":
    create_all_tables()
