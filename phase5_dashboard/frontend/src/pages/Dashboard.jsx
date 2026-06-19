import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, ChevronRight } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { api } from '../utils/api'
import { RiskIndicator, ScoreNum, Delta, Skel, Empty, Sparkline, SectionTitle } from '../components/UI'

const TIER_ORDER = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 }

export default function Dashboard() {
  const navigate = useNavigate()

  const { data: companies, loading } = useApi(() => api.companies({ limit: 100 }))
  const { data: sectors }            = useApi(() => api.sectors())

  const [search,       setSearch]       = useState('')
  const [filterSector, setFilterSector] = useState('')
  const [filterTier,   setFilterTier]   = useState('')
  const [sortKey,      setSortKey]      = useState('score')

  const filtered = useMemo(() => {
    if (!companies) return []
    return companies
      .filter(c => {
        const ms = !search || c.name.toLowerCase().includes(search.toLowerCase())
        const mse = !filterSector || c.sector === filterSector
        const mt  = !filterTier   || c.tier   === filterTier
        return ms && mse && mt
      })
      .sort((a, b) => {
        if (sortKey === 'score') return (b.score || 0) - (a.score || 0)
        if (sortKey === 'delta') return Math.abs(b.delta || 0) - Math.abs(a.delta || 0)
        if (sortKey === 'name')  return a.name.localeCompare(b.name)
        if (sortKey === 'tier')  return (TIER_ORDER[a.tier]||3) - (TIER_ORDER[b.tier]||3)
        return 0
      })
  }, [companies, search, filterSector, filterTier, sortKey])

  return (
    <div className="fade-up">

      {/* ── Page header ──────────────────────────────────── */}
      <div className="mb-24">
        <div style={{
          fontFamily: 'var(--f-mono)', fontSize: 9,
          letterSpacing: '0.16em', textTransform: 'uppercase',
          color: 'var(--t-cyan)', marginBottom: 8,
          display: 'flex', alignItems: 'center', gap: 8,
        }}>
          <span style={{ width: 16, height: 1, background: 'var(--cyan)', display: 'inline-block' }} />
          Supply Chain Intelligence
        </div>
        <h1 style={{ fontSize: 28, letterSpacing: '-0.5px', color: 'var(--t1)', marginBottom: 6 }}>
          Supplier Risk Leaderboard
        </h1>
        <p style={{ color: 'var(--t2)', fontSize: 13, maxWidth: 480 }}>
          6-month distress probability modeled from NLP signals, financial ratios, and forecasted trajectories.
        </p>
      </div>

      {/* ── Leaderboard card ─────────────────────────────── */}
      <div className="card">

        {/* Filter toolbar */}
        <div style={{
          padding: '12px 16px',
          borderBottom: '1px solid var(--line)',
          display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap',
        }}>
          {/* Search */}
          <div style={{ position: 'relative', flex: '1 1 180px', maxWidth: 240 }}>
            <Search size={12} style={{
              position: 'absolute', left: 10, top: '50%',
              transform: 'translateY(-50%)', color: 'var(--t3)',
            }} />
            <input
              className="input" value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search suppliers…"
              style={{ width: '100%', paddingLeft: 30, height: 32, fontSize: 12 }}
            />
          </div>

          {/* Sector */}
          <select
            className="input" value={filterSector}
            onChange={e => setFilterSector(e.target.value)}
            style={{ height: 32, fontSize: 12 }}
          >
            <option value="">All Sectors</option>
            {(sectors || []).map(s => <option key={s}>{s}</option>)}
          </select>

          {/* Tier filter */}
          {['CRITICAL','HIGH','MEDIUM','LOW'].map(t => {
            const dotColors = { CRITICAL:'var(--red)', HIGH:'var(--orange)', MEDIUM:'var(--yellow)', LOW:'var(--green)' }
            return (
              <button
                key={t}
                onClick={() => setFilterTier(filterTier === t ? '' : t)}
                className={`btn btn-ghost ${filterTier === t ? 'on' : ''}`}
                style={{ height: 32, fontSize: 11, fontFamily: 'var(--f-mono)', letterSpacing: '0.04em', gap: 5 }}
              >
                <span style={{ width: 5, height: 5, borderRadius: '50%', background: dotColors[t] }} />
                {t}
              </button>
            )
          })}

          {/* Sort */}
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 4 }}>
            {[['score','Score'],['delta','Δ'],['tier','Tier'],['name','Name']].map(([k, lbl]) => (
              <button
                key={k}
                onClick={() => setSortKey(k)}
                className={`btn btn-ghost ${sortKey === k ? 'on' : ''}`}
                style={{ height: 32, fontSize: 11, padding: '0 10px' }}
              >
                {lbl}
              </button>
            ))}
          </div>

          <span style={{
            fontFamily: 'var(--f-mono)', fontSize: 10, color: 'var(--t3)', whiteSpace: 'nowrap',
          }}>
            {filtered.length} suppliers
          </span>
        </div>

        {/* Table */}
        {loading ? (
          <div style={{ padding: 20 }}>
            {[0,1,2,3,4,5,6].map(i => (
              <div key={i} style={{ display: 'flex', gap: 14, alignItems: 'center', marginBottom: 14 }}>
                <Skel w={36} h={12} />
                <Skel w={160} h={12} />
                <Skel w={60} h={12} />
                <Skel w={80} h={24} />
                <Skel w={50} h={12} />
              </div>
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <Empty message="No suppliers match your filters" />
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th style={{ width: 36 }}>#</th>
                  <th>Supplier</th>
                  <th>Sector</th>
                  <th>Risk</th>
                  <th>Score</th>
                  <th>MoM Δ</th>
                  <th>Trajectory</th>
                  <th>Sentiment</th>
                  <th>Cash</th>
                  <th style={{ width: 24 }}></th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((c, idx) => (
                  <tr key={c.id} onClick={() => navigate(`/company/${c.id}`)}>

                    {/* Rank */}
                    <td style={{
                      fontFamily: 'var(--f-mono)', fontSize: 10,
                      color: 'var(--t3)',
                    }}>
                      {String(idx + 1).padStart(2, '0')}
                    </td>

                    {/* Name */}
                    <td>
                      <div style={{ fontWeight: 500, fontSize: 13, color: 'var(--t1)' }} className="truncate">
                        {c.name}
                      </div>
                      <div style={{ fontSize: 10, color: 'var(--t3)', marginTop: 1 }}>
                        {c.industry}
                      </div>
                    </td>

                    {/* Sector */}
                    <td style={{ color: 'var(--t3)', fontSize: 11, fontFamily: 'var(--f-mono)', letterSpacing: '0.04em' }}>
                      {c.sector || '—'}
                    </td>

                    {/* Risk indicator (dot + label, no pill) */}
                    <td><RiskIndicator tier={c.tier} /></td>

                    {/* Score */}
                    <td><ScoreNum score={c.score} tier={c.tier} /></td>

                    {/* Delta */}
                    <td><Delta value={c.delta} /></td>

                    {/* Sparkline — THE SIGNATURE ELEMENT */}
                    <td>
                      <Sparkline
                        data={c._spark || [c.score]}
                        color="auto"
                        width={72}
                        height={26}
                      />
                    </td>

                    {/* Sentiment */}
                    <td style={{
                      fontFamily: 'var(--f-mono)', fontSize: 11,
                      color: c.news_sentiment > 0.1 ? 'var(--green)'
                           : c.news_sentiment < -0.1 ? 'var(--red)'
                           : 'var(--t3)',
                    }}>
                      {c.news_sentiment != null ? c.news_sentiment.toFixed(2) : '—'}
                    </td>

                    {/* Cash ratio */}
                    <td style={{ fontFamily: 'var(--f-mono)', fontSize: 11, color: 'var(--t2)' }}>
                      {c.cash_ratio != null ? c.cash_ratio.toFixed(2) : '—'}
                    </td>

                    {/* Arrow */}
                    <td>
                      <ChevronRight size={12} color="var(--t3)" />
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
