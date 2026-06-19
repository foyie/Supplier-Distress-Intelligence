import { useParams } from 'react-router-dom'
import { useState } from 'react'
import {
  Activity, TrendingUp, BarChart2, FileText,
  Users, Newspaper, DollarSign, AlertTriangle,
  Download, ArrowUpRight,
} from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { api } from '../utils/api'
import {
  RiskIndicator, Skel, Empty, MetricTile,
  Eyebrow, SectionTitle,
} from '../components/UI'
import { SignalTimelineChart, ForecastChart, ShapWaterfall } from '../components/Charts'

/* ── SVG Arc Gauge ────────────────────────────────────── */
function ArcGauge({ score = 0, tier }) {
  const colors = { CRITICAL:'#FF4545', HIGH:'#FF7A35', MEDIUM:'#FFD166', LOW:'#22C55E' }
  const color  = colors[tier] || '#344556'
  const R = 80, SW = 10
  const circ = Math.PI * R        // half circle arc length
  const fill = (score / 100) * circ
  const cx = 100, cy = 92

  return (
    <div style={{ textAlign: 'center' }}>
      <svg width="200" height="110" viewBox="0 0 200 110">
        {/* Track */}
        <path
          d={`M ${cx - R} ${cy} A ${R} ${R} 0 0 1 ${cx + R} ${cy}`}
          fill="none"
          stroke="var(--raised)"
          strokeWidth={SW}
          strokeLinecap="round"
        />
        {/* Fill */}
        <path
          d={`M ${cx - R} ${cy} A ${R} ${R} 0 0 1 ${cx + R} ${cy}`}
          fill="none"
          stroke={color}
          strokeWidth={SW}
          strokeLinecap="round"
          strokeDasharray={`${fill} ${circ}`}
          style={{
            filter: `drop-shadow(0 0 6px ${color}88)`,
            transition: 'stroke-dasharray 1s cubic-bezier(0.4,0,0.2,1)',
          }}
        />
        {/* Score */}
        <text x={cx} y={cy - 14} textAnchor="middle"
          style={{ fontFamily: 'Space Grotesk, sans-serif', fontSize: 34, fontWeight: 700, fill: color, letterSpacing: '-1px' }}
        >
          {score?.toFixed(0)}
        </text>
        <text x={cx} y={cy + 2} textAnchor="middle"
          style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 8, fill: 'var(--t3)', letterSpacing: '0.14em' }}
        >
          RISK SCORE / 100
        </text>
      </svg>
    </div>
  )
}

/* ── Horizontal signal bar ────────────────────────────── */
function SignalRow({ label, value, max = 1, good, format }) {
  const pct = Math.min(100, Math.max(0, (Math.abs(value || 0) / max) * 100))
  const color = good === true ? 'var(--green)' : good === false ? 'var(--red)' : 'var(--cyan)'
  const displayVal = format ? format(value) : value?.toFixed?.(2) ?? '—'

  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <span style={{ fontFamily: 'var(--f-mono)', fontSize: 10, color: 'var(--t3)', letterSpacing: '0.06em' }}>
          {label}
        </span>
        <span style={{ fontFamily: 'var(--f-mono)', fontSize: 11, color }}>
          {value != null ? displayVal : '—'}
        </span>
      </div>
      <div style={{ height: 3, background: 'var(--raised)', borderRadius: 2, overflow: 'hidden' }}>
        <div style={{
          height: '100%', width: `${pct}%`,
          background: color, borderRadius: 2,
          transition: 'width 0.8s cubic-bezier(0.4,0,0.2,1)',
          boxShadow: value != null ? `0 0 4px ${color}66` : 'none',
        }} />
      </div>
    </div>
  )
}

