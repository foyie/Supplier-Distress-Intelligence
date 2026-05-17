import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, SlidersHorizontal } from 'lucide-react'
import { api } from '../lib/api'
import { useFetch } from '../hooks/useFetch'
import { TierBadge, DeltaChip, Skeleton, ErrorState } from '../components/UI'

// ── Stat card ──────────────────────────────────────────────
function StatCard({ label, value, sub, color }) {
  return (
    <div className="stat-card">
      <span className="text-xs text-ash font-mono uppercase tracking-wider">{label}</span>
      <span className="font-display text-3xl" style={color ? { color } : {}}>
        {value ?? '—'}
      </span>
      {sub && <span className="text-xs text-ash">{sub}</span>}
    </div>
  )
}

// ── Company row ────────────────────────────────────────────
function CompanyRow({ company, index, onClick }) {
  const bar = Math.round(company.score_pct)
  const barColor =
    company.tier === 'HIGH'   ? '#C0392B' :
    company.tier === 'MEDIUM' ? '#D4860A' : '#27AE60'

  return (
    <tr
      onClick={onClick}
      className="border-b border-mist hover:bg-paper cursor-pointer transition-colors group"
      style={{ animationDelay: `${index * 0.03}s` }}
    >
      <td className="py-3.5 pl-4 pr-2 font-mono text-xs text-ash w-8">{index + 1}</td>
      <td className="py-3.5 pr-4">
        <div className="font-medium text-sm group-hover:text-accent transition-colors">
          {company.name}
        </div>
        <div className="flex items-center gap-2 mt-0.5">
          {company.ticker && (
            <span className="font-mono text-xs text-ash">{company.ticker}</span>
          )}
          <span className="text-xs text-ash">{company.industry}</span>
        </div>
      </td>
      <td className="py-3.5 pr-6 w-48">
        <div className="flex items-center gap-2">
          <div className="flex-1 h-1.5 bg-mist rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-700"
              style={{ width: `${bar}%`, background: barColor }}
            />
          </div>
          <span className="font-mono text-sm font-medium w-8 text-right"
            style={{ color: barColor }}
          >
            {bar}
          </span>
        </div>
      </td>
      <td className="py-3.5 pr-4">
        <TierBadge tier={company.tier} />
      </td>
      <td className="py-3.5 pr-4 text-right">
        <DeltaChip delta={company.delta} />
      </td>
      <td className="py-3.5 pr-4 text-xs text-ash">{company.sector}</td>
    </tr>
  )
}

