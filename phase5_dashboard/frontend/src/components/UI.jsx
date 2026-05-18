// src/components/UI.jsx — shared primitives

import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

/* ── Skeleton loader ─────────────────────────────────── */
export function Skeleton({ width = '100%', height = 16, style = {} }) {
  return (
    <div className="skeleton" style={{ width, height, ...style }} />
  )
}

/* ── Tier badge ──────────────────────────────────────── */
export function TierBadge({ tier }) {
  return (
    <span className={`tier-badge tier-${tier}`}>{tier}</span>
  )
}

/* ── Score pill ──────────────────────────────────────── */
export function ScorePill({ score, tier }) {
  const colors = {
    CRITICAL: '#FF3B3B', HIGH: '#FF6B35',
    MEDIUM: '#F5C518',   LOW: '#22C55E',
  }
  return (
    <span style={{
      fontFamily: 'var(--font-mono)',
      fontSize: 13,
      fontWeight: 500,
      color: colors[tier] || '#888',
    }}>
      {score?.toFixed(1)}
    </span>
  )
}

/* ── Delta indicator ─────────────────────────────────── */
export function Delta({ value }) {
  if (value == null) return <span style={{ color: 'var(--text-muted)' }}>—</span>
  const up   = value > 0
  const down = value < 0
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 3,
      fontFamily: 'var(--font-mono)', fontSize: 11,
      color: up ? '#FF3B3B' : down ? '#22C55E' : 'var(--text-muted)',
    }}>
      {up   ? <TrendingUp  size={11} /> : null}
      {down ? <TrendingDown size={11} /> : null}
      {!up && !down ? <Minus size={11} /> : null}
      {up ? '+' : ''}{value?.toFixed(1)}
    </span>
  )
}

/* ── Signal bar ──────────────────────────────────────── */
export function SignalBar({ value, max = 1, color = 'var(--amber)' }) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100))
  return (
    <div className="signal-bar-track">
      <div className="signal-bar-fill" style={{ width: `${pct}%`, background: color }} />
    </div>
  )
}

/* ── Section header ──────────────────────────────────── */
export function SectionHeader({ label, children }) {
  return (
    <div className="flex items-center justify-between mb-16">
      <span style={{
        fontFamily: 'var(--font-mono)',
        fontSize: 10,
        fontWeight: 500,
        letterSpacing: '0.12em',
        textTransform: 'uppercase',
        color: 'var(--text-muted)',
        display: 'flex',
        alignItems: 'center',
        gap: 8,
      }}>
        <span style={{
          display: 'inline-block', width: 20, height: 1,
          background: 'var(--amber)', opacity: 0.6,
        }} />
        {label}
      </span>
      {children}
    </div>
  )
}

/* ── Empty state ─────────────────────────────────────── */
export function EmptyState({ message = 'No data available' }) {
  return (
    <div style={{
      padding: '48px 24px',
      textAlign: 'center',
      color: 'var(--text-muted)',
      fontFamily: 'var(--font-mono)',
      fontSize: 12,
    }}>
      {message}
    </div>
  )
}

/* ── Recharts custom tooltip ─────────────────────────── */
export function ChartTooltip({ active, payload, label, formatter }) {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: 'var(--bg-elevated)',
      border: '1px solid var(--border-bright)',
      borderRadius: 8,
      padding: '10px 14px',
      fontFamily: 'var(--font-mono)',
      fontSize: 12,
    }}>
      <div style={{ color: 'var(--text-muted)', marginBottom: 6, fontSize: 11 }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.color || 'var(--text-primary)', marginBottom: 2 }}>
          {p.name}: <strong>{formatter ? formatter(p.value) : p.value?.toFixed?.(3) ?? p.value}</strong>
        </div>
      ))}
    </div>
  )
}

/* ── Stat card ───────────────────────────────────────── */
export function StatCard({ label, value, sub, icon: Icon, accent }) {
  return (
    <div className="stat-card">
      <div className="flex items-center justify-between mb-8">
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: 10,
          letterSpacing: '0.1em', textTransform: 'uppercase',
          color: 'var(--text-muted)',
        }}>{label}</span>
        {Icon && (
          <div style={{
            width: 28, height: 28, borderRadius: 7,
            background: accent ? `${accent}18` : 'var(--bg-elevated)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <Icon size={13} color={accent || 'var(--text-muted)'} />
          </div>
        )}
      </div>
      <div style={{
        fontFamily: 'var(--font-display)',
        fontSize: 28,
        fontWeight: 700,
        color: accent || 'var(--text-primary)',
        lineHeight: 1,
        letterSpacing: '-1px',
      }}>{value ?? '—'}</div>
      {sub && (
        <div style={{
          marginTop: 6, fontSize: 12,
          color: 'var(--text-secondary)',
        }}>{sub}</div>
      )}
    </div>
  )
}