/* ── Analyst brief panel ──────────────────────────────── */
function AnalystBrief({ brief }) {
  if (!brief) return <Empty message="Brief unavailable" />

  const tierColors = { CRITICAL:'#FF4545', HIGH:'#FF7A35', MEDIUM:'#FFD166', LOW:'#22C55E' }
  const color = tierColors[brief.risk_tier] || 'var(--t2)'

  return (
    <div>
      {/* Header */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
        marginBottom: 20,
      }}>
        <div>
          <Eyebrow style={{ marginBottom: 6 }}>
            Procurement Risk Brief · {brief.generated_at}
          </Eyebrow>
          <h2 style={{ fontSize: 20, letterSpacing: '-0.3px' }}>{brief.company_name}</h2>
          <div style={{ marginTop: 6, display: 'flex', alignItems: 'center', gap: 8 }}>
            <RiskIndicator tier={brief.risk_tier} />
            <span style={{ fontFamily: 'var(--f-mono)', fontSize: 11, color: 'var(--t3)' }}>
              Score: {brief.risk_score?.toFixed(1)}
            </span>
          </div>
        </div>
        <button className="btn btn-ghost" style={{ fontSize: 11 }}>
          <Download size={11} /> Export PDF
        </button>
      </div>

      {/* Signals */}
      {brief.signal_summary?.length > 0 && (
        <>
          <Eyebrow style={{ marginBottom: 10 }}>Active Signals</Eyebrow>
          {brief.signal_summary.map((s, i) => (
            <div key={i} className="brief-signal">
              <div style={{
                width: 4, height: 4, borderRadius: '50%',
                background: color, marginTop: 5, flexShrink: 0,
              }} />
              <span>{s}</span>
            </div>
          ))}
        </>
      )}

      <div className="hr mt-16 mb-16" />

      {/* Recommendation */}
      <Eyebrow style={{ marginBottom: 10 }}>Recommendation</Eyebrow>
      <div style={{
        background: `${color}0C`,
        border: `1px solid ${color}25`,
        borderLeft: `3px solid ${color}`,
        borderRadius: '0 8px 8px 0',
        padding: '14px 16px',
        fontSize: 13,
        color: 'var(--t2)',
        lineHeight: 1.7,
      }}>
        {brief.recommendation}
      </div>

      <div className="hr mt-16 mb-12" />

      {/* Disclaimer */}
      <div style={{
        fontFamily: 'var(--f-mono)', fontSize: 9,
        color: 'var(--t3)', letterSpacing: '0.05em',
        lineHeight: 1.6,
      }}>
        {brief.disclaimer}
      </div>
    </div>
  )
}

/* ── Tab config ───────────────────────────────────────── */
const TABS = [
  { key: 'signals',  label: 'Signal History', icon: Activity },
  { key: 'forecast', label: '6M Forecast',    icon: TrendingUp },
  { key: 'shap',     label: 'SHAP Analysis',  icon: BarChart2 },
  { key: 'brief',    label: 'Analyst Brief',  icon: FileText },
]