// ── Main dashboard ─────────────────────────────────────────
export default function Dashboard() {
  const navigate = useNavigate()
  const [search,  setSearch]  = useState('')
  const [sector,  setSector]  = useState('')
  const [tier,    setTier]    = useState('')
  const [sortBy,  setSortBy]  = useState('score')

  const { data: stats,   loading: statsLoading } = useFetch(() => api.stats(),   [])
  const { data: sectors, loading: secLoading   } = useFetch(() => api.sectors(), [])
  const { data: comp,    loading: compLoading, error } = useFetch(
    () => api.companies({ sector, tier, sort_by: sortBy }),
    [sector, tier, sortBy]
  )

  const companies = (comp?.companies || []).filter(c =>
    !search || c.name.toLowerCase().includes(search.toLowerCase()) ||
    (c.ticker || '').toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="space-y-7 stagger">
      {/* Header */}
      <div className="flex items-end justify-between">
        <div>
          <h1 className="font-display text-4xl leading-tight">
            Supplier Risk Intelligence
          </h1>
          <p className="text-ash text-sm mt-1">
            Early-warning distress scores · Updated {stats?.last_updated || '—'}
          </p>
        </div>
        <div className="font-mono text-xs text-ash text-right">
          XGBoost + Cox PH Survival<br />
          FinBERT · Prophet · LSTM
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {statsLoading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="stat-card"><Skeleton className="h-8 w-16" /></div>
          ))
        ) : (
          <>
            <StatCard label="Companies Monitored" value={stats?.total_companies} />
            <StatCard label="High Risk"   value={stats?.high_risk}   color="#C0392B" sub="Immediate review" />
            <StatCard label="Medium Risk" value={stats?.medium_risk} color="#D4860A" sub="Watch list" />
            <StatCard label="Mean Score"  value={stats?.mean_score ? `${stats.mean_score}` : null} sub="out of 100" />
          </>
        )}
      </div>

      {/* Filters */}
      <div className="card flex flex-wrap items-center gap-3">
        {/* Search */}
        <div className="relative flex-1 min-w-[180px]">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-ash" />
          <input
            type="text"
            placeholder="Search company or ticker..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 text-sm border border-mist rounded-lg bg-paper
                       focus:outline-none focus:border-accent font-sans"
          />
        </div>

        {/* Sector filter */}
        <select
          value={sector}
          onChange={e => setSector(e.target.value)}
          className="text-sm border border-mist rounded-lg px-3 py-1.5 bg-paper
                     focus:outline-none focus:border-accent font-sans text-ink"
        >
          <option value="">All Sectors</option>
          {(sectors?.sectors || []).map(s => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>

        {/* Tier filter */}
        <select
          value={tier}
          onChange={e => setTier(e.target.value)}
          className="text-sm border border-mist rounded-lg px-3 py-1.5 bg-paper
                     focus:outline-none focus:border-accent font-sans text-ink"
        >
          <option value="">All Tiers</option>
          <option value="HIGH">High Risk</option>
          <option value="MEDIUM">Medium Risk</option>
          <option value="LOW">Low Risk</option>
        </select>

        {/* Sort */}
        <div className="flex items-center gap-2 ml-auto">
          <SlidersHorizontal size={14} className="text-ash" />
          <select
            value={sortBy}
            onChange={e => setSortBy(e.target.value)}
            className="text-sm border border-mist rounded-lg px-3 py-1.5 bg-paper
                       focus:outline-none focus:border-accent font-sans text-ink"
          >
            <option value="score">Sort: Risk Score</option>
            <option value="score_change">Sort: Biggest Move</option>
            <option value="name">Sort: Name</option>
          </select>
        </div>
      </div>

      {/* Table */}
      {error ? (
        <ErrorState message={error} />
      ) : (
        <div className="card p-0 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-mist bg-paper">
                <th className="py-3 pl-4 pr-2 text-left text-xs font-mono text-ash">#</th>
                <th className="py-3 pr-4 text-left text-xs font-mono text-ash">Company</th>
                <th className="py-3 pr-6 text-left text-xs font-mono text-ash">Risk Score</th>
                <th className="py-3 pr-4 text-left text-xs font-mono text-ash">Tier</th>
                <th className="py-3 pr-4 text-right text-xs font-mono text-ash">Δ MoM</th>
                <th className="py-3 pr-4 text-left text-xs font-mono text-ash">Sector</th>
              </tr>
            </thead>
            <tbody>
              {compLoading ? (
                Array.from({ length: 8 }).map((_, i) => (
                  <tr key={i} className="border-b border-mist">
                    {Array.from({ length: 6 }).map((_, j) => (
                      <td key={j} className="py-4 px-4">
                        <Skeleton className="h-4 w-full" />
                      </td>
                    ))}
                  </tr>
                ))
              ) : companies.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-16 text-center text-ash text-sm">
                    No companies match your filters.
                  </td>
                </tr>
              ) : (
                companies.map((c, i) => (
                  <CompanyRow
                    key={c.id}
                    company={c}
                    index={i}
                    onClick={() => navigate(`/company/${c.id}`)}
                  />
                ))
              )}
            </tbody>
          </table>
          {!compLoading && companies.length > 0 && (
            <div className="px-4 py-2.5 border-t border-mist bg-paper">
              <span className="text-xs text-ash font-mono">
                {companies.length} companies · click any row for full analysis
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
