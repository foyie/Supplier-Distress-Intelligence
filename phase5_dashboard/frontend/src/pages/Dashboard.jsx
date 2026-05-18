import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  AlertTriangle, Shield, Activity, Database,
  Search, ChevronRight, TrendingUp,
} from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { api } from '../utils/api'
import {
  TierBadge, ScorePill, Delta, StatCard,
  SectionHeader, Skeleton, EmptyState,
} from '../components/UI'
import { RiskDistributionChart } from '../components/Charts'

const TIER_ORDER = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 }

export default function Dashboard() {
  const navigate = useNavigate()

  const { data: stats,     loading: statsLoading }     = useApi(() => api.stats())
  const { data: companies, loading: companiesLoading } = useApi(() => api.companies({ limit: 100 }))
  const { data: sectors }                              = useApi(() => api.sectors())

  const [search,        setSearch]        = useState('')
  const [filterSector,  setFilterSector]  = useState('')
  const [filterTier,    setFilterTier]    = useState('')
  const [sortKey,       setSortKey]       = useState('score')

  const filtered = useMemo(() => {
    if (!companies) return []
    return companies
      .filter(c => {
        const matchSearch = !search || c.name.toLowerCase().includes(search.toLowerCase())
        const matchSector = !filterSector || c.sector === filterSector
        const matchTier   = !filterTier   || c.tier   === filterTier
        return matchSearch && matchSector && matchTier
      })
      .sort((a, b) => {
        if (sortKey === 'score') return (b.score || 0) - (a.score || 0)
        if (sortKey === 'delta') return Math.abs(b.delta || 0) - Math.abs(a.delta || 0)
        if (sortKey === 'name')  return a.name.localeCompare(b.name)
        if (sortKey === 'tier')  return (TIER_ORDER[a.tier] || 3) - (TIER_ORDER[b.tier] || 3)
        return 0
      })
  }, [companies, search, filterSector, filterTier, sortKey])

  const riskDist = stats?.risk_distribution || {}

  return (
    <div style={{ animation: 'fadeUp 0.4s ease both' }}>

      {/* ── Page header ────────────────────────────────── */}
      <div className="flex items-center justify-between mb-24">
        <div>
          <h1 style={{ fontSize: 26, letterSpacing: '-0.5px', marginBottom: 4 }}>
            Supply Chain Risk Intelligence
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: 13 }}>
            6-month forward distress prediction · Survival + XGBoost ensemble
          </p>
        </div>
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: 11,
          color: 'var(--text-muted)',
          background: 'var(--bg-surface)',
          border: '1px solid var(--border)',
          borderRadius: 8, padding: '8px 14px',
          textAlign: 'right',
        }}>
          <div>Last updated</div>
          <div style={{ color: 'var(--text-secondary)', marginTop: 2 }}>
            {stats?.last_updated || '—'}
          </div>
        </div>
      </div>

      {/* ── Stat cards ─────────────────────────────────── */}
      <div className="grid-4 mb-24">
        {statsLoading ? (
          [0,1,2,3].map(i => <div key={i} className="stat-card"><Skeleton height={60} /></div>)
        ) : (
          <>
            <StatCard
              label="Total Suppliers"
              value={stats?.total_companies}
              sub={`${stats?.data_coverage_months} months coverage`}
              icon={Database}
              accent="var(--blue-accent)"
            />
            <StatCard
              label="Critical Risk"
              value={riskDist.CRITICAL || 0}
              sub="Immediate action required"
              icon={AlertTriangle}
              accent="var(--red-critical)"
            />
            <StatCard
              label="High Risk"
              value={(riskDist.HIGH || 0)}
              sub="Enhanced monitoring"
              icon={TrendingUp}
              accent="#FF6B35"
            />
            <StatCard
              label="Model AUC"
              value={stats?.model_auc ? (stats.model_auc * 100).toFixed(1) + '%' : '—'}
              sub="XGBoost + forecasted signals"
              icon={Activity}
              accent="var(--amber)"
            />
          </>
        )}
      </div>

      {/* ── Two-col: Risk distribution + Tier breakdown ── */}
      <div className="grid-2 mb-24">
        {/* Risk distribution donut */}
        <div className="card">
          <div className="card-header">
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: 11,
              letterSpacing: '0.1em', textTransform: 'uppercase',
              color: 'var(--text-muted)',
            }}>Risk Distribution</span>
            <Shield size={14} color="var(--text-muted)" />
          </div>
          <div className="card-body" style={{ height: 220 }}>
            {statsLoading
              ? <Skeleton height={180} />
              : <RiskDistributionChart data={riskDist} />
            }
          </div>
        </div>

        {/* Tier breakdown bars */}
        <div className="card">
          <div className="card-header">
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: 11,
              letterSpacing: '0.1em', textTransform: 'uppercase',
              color: 'var(--text-muted)',
            }}>Portfolio Breakdown</span>
          </div>
          <div className="card-body">
            {[
              { tier: 'CRITICAL', color: '#FF3B3B' },
              { tier: 'HIGH',     color: '#FF6B35' },
              { tier: 'MEDIUM',   color: '#F5C518' },
              { tier: 'LOW',      color: '#22C55E' },
            ].map(({ tier, color }) => {
              const count = riskDist[tier] || 0
              const total = stats?.total_companies || 1
              const pct   = ((count / total) * 100).toFixed(0)
              return (
                <div key={tier} style={{ marginBottom: 18 }}>
                  <div className="flex items-center justify-between mb-4">
                    <TierBadge tier={tier} />
                    <span style={{
                      fontFamily: 'var(--font-mono)', fontSize: 12,
                      color: 'var(--text-secondary)',
                    }}>
                      {statsLoading ? '—' : `${count} suppliers · ${pct}%`}
                    </span>
                  </div>
                  <div style={{
                    height: 6, background: 'var(--bg-elevated)',
                    borderRadius: 3, overflow: 'hidden',
                  }}>
                    <div style={{
                      height: '100%', width: statsLoading ? '0%' : `${pct}%`,
                      background: color, borderRadius: 3,
                      transition: 'width 1s cubic-bezier(0.4,0,0.2,1)',
                    }} />
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* ── Supplier leaderboard ────────────────────────── */}
      <div className="card">
        <div className="card-header">
          <SectionHeader label="Supplier Risk Leaderboard">
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: 11,
              color: 'var(--text-muted)',
            }}>
              {filtered.length} suppliers
            </span>
          </SectionHeader>
        </div>

        {/* Filter bar */}
        <div style={{
          padding: '12px 20px',
          borderBottom: '1px solid var(--border)',
          display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap',
        }}>
          {/* Search */}
          <div style={{ position: 'relative', flex: '1 1 200px', maxWidth: 280 }}>
            <Search size={13} style={{
              position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)',
              color: 'var(--text-muted)',
            }} />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search suppliers..."
              style={{
                width: '100%', paddingLeft: 32, paddingRight: 12,
                height: 34, background: 'var(--bg-elevated)',
                border: '1px solid var(--border)', borderRadius: 7,
                color: 'var(--text-primary)', fontSize: 13,
                fontFamily: 'var(--font-body)',
                outline: 'none',
              }}
            />
          </div>

          {/* Sector filter */}
          <select
            value={filterSector}
            onChange={e => setFilterSector(e.target.value)}
            style={{
              height: 34, padding: '0 10px',
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border)', borderRadius: 7,
              color: filterSector ? 'var(--text-primary)' : 'var(--text-muted)',
              fontSize: 13, fontFamily: 'var(--font-body)', cursor: 'pointer',
            }}
          >
            <option value="">All Sectors</option>
            {(sectors || []).map(s => <option key={s} value={s}>{s}</option>)}
          </select>

          {/* Tier filter pills */}
          {['CRITICAL','HIGH','MEDIUM','LOW'].map(t => (
            <button
              key={t}
              onClick={() => setFilterTier(filterTier === t ? '' : t)}
              className={`btn btn-ghost ${filterTier === t ? 'active' : ''}`}
              style={{ padding: '4px 10px', fontSize: 11, fontFamily: 'var(--font-mono)' }}
            >
              {t}
            </button>
          ))}

          {/* Sort */}
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 6 }}>
            {[['score','Score'],['delta','Δ Change'],['tier','Tier'],['name','Name']].map(([k, label]) => (
              <button
                key={k}
                onClick={() => setSortKey(k)}
                className={`btn btn-ghost ${sortKey === k ? 'active' : ''}`}
                style={{ padding: '4px 10px', fontSize: 11 }}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {/* Table */}
        {companiesLoading ? (
          <div style={{ padding: 20 }}>
            {[0,1,2,3,4,5].map(i => (
              <div key={i} style={{ display: 'flex', gap: 16, marginBottom: 12 }}>
                <Skeleton width={160} height={14} />
                <Skeleton width={80}  height={14} />
                <Skeleton width={60}  height={14} />
                <Skeleton width={100} height={14} />
              </div>
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState message="No suppliers match your filters" />
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Supplier</th>
                  <th>Sector</th>
                  <th>Risk Score</th>
                  <th>Tier</th>
                  <th>MoM Δ</th>
                  <th>Sentiment</th>
                  <th>Cash Ratio</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((c, idx) => (
                  <tr
                    key={c.id}
                    onClick={() => navigate(`/company/${c.id}`)}
                    style={{ animationDelay: `${idx * 20}ms` }}
                  >
                    <td style={{
                      fontFamily: 'var(--font-mono)', fontSize: 11,
                      color: 'var(--text-muted)', width: 36,
                    }}>
                      {idx + 1}
                    </td>
                    <td>
                      <div style={{ fontWeight: 500, fontSize: 13 }}>{c.name}</div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{c.industry}</div>
                    </td>
                    <td style={{ color: 'var(--text-secondary)', fontSize: 12 }}>
                      {c.sector || '—'}
                    </td>
                    <td>
                      {/* Mini score bar */}
                      <div className="flex items-center gap-8">
                        <div style={{
                          width: 60, height: 4, background: 'var(--bg-elevated)',
                          borderRadius: 2, overflow: 'hidden',
                        }}>
                          <div style={{
                            height: '100%',
                            width: `${c.score}%`,
                            background: c.color,
                            borderRadius: 2,
                          }} />
                        </div>
                        <ScorePill score={c.score} tier={c.tier} />
                      </div>
                    </td>
                    <td><TierBadge tier={c.tier} /></td>
                    <td><Delta value={c.delta} /></td>
                    <td>
                      <span style={{
                        fontFamily: 'var(--font-mono)', fontSize: 12,
                        color: c.news_sentiment > 0.1 ? 'var(--green-low)'
                          : c.news_sentiment < -0.1 ? 'var(--red-critical)'
                          : 'var(--text-secondary)',
                      }}>
                        {c.news_sentiment != null ? c.news_sentiment.toFixed(2) : '—'}
                      </span>
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}>
                      {c.cash_ratio != null ? c.cash_ratio.toFixed(2) : '—'}
                    </td>
                    <td>
                      <ChevronRight size={14} color="var(--text-muted)" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
