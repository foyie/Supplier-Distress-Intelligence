// src/components/UI.jsx — shared primitives

import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

/* ── Skeleton ─────────────────────────────────────────── */
export function Skel({ w = '100%', h = 14, style = {} }) {
  return <div className="skel" style={{ width: w, height: h, ...style }} />
}

/* ── Risk indicator (dot + label, no pill) ─────────────── */
export function RiskIndicator({ tier, showLabel = true }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
      <span className={`risk-dot dot-${tier}`} />
      {showLabel && (
        <span className={`risk-label risk-${tier}`}>{tier}</span>
      )}
    </div>
  )
}

/* ── Score number ─────────────────────────────────────── */
export function ScoreNum({ score, tier }) {
  const colors = { CRITICAL: 'var(--red)', HIGH: 'var(--orange)', MEDIUM: 'var(--yellow)', LOW: 'var(--green)' }
  return (
    <span style={{
      fontFamily: 'var(--f-mono)',
      fontSize: 13,
      fontWeight: 600,
      color: colors[tier] || 'var(--t2)',
      letterSpacing: '0.03em',
    }}>
      {score?.toFixed(1)}
    </span>
  )
}

/* ── Delta ────────────────────────────────────────────── */
export function Delta({ value }) {
  if (value == null) return <span className="delta-flat">—</span>
  const cls = value > 0.5 ? 'delta-up' : value < -0.5 ? 'delta-down' : 'delta-flat'
  const Icon = value > 0.5 ? TrendingUp : value < -0.5 ? TrendingDown : Minus
  return (
    <span className={cls} style={{ display: 'inline-flex', alignItems: 'center', gap: 3 }}>
      <Icon size={10} />
      {value > 0 ? '+' : ''}{value?.toFixed(1)}
    </span>
  )
}

/* ── Eyebrow label ────────────────────────────────────── */
export function Eyebrow({ children, style = {} }) {
  return (
    <div className="eyebrow" style={style}>{children}</div>
  )
}

/* ── Section title ────────────────────────────────────── */
export function SectionTitle({ label, right }) {
  return (
    <div className="flex items-c justify-b mb-16">
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{ width: 2, height: 14, background: 'var(--cyan)', borderRadius: 1 }} />
        <Eyebrow>{label}</Eyebrow>
      </div>
      {right}
    </div>
  )
}

/* ── Empty state ──────────────────────────────────────── */
export function Empty({ message }) {
  return (
    <div style={{
      padding: '52px 24px', textAlign: 'center',
      fontFamily: 'var(--f-mono)', fontSize: 11,
      color: 'var(--t3)',
      letterSpacing: '0.05em',
    }}>
      {message || 'No data available'}
    </div>
  )
}

/* ── Inline sparkline (SVG) ────────────────────────────── */
export function Sparkline({ data = [], color = 'var(--cyan)', width = 80, height = 28 }) {
  if (!data || data.length < 2) {
    return <div style={{ width, height, opacity: 0.2, background: 'var(--line)' }} />
  }

  const vals = data.filter(v => v != null && !isNaN(v))
  if (vals.length < 2) return null

  const min = Math.min(...vals)
  const max = Math.max(...vals)
  const range = max - min || 1
  const pad = 2

  const pts = vals.map((v, i) => {
    const x = pad + (i / (vals.length - 1)) * (width - pad * 2)
    const y = pad + ((1 - (v - min) / range) * (height - pad * 2))
    return `${x},${y}`
  })

  const polyline = pts.join(' ')
  const last = pts[pts.length - 1].split(',')
  const isUp = vals[vals.length - 1] > vals[0]
  const lineColor = color === 'auto' ? (isUp ? 'var(--red)' : 'var(--green)') : color

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{ overflow: 'visible' }}>
      <polyline
        points={polyline}
        fill="none"
        stroke={lineColor}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity="0.9"
      />
      {/* Last point dot */}
      <circle
        cx={last[0]} cy={last[1]} r="2.5"
        fill={lineColor}
      />
    </svg>
  )
}

/* ── Recharts tooltip ─────────────────────────────────── */
export function CTooltip({ active, payload, label, fmt }) {
  if (!active || !payload?.length) return null
  return (
    <div className="ct">
      <div style={{ color: 'var(--t2)', marginBottom: 5, fontSize: 10 }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.color || 'var(--t1)', marginBottom: 2 }}>
          <span style={{ color: 'var(--t2)', marginRight: 6 }}>{p.name}</span>
          <strong>{fmt ? fmt(p.value) : (typeof p.value === 'number' ? p.value.toFixed(3) : p.value)}</strong>
        </div>
      ))}
    </div>
  )
}

/* ── Metric tile ──────────────────────────────────────── */
export function MetricTile({ label, value, unit = '', good, icon: Icon, accent }) {
  const color = good === true ? 'var(--green)' : good === false ? 'var(--red)' : accent || 'var(--t1)'
  return (
    <div className="metric-tile">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Eyebrow>{label}</Eyebrow>
        {Icon && <Icon size={12} color="var(--t3)" />}
      </div>
      <div className="metric-value" style={{ color }}>
        {value != null
          ? (typeof value === 'number' ? value.toFixed(2) : value) + unit
          : <span style={{ color: 'var(--t3)', fontSize: 16 }}>—</span>
        }
      </div>
    </div>
  )
}
