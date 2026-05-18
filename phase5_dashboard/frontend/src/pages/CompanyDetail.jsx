import { useParams } from 'react-router-dom'
import { useState } from 'react'
import {
  FileText, Zap, BarChart2, TrendingUp,
  Activity, Users, Newspaper, DollarSign,
  AlertTriangle, Download,
} from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { api } from '../utils/api'
import {
  TierBadge, SectionHeader, Skeleton, EmptyState, ChartTooltip,
} from '../components/UI'
import {
  SignalTimelineChart,
  ForecastChart,
  ShapWaterfall,
} from '../components/Charts'

/* ── Risk gauge ──────────────────────────────────────── */
function RiskGauge({ score, tier }) {
  const colors = {
    CRITICAL: '#FF3B3B', HIGH: '#FF6B35',
    MEDIUM: '#F5C518', LOW: '#22C55E',
  }
  const color   = colors[tier] || '#888'
  const radius  = 70
  const stroke  = 8
  const circ    = 2 * Math.PI * radius
  const half    = circ / 2
  const dashoff = half - (score / 100) * half

  return (
    <div style={{ textAlign: 'center', padding: '8px 0' }}>
      <svg width="180" height="100" viewBox="0 0 180 100">
        {/* Track */}
        <path
          d={`M ${90 - radius} 90 A ${radius} ${radius} 0 0 1 ${90 + radius} 90`}
          fill="none" stroke="var(--bg-elevated)" strokeWidth={stroke}
          strokeLinecap="round"
        />
        {/* Fill */}
        <path
          d={`M ${90 - radius} 90 A ${radius} ${radius} 0 0 1 ${90 + radius} 90`}
          fill="none" stroke={color} strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${half} ${half}`}
          strokeDashoffset={dashoff}
          style={{ transition: 'stroke-dashoffset 1s cubic-bezier(0.4,0,0.2,1)', transformOrigin: '90px 90px' }}
        />
        {/* Score text */}
        <text x="90" y="78" textAnchor="middle"
          style={{ fontFamily: 'var(--font-display)', fontSize: 28, fontWeight: 800, fill: color }}
        >
          {score?.toFixed(0)}
        </text>
        <text x="90" y="95" textAnchor="middle"
          style={{ fontFamily: 'var(--font-mono)', fontSize: 10, fill: 'var(--text-muted)' }}
        >
          RISK SCORE
        </text>
      </svg>
    </div>
  )
}

/* ── Signal metric card ──────────────────────────────── */
function SignalMetric({ label, value, unit = '', good = null, icon: Icon }) {
  let color = 'var(--text-primary)'
  if (good !== null && value != null) {
    color = good ? 'var(--green-low)' : 'var(--red-critical)'
  }
  return (
    <div style={{
      background: 'var(--bg-elevated)',
      borderRadius: 10, padding: '14px 16px',
      border: '1px solid var(--border)',
    }}>
      <div className="flex items-center gap-8 mb-8">
        {Icon && <Icon size={12} color="var(--text-muted)" />}
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: 10,
          textTransform: 'uppercase', letterSpacing: '0.1em',
          color: 'var(--text-muted)',
        }}>{label}</span>
      </div>
      <div style={{
        fontFamily: 'var(--font-display)', fontSize: 22,
        fontWeight: 700, color, letterSpacing: '-0.5px',
      }}>
        {value != null ? `${typeof value === 'number' ? value.toFixed(2) : value}${unit}` : '—'}
      </div>
    </div>
  )
}

/* ── Analyst brief panel ─────────────────────────────── */
function AnalystBrief({ brief }) {
  if (!brief) return null
  const tierColors = {
    CRITICAL: '#FF3B3B', HIGH: '#FF6B35',
    MEDIUM: '#F5C518', LOW: '#22C55E',
  }

  return (
    <div style={{
      background: 'var(--bg-surface)',
      border: `1px solid ${tierColors[brief.risk_tier] || 'var(--border)'}44`,
      borderRadius: 12, padding: 24,
    }}>
      {/* Header */}
      <div className="flex items-center justify-between mb-16">
        <div>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 10,
            letterSpacing: '0.12em', textTransform: 'uppercase',
            color: 'var(--text-muted)', marginBottom: 4,
          }}>
            ANALYST BRIEF · {brief.generated_at}
          </div>
          <h3 style={{ fontFamily: 'var(--font-display)', fontSize: 18 }}>
            {brief.company_name}
          </h3>
        </div>
        <div className="flex items-center gap-8">
          <TierBadge tier={brief.risk_tier} />
          <button className="btn btn-ghost" style={{ padding: '6px 12px', fontSize: 12 }}>
            <Download size={12} />
            Export
          </button>
        </div>
      </div>

      {/* Signals */}
      {brief.signal_summary?.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 10,
            textTransform: 'uppercase', letterSpacing: '0.1em',
            color: 'var(--text-muted)', marginBottom: 10,
          }}>Key Signals</div>
          {brief.signal_summary.map((s, i) => (
            <div key={i} className="flex items-center gap-8" style={{ marginBottom: 7 }}>
              <AlertTriangle size={11} color={tierColors[brief.risk_tier]} />
              <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{s}</span>
            </div>
          ))}
        </div>
      )}

      {/* Divider */}
      <div className="divider" style={{ margin: '16px 0' }} />

      {/* Recommendation */}
      <div>
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: 10,
          textTransform: 'uppercase', letterSpacing: '0.1em',
          color: 'var(--text-muted)', marginBottom: 8,
        }}>Recommendation</div>
        <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7 }}>
          {brief.recommendation}
        </p>
      </div>

      {/* Disclaimer */}
      <div style={{
        marginTop: 16, padding: '8px 12px',
        background: 'var(--bg-elevated)', borderRadius: 6,
        fontSize: 11, color: 'var(--text-muted)',
        fontFamily: 'var(--font-mono)',
      }}>
        {brief.disclaimer}
      </div>
    </div>
  )
}

/* ── Tab switcher ────────────────────────────────────── */
const TABS = [
  { key: 'signals',  label: 'Signal Timeline', icon: Activity },
  { key: 'forecast', label: 'Forecast',         icon: TrendingUp },
  { key: 'shap',     label: 'SHAP Analysis',    icon: BarChart2 },
  { key: 'brief',    label: 'Analyst Brief',    icon: FileText },
]

/* ══ Main page ═══════════════════════════════════════════ */
export default function CompanyDetail() {
  const { id } = useParams()
  const [activeTab, setActiveTab] = useState('signals')

  const { data: company, loading: compLoading } = useApi(() => api.company(id),    [id])
  const { data: signals, loading: sigLoading }  = useApi(() => api.signals(id),    [id])
  const { data: forecast,loading: fcLoading }   = useApi(() => api.forecast(id),   [id])
  const { data: shapData, loading: shapLoading} = useApi(() => api.shap(id),       [id])
  const { data: brief,   loading: briefLoading} = useApi(() => api.brief(id),      [id])

  if (compLoading) {
    return (
      <div style={{ padding: 32 }}>
        <Skeleton height={32} width={300} style={{ marginBottom: 16 }} />
        <div className="grid-2"><Skeleton height={200} /><Skeleton height={200} /></div>
      </div>
    )
  }
  if (!company) return <EmptyState message="Company not found" />

  const risk = company.risk || {}
  const sig  = company.latest_signals || {}

  return (
    <div style={{ animation: 'fadeUp 0.35s ease both' }}>

      {/* ── Company header ──────────────────────────────── */}
      <div style={{
        marginBottom: 28,
        padding: '24px',
        background: 'var(--bg-surface)',
        border: '1px solid var(--border)',
        borderRadius: 12,
        display: 'grid',
        gridTemplateColumns: '1fr auto',
        gap: 24,
        alignItems: 'center',
      }}>
        <div>
          <div className="flex items-center gap-12 mb-8">
            <TierBadge tier={risk.tier} />
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: 11,
              color: 'var(--text-muted)',
            }}>
              {company.sector} · {company.industry}
            </span>
          </div>
          <h1 style={{ fontSize: 30, letterSpacing: '-0.8px', marginBottom: 8 }}>
            {company.name}
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: 13, maxWidth: 500 }}>
            Distress probability modeled from {' '}
            <span className="text-amber">NLP signals</span>,
            {' '}<span className="text-amber">financial ratios</span>, and
            {' '}<span className="text-amber">6-month signal forecasts</span>.
          </p>
        </div>
        <RiskGauge score={risk.score} tier={risk.tier} />
      </div>

      {/* ── Key signal metrics ──────────────────────────── */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: 12, marginBottom: 24,
      }}>
        <SignalMetric
          label="Headcount Δ" icon={Users}
          value={sig.headcount_mom_pct}
          unit="%" good={sig.headcount_mom_pct > 0}
        />
        <SignalMetric
          label="News Sentiment" icon={Newspaper}
          value={sig.news_sentiment_score}
          good={sig.news_sentiment_score > 0}
        />
        <SignalMetric
          label="Cash Ratio" icon={DollarSign}
          value={sig.cash_ratio}
          good={sig.cash_ratio > 1.0}
        />
        <SignalMetric
          label="Distress Keywords" icon={AlertTriangle}
          value={sig.distress_keyword_score}
          good={sig.distress_keyword_score < 0.3}
        />
      </div>

      {/* ── Secondary metrics ───────────────────────────── */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: 12, marginBottom: 28,
      }}>
        <SignalMetric label="Debt / Equity"      value={sig.debt_to_equity}     good={sig.debt_to_equity < 2} />
        <SignalMetric label="Operating Margin"   value={sig.operating_margin}   unit="" good={sig.operating_margin > 0} />
        <SignalMetric label="Ops/Finance Roles %" value={sig.pct_ops_finance_roles != null ? (sig.pct_ops_finance_roles * 100).toFixed(1) : null} unit="%" good={sig.pct_ops_finance_roles < 0.4} />
        <SignalMetric label="Headcount"          value={sig.headcount} />
      </div>

      {/* ── Tab navigation ──────────────────────────────── */}
      <div style={{
        display: 'flex', gap: 4, marginBottom: 20,
        borderBottom: '1px solid var(--border)',
        paddingBottom: 0,
      }}>
        {TABS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            style={{
              display: 'flex', alignItems: 'center', gap: 7,
              padding: '10px 16px',
              background: 'none', border: 'none', cursor: 'pointer',
              fontFamily: 'var(--font-body)', fontSize: 13,
              fontWeight: activeTab === key ? 600 : 400,
              color: activeTab === key ? 'var(--amber)' : 'var(--text-secondary)',
              borderBottom: activeTab === key ? '2px solid var(--amber)' : '2px solid transparent',
              marginBottom: -1,
              transition: 'all 0.15s',
            }}
          >
            <Icon size={13} />
            {label}
          </button>
        ))}
      </div>

      {/* ── Tab content ─────────────────────────────────── */}
      <div className="card" style={{ minHeight: 320 }}>
        <div className="card-body">

          {/* Signal timeline */}
          {activeTab === 'signals' && (
            sigLoading
              ? <Skeleton height={280} />
              : <SignalTimelineChart data={signals || []} />
          )}

          {/* Forecast */}
          {activeTab === 'forecast' && (
            fcLoading
              ? <Skeleton height={280} />
              : forecast?.forecasts?.length === 0
                ? <EmptyState message="No forecasts available. Run Phase 3 first." />
                : <ForecastChart
                    signals={signals || []}
                    forecasts={forecast?.forecasts || forecast || []}
                  />
          )}

          {/* SHAP */}
          {activeTab === 'shap' && (
            shapLoading
              ? <Skeleton height={280} />
              : shapData?.shap_values?.length === 0
                ? <EmptyState message="SHAP values not available. Ensure XGBoost model is loaded." />
                : <ShapWaterfall values={shapData?.shap_values || []} />
          )}

          {/* Analyst brief */}
          {activeTab === 'brief' && (
            briefLoading
              ? <Skeleton height={280} />
              : <AnalystBrief brief={brief} />
          )}
        </div>
      </div>
    </div>
  )
}
