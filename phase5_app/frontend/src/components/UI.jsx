import { clsx } from 'clsx'

// ── Tier badge ─────────────────────────────────────────────
export function TierBadge({ tier }) {
  return (
    <span className={clsx('tier-badge', `tier-${tier}`)}>
      <span className={clsx(
        'w-1.5 h-1.5 rounded-full animate-pulse-dot',
        tier === 'HIGH'   && 'bg-high',
        tier === 'MEDIUM' && 'bg-mid',
        tier === 'LOW'    && 'bg-low',
      )} />
      {tier}
    </span>
  )
}

// ── Risk score gauge ───────────────────────────────────────
export function ScoreGauge({ score }) {
  const pct    = Math.round(score * 100)
  const color  = pct >= 65 ? '#C0392B' : pct >= 35 ? '#D4860A' : '#27AE60'
  const r      = 38
  const circ   = 2 * Math.PI * r
  const offset = circ * (1 - pct / 100)

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width={96} height={96} className="-rotate-90">
        <circle cx={48} cy={48} r={r} fill="none" stroke="#E8E5DF" strokeWidth={7} />
        <circle
          cx={48} cy={48} r={r} fill="none"
          stroke={color} strokeWidth={7}
          strokeDasharray={circ}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: 'stroke-dashoffset 0.8s ease' }}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="font-mono text-xl font-medium leading-none" style={{ color }}>
          {pct}
        </span>
        <span className="text-[10px] text-ash font-mono">/100</span>
      </div>
    </div>
  )
}

// ── Delta chip ─────────────────────────────────────────────
export function DeltaChip({ delta }) {
  if (delta === null || delta === undefined) return null
  const pct = Math.round(delta * 100)
  if (pct === 0) return <span className="text-ash font-mono text-xs">—</span>
  const up = pct > 0
  return (
    <span className={clsx(
      'font-mono text-xs font-medium',
      up ? 'text-high' : 'text-low'
    )}>
      {up ? '▲' : '▼'} {Math.abs(pct)}
    </span>
  )
}

// ── Loading skeleton ───────────────────────────────────────
export function Skeleton({ className }) {
  return (
    <div className={clsx('animate-pulse bg-mist rounded', className)} />
  )
}

// ── Error state ────────────────────────────────────────────
export function ErrorState({ message }) {
  return (
    <div className="card border-red-200 bg-red-50 text-center py-10">
      <p className="text-high font-mono text-sm">Error: {message}</p>
      <p className="text-ash text-xs mt-1">Check that the API server is running on :8000</p>
    </div>
  )
}

// ── Signal value formatter ─────────────────────────────────
export function fmt(val, type = 'number') {
  if (val === null || val === undefined) return '—'
  if (type === 'pct')    return `${(val * 100).toFixed(1)}%`
  if (type === 'rating') return val.toFixed(1)
  if (type === 'score')  return Math.round(val * 100)
  return val.toFixed(2)
}