/* ══════════════════════════════════════════════════════
   Main page
══════════════════════════════════════════════════════ */
export default function CompanyDetail() {
  const { id }       = useParams()
  const [tab, setTab] = useState('signals')

  const { data: company, loading: cl } = useApi(() => api.company(id),  [id])
  const { data: signals, loading: sl } = useApi(() => api.signals(id),  [id])
  const { data: forecast,loading: fl } = useApi(() => api.forecast(id), [id])
  const { data: shapData,loading: hl } = useApi(() => api.shap(id),     [id])
  const { data: brief,   loading: bl } = useApi(() => api.brief(id),    [id])

  if (cl) return (
    <div style={{ padding: 24 }}>
      <Skel w={280} h={28} style={{ marginBottom: 16 }} />
      <div style={{ display: 'grid', gridTemplateColumns:'1fr 1fr', gap: 16 }}>
        <Skel h={200} /><Skel h={200} />
      </div>
    </div>
  )
  if (!company) return <Empty message="Company not found" />

  const risk = company.risk || {}
  const sig  = company.latest_signals || {}

  return (
    <div className="fade-up">

      {/* ── Company header ──────────────────────────────── */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr auto',
        gap: 24,
        alignItems: 'start',
        background: 'var(--surface)',
        border: '1px solid var(--line)',
        borderRadius: 10,
        padding: '24px 28px',
        marginBottom: 20,
      }}>
        <div>
          {/* Sector eyebrow */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
            <Eyebrow>{company.sector}</Eyebrow>
            <span style={{ width: 3, height: 3, borderRadius: '50%', background: 'var(--t3)' }} />
            <Eyebrow>{company.industry}</Eyebrow>
          </div>

          <h1 style={{ fontSize: 26, letterSpacing: '-0.5px', marginBottom: 12 }}>
            {company.name}
          </h1>

          {/* Risk status row */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
            <RiskIndicator tier={risk.tier} />
            <span style={{ width: 1, height: 14, background: 'var(--line)' }} />
            <span style={{ fontFamily: 'var(--f-mono)', fontSize: 11, color: 'var(--t3)' }}>
              MoM Δ{' '}
              <span style={{ color: risk.delta > 0 ? 'var(--red)' : 'var(--green)' }}>
                {risk.delta > 0 ? '+' : ''}{risk.delta?.toFixed(1) ?? '—'}
              </span>
            </span>
            <span style={{ width: 1, height: 14, background: 'var(--line)' }} />
            {company.distress_label && (
              <span style={{
                fontFamily: 'var(--f-mono)', fontSize: 9,
                letterSpacing: '0.1em', textTransform: 'uppercase',
                color: 'var(--red)', opacity: 0.8,
              }}>
                ⬤ Known distress event
              </span>
            )}
          </div>

          {/* Signal bars */}
          <div style={{ marginTop: 20, maxWidth: 480 }}>
            <SignalRow label="NEWS SENTIMENT"      value={sig.news_sentiment_score}   max={1}   good={sig.news_sentiment_score > 0} format={v => v?.toFixed(2)} />
            <SignalRow label="DISTRESS KEYWORDS"   value={sig.distress_keyword_score} max={1}   good={false} format={v => v?.toFixed(3)} />
            <SignalRow label="CASH RATIO"          value={sig.cash_ratio}             max={3}   good={sig.cash_ratio > 1} />
            <SignalRow label="OPS/FINANCE ROLES %"  value={sig.pct_ops_finance_roles}  max={1}   good={sig.pct_ops_finance_roles < 0.4} format={v => (v * 100).toFixed(0) + '%'} />
          </div>
        </div>

        {/* Right: Gauge */}
        <div>
          <ArcGauge score={risk.score} tier={risk.tier} />
        </div>
      </div>

      {/* ── Metric tiles ─────────────────────────────────── */}
      <div className="grid-4 mb-20">
        <MetricTile label="Headcount Δ%"     value={sig.headcount_mom_pct}     unit="%" good={sig.headcount_mom_pct > 0}    icon={Users} />
        <MetricTile label="Debt / Equity"    value={sig.debt_to_equity}                 good={sig.debt_to_equity < 2}       icon={DollarSign} />
        <MetricTile label="Operating Margin" value={sig.operating_margin}      unit="%" good={sig.operating_margin > 0}     icon={TrendingUp} />
        <MetricTile label="News Volume"      value={sig.news_volume}                                                          icon={Newspaper} />
      </div>

      {/* ── Tabs ─────────────────────────────────────────── */}
      <div className="card">
        <div className="card-head" style={{ padding: 0 }}>
          <div className="tab-bar" style={{ margin: 0, width: '100%', padding: '0 18px' }}>
            {TABS.map(({ key, label, icon: Icon }) => (
              <button
                key={key}
                onClick={() => setTab(key)}
                className={`tab-btn ${tab === key ? 'active' : ''}`}
              >
                <Icon size={12} />
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="card-body" style={{ minHeight: 300 }}>
          {tab === 'signals' && (
            sl ? <Skel h={260} /> : <SignalTimelineChart data={signals || []} />
          )}
          {tab === 'forecast' && (
            fl ? <Skel h={260} /> : (
              <ForecastChart
                signals={signals || []}
                forecasts={forecast?.forecasts || forecast || []}
              />
            )
          )}
          {tab === 'shap' && (
            hl ? <Skel h={260} /> : (
              shapData?.shap_values?.length > 0
                ? <ShapWaterfall values={shapData.shap_values} />
                : <Empty message={shapData?.error || 'SHAP values unavailable — ensure model is loaded'} />
            )
          )}
          {tab === 'brief' && (
            bl ? <Skel h={260} /> : <AnalystBrief brief={brief} />
          )}
        </div>
      </div>
    </div>
  )
}
