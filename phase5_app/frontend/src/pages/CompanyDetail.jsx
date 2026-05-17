import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  LineChart, Line, BarChart, Bar,
  XAxis, YAxis, Tooltip, ResponsiveContainer,
  ReferenceLine, Cell
} from 'recharts'
import { ArrowLeft, FileText, TrendingUp, Brain, BarChart2 } from 'lucide-react'
import { api } from '../lib/api'
import { useFetch } from '../hooks/useFetch'
import { TierBadge, ScoreGauge, Skeleton, ErrorState, fmt } from '../components/UI'

// ── Tab bar ────────────────────────────────────────────────
function Tabs({ tabs, active, onChange }) {
  return (
    <div className="flex gap-1 border-b border-mist mb-6">
      {tabs.map(t => (
        <button
          key={t.id}
          onClick={() => onChange(t.id)}
          className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium transition-colors
            ${active === t.id
              ? 'text-ink border-b-2 border-ink -mb-px'
              : 'text-ash hover:text-ink'
            }`}
        >
          <t.icon size={14} />
          {t.label}
        </button>
      ))}
    </div>
  )
}

// ── Score history chart ────────────────────────────────────
function ScoreHistory({ history }) {
  const data = (history || []).map(h => ({
    date:  h.date,
    score: h.score_pct,
  }))

  return (
    <div className="card">
      <h3 className="text-sm font-medium mb-4">Risk Score History</h3>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
          <XAxis
            dataKey="date" tick={{ fontSize: 10, fill: '#9B9690', fontFamily: 'DM Mono' }}
            tickLine={false} axisLine={false}
            interval={Math.floor(data.length / 6)}
          />
          <YAxis
            domain={[0, 100]} tick={{ fontSize: 10, fill: '#9B9690', fontFamily: 'DM Mono' }}
            tickLine={false} axisLine={false}
          />
          <Tooltip
            contentStyle={{
              background: '#fff', border: '1px solid #E8E5DF',
              borderRadius: 8, fontSize: 12, fontFamily: 'DM Mono'
            }}
            formatter={v => [`${v}/100`, 'Risk Score']}
          />
          <ReferenceLine y={65} stroke="#C0392B" strokeDasharray="3 3" strokeOpacity={0.4} />
          <ReferenceLine y={35} stroke="#D4860A" strokeDasharray="3 3" strokeOpacity={0.4} />
          <Line
            type="monotone" dataKey="score" stroke="#1A4ED8"
            strokeWidth={2} dot={false} activeDot={{ r: 4 }}
          />
        </LineChart>
      </ResponsiveContainer>
      <div className="flex gap-4 mt-3 text-xs text-ash font-mono">
        <span className="flex items-center gap-1">
          <span className="w-6 border-t-2 border-dashed border-high opacity-50" />
          High threshold (65)
        </span>
        <span className="flex items-center gap-1">
          <span className="w-6 border-t-2 border-dashed border-mid opacity-50" />
          Medium threshold (35)
        </span>
      </div>
    </div>
  )
}

// ── SHAP waterfall ─────────────────────────────────────────
function ShapChart({ shap }) {
  const data = (shap || []).slice(0, 12).map(s => ({
    feature: s.feature_label,
    value:   parseFloat((s.shap_value * 100).toFixed(2)),
  }))

  return (
    <div className="card">
      <h3 className="text-sm font-medium mb-1">SHAP Feature Attribution</h3>
      <p className="text-xs text-ash mb-4">
        Red bars increase distress risk · Blue bars reduce it
      </p>
      <ResponsiveContainer width="100%" height={320}>
        <BarChart
          data={data} layout="vertical"
          margin={{ top: 0, right: 16, bottom: 0, left: 150 }}
        >
          <XAxis
            type="number" tick={{ fontSize: 10, fill: '#9B9690', fontFamily: 'DM Mono' }}
            tickLine={false} axisLine={false}
          />
          <YAxis
            type="category" dataKey="feature" width={145}
            tick={{ fontSize: 11, fill: '#0D0F12', fontFamily: 'DM Sans' }}
            tickLine={false} axisLine={false}
          />
          <Tooltip
            contentStyle={{
              background: '#fff', border: '1px solid #E8E5DF',
              borderRadius: 8, fontSize: 12, fontFamily: 'DM Mono'
            }}
            formatter={v => [`${v > 0 ? '+' : ''}${v}`, 'SHAP impact']}
          />
          <ReferenceLine x={0} stroke="#E8E5DF" />
          <Bar dataKey="value" radius={[0, 3, 3, 0]}>
            {data.map((d, i) => (
              <Cell key={i} fill={d.value > 0 ? '#C0392B' : '#1A4ED8'} fillOpacity={0.8} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

// ── Forecast charts ────────────────────────────────────────
function ForecastCharts({ forecasts }) {
  const items = forecasts || []
  if (items.length === 0) {
    return (
      <div className="card text-center py-10 text-ash text-sm">
        No forecasts available. Run Phase 3 (forecaster.py) first.
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
      {items.slice(0, 6).map(f => {
        const data = f.values.map(v => ({
          date:  v.date,
          value: v.value,
          lower: v.value_lower,
          upper: v.value_upper,
        }))
        return (
          <div key={f.feature} className="card">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-medium">{f.feature_label}</h3>
              <span className="text-xs font-mono text-ash bg-mist px-2 py-0.5 rounded">
                {f.model}
              </span>
            </div>
            <ResponsiveContainer width="100%" height={130}>
              <LineChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
                <XAxis
                  dataKey="date" tick={{ fontSize: 9, fill: '#9B9690', fontFamily: 'DM Mono' }}
                  tickLine={false} axisLine={false}
                />
                <YAxis
                  tick={{ fontSize: 9, fill: '#9B9690', fontFamily: 'DM Mono' }}
                  tickLine={false} axisLine={false}
                />
                <Tooltip
                  contentStyle={{
                    background: '#fff', border: '1px solid #E8E5DF',
                    borderRadius: 8, fontSize: 11, fontFamily: 'DM Mono'
                  }}
                />
                <Line
                  type="monotone" dataKey="value" stroke="#1A4ED8"
                  strokeWidth={2} dot={{ r: 3, fill: '#1A4ED8' }}
                  strokeDasharray="5 3"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )
      })}
    </div>
  )
}

// ── Analyst brief ──────────────────────────────────────────
function AnalystBrief({ brief }) {
  if (!brief) return null

  const tierColors = {
    HIGH:   { bg: '#FEF2F2', border: '#FECACA', text: '#C0392B' },
    MEDIUM: { bg: '#FFFBEB', border: '#FDE68A', text: '#D4860A' },
    LOW:    { bg: '#F0FDF4', border: '#BBF7D0', text: '#27AE60' },
  }
  const tc = tierColors[brief.tier] || tierColors.LOW

  const financialRows = [
    { label: 'Cash Ratio',       value: fmt(brief.financials?.cash_ratio) },
    { label: 'Debt / Equity',    value: fmt(brief.financials?.debt_to_equity) },
    { label: 'Operating Margin', value: fmt(brief.financials?.operating_margin, 'pct') },
    { label: 'Revenue QoQ %',    value: fmt(brief.financials?.revenue_qoq_pct, 'pct') },
  ]

  const sentimentRows = [
    { label: 'News Sentiment',     value: fmt(brief.sentiment?.news_sentiment_score) },
    { label: 'Distress Keywords',  value: fmt(brief.sentiment?.distress_keyword_score) },
    { label: 'Glassdoor Rating',   value: fmt(brief.sentiment?.glassdoor_rating, 'rating') },
  ]

  return (
    <div className="space-y-4">
      {/* Header */}
      <div
        className="card border-2"
        style={{ borderColor: tc.border, background: tc.bg }}
      >
        <div className="flex items-start justify-between">
          <div>
            <p className="text-xs font-mono text-ash mb-1">ANALYST BRIEF · {brief.generated}</p>
            <h2 className="font-display text-2xl">{brief.company}</h2>
            <p className="text-sm text-ash mt-0.5">{brief.industry} · {brief.sector}</p>
          </div>
          <div className="text-right">
            <div className="font-mono text-4xl font-medium" style={{ color: tc.text }}>
              {brief.score}
            </div>
            <div className="text-xs text-ash font-mono">/100 risk score</div>
          </div>
        </div>
        <p className="text-sm mt-4 leading-relaxed">{brief.summary}</p>
      </div>

      {/* Key drivers */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="card border-red-200">
          <h4 className="text-xs font-mono text-ash uppercase tracking-wider mb-2">
            ⚠ Key Risk Drivers
          </h4>
          <p className="text-sm">{brief.key_risk_drivers}</p>
        </div>
        <div className="card border-emerald-200">
          <h4 className="text-xs font-mono text-ash uppercase tracking-wider mb-2">
            ✓ Protective Factors
          </h4>
          <p className="text-sm">{brief.protective_factors}</p>
        </div>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="card">
          <h4 className="text-xs font-mono text-ash uppercase tracking-wider mb-3">
            Financial Indicators
          </h4>
          <div className="space-y-2">
            {financialRows.map(r => (
              <div key={r.label} className="flex justify-between items-center
                                            border-b border-mist pb-2 last:border-0 last:pb-0">
                <span className="text-sm text-ash">{r.label}</span>
                <span className="font-mono text-sm font-medium">{r.value}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="card">
          <h4 className="text-xs font-mono text-ash uppercase tracking-wider mb-3">
            Sentiment Signals
          </h4>
          <div className="space-y-2">
            {sentimentRows.map(r => (
              <div key={r.label} className="flex justify-between items-center
                                            border-b border-mist pb-2 last:border-0 last:pb-0">
                <span className="text-sm text-ash">{r.label}</span>
                <span className="font-mono text-sm font-medium">{r.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recommendation */}
      <div className="card border-accent/30 bg-blue-50">
        <h4 className="text-xs font-mono text-ash uppercase tracking-wider mb-2">
          Recommendation
        </h4>
        <p className="text-sm font-medium text-accent">{brief.recommendation}</p>
      </div>
    </div>
  )
}

// ── Page ───────────────────────────────────────────────────
const TABS = [
  { id: 'overview',  label: 'Overview',       icon: BarChart2  },
  { id: 'shap',      label: 'SHAP Analysis',  icon: Brain      },
  { id: 'forecasts', label: 'Forecasts',      icon: TrendingUp },
  { id: 'brief',     label: 'Analyst Brief',  icon: FileText   },
]

export default function CompanyDetail() {
  const { id }          = useParams()
  const [tab, setTab]   = useState('overview')

  const { data: company, loading: cLoading, error: cError } =
    useFetch(() => api.company(id), [id])
  const { data: shap,    loading: sLoading } =
    useFetch(() => api.shap(id),    [id])
  const { data: forecast, loading: fLoading } =
    useFetch(() => api.forecast(id), [id])
  const { data: brief,   loading: bLoading } =
    useFetch(() => api.brief(id),   [id])

  if (cError) return <ErrorState message={cError} />

  const tierColor =
    company?.tier === 'HIGH'   ? '#C0392B' :
    company?.tier === 'MEDIUM' ? '#D4860A' : '#27AE60'

  return (
    <div className="space-y-6">
      {/* Back */}
      <Link to="/" className="inline-flex items-center gap-1.5 text-sm text-ash
                               hover:text-ink transition-colors">
        <ArrowLeft size={14} /> Back to Dashboard
      </Link>

      {/* Company header */}
      {cLoading ? (
        <div className="card flex gap-5">
          <Skeleton className="w-24 h-24 rounded-full" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-7 w-64" />
            <Skeleton className="h-4 w-40" />
          </div>
        </div>
      ) : company && (
        <div className="card flex flex-wrap items-center gap-6">
          <ScoreGauge score={company.score || 0} />
          <div className="flex-1">
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="font-display text-3xl">{company.name}</h1>
              {company.ticker && (
                <span className="font-mono text-sm text-ash border border-mist
                                 px-2 py-0.5 rounded">
                  {company.ticker}
                </span>
              )}
              <TierBadge tier={company.tier} />
            </div>
            <p className="text-ash text-sm mt-1">
              {company.industry} · {company.sector}
            </p>
            <div className="flex gap-6 mt-3 text-sm">
              <div>
                <span className="text-ash">Risk Score </span>
                <span className="font-mono font-medium" style={{ color: tierColor }}>
                  {company.score_pct}/100
                </span>
              </div>
              {company.delta !== undefined && (
                <div>
                  <span className="text-ash">MoM </span>
                  <span className={`font-mono font-medium ${
                    company.delta > 0 ? 'text-high' : 'text-low'
                  }`}>
                    {company.delta > 0 ? '+' : ''}{Math.round(company.delta * 100)}
                  </span>
                </div>
              )}
              {company.distress_label && company.distress_date && (
                <div>
                  <span className="text-ash">Distress Event </span>
                  <span className="font-mono text-high">{company.distress_date}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <Tabs tabs={TABS} active={tab} onChange={setTab} />

      {/* Tab content */}
      {tab === 'overview' && (
        <div className="space-y-4 stagger">
          {cLoading
            ? <Skeleton className="h-64 w-full rounded-xl" />
            : <ScoreHistory history={company?.score_history} />
          }
        </div>
      )}

      {tab === 'shap' && (
        <div className="stagger">
          {sLoading
            ? <Skeleton className="h-80 w-full rounded-xl" />
            : <ShapChart shap={shap?.shap} />
          }
        </div>
      )}

      {tab === 'forecasts' && (
        <div className="stagger">
          {fLoading
            ? <div className="grid grid-cols-2 gap-4">
                {Array.from({ length: 4 }).map((_, i) => (
                  <Skeleton key={i} className="h-48 rounded-xl" />
                ))}
              </div>
            : <ForecastCharts forecasts={forecast?.forecasts} />
          }
        </div>
      )}

      {tab === 'brief' && (
        <div className="stagger">
          {bLoading
            ? <Skeleton className="h-96 w-full rounded-xl" />
            : <AnalystBrief brief={brief} />
          }
        </div>
      )}
    </div>
  )
}
