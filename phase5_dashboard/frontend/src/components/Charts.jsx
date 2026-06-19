// src/components/Charts.jsx
import { useState } from 'react'
import {
  AreaChart, Area, LineChart, Line, ComposedChart,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ReferenceLine, ResponsiveContainer, Cell,
} from 'recharts'
import { CTooltip } from './UI'

const COLORS = {
  news_sentiment_score:    '#00D4FF',
  distress_keyword_score:  '#FF4545',
  headcount_mom_pct:       '#FFD166',
  glassdoor_rating:        '#A78BFA',
  cash_ratio:              '#22C55E',
  debt_to_equity:          '#FF7A35',
  operating_margin:        '#34D399',
  pct_ops_finance_roles:   '#F87171',
  job_postings_total:      '#60A5FA',
}

const LABELS = {
  news_sentiment_score:    'News Sentiment',
  distress_keyword_score:  'Distress Keywords',
  headcount_mom_pct:       'Headcount Δ%',
  glassdoor_rating:        'Glassdoor',
  cash_ratio:              'Cash Ratio',
  debt_to_equity:          'Debt/Equity',
  operating_margin:        'Op Margin',
  pct_ops_finance_roles:   'Ops/Finance %',
  job_postings_total:      'Job Postings',
}

const AX = {
  tick: { fontFamily: 'JetBrains Mono, monospace', fontSize: 9, fill: '#344556' },
}

/* ── Signal selector chip (not a pill) ─────────────────── */
function SignalChip({ sig, active, onClick }) {
  return (
    <button onClick={onClick} style={{
      display: 'flex', alignItems: 'center', gap: 6,
      padding: '4px 10px',
      background: active ? `${COLORS[sig]}14` : 'transparent',
      border: `1px solid ${active ? COLORS[sig] + '50' : 'var(--line)'}`,
      borderRadius: 5,
      cursor: 'pointer',
      transition: 'all 0.12s',
    }}>
      <span style={{
        width: 6, height: 6, borderRadius: '50%',
        background: COLORS[sig] || '#888',
        opacity: active ? 1 : 0.3,
        flexShrink: 0,
      }} />
      <span style={{
        fontFamily: 'var(--f-mono)', fontSize: 9,
        letterSpacing: '0.06em',
        color: active ? (COLORS[sig] || 'var(--t1)') : 'var(--t3)',
        textTransform: 'uppercase',
        whiteSpace: 'nowrap',
      }}>
        {LABELS[sig] || sig}
      </span>
    </button>
  )
}

/* ═══════════════════════════════════════════════════════
   Signal Timeline
══════════════════════════════════════════════════════ */
const TIMELINE_SIGS = [
  'news_sentiment_score', 'distress_keyword_score',
  'headcount_mom_pct', 'cash_ratio', 'operating_margin',
]

export function SignalTimelineChart({ data }) {
  const [selected, setSelected] = useState(['news_sentiment_score', 'distress_keyword_score'])

  if (!data?.length) return (
    <div style={{ padding: '60px 0', textAlign: 'center', fontFamily: 'var(--f-mono)', fontSize: 11, color: 'var(--t3)' }}>
      No signal history available
    </div>
  )

  const toggle = s => setSelected(p => p.includes(s) ? p.filter(x => x !== s) : [...p, s])

  const chartData = data.map(d => ({ ...d, date: d.date?.slice(0, 7) }))

  return (
    <div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 20 }}>
        {TIMELINE_SIGS.map(s => (
          <SignalChip key={s} sig={s} active={selected.includes(s)} onClick={() => toggle(s)} />
        ))}
      </div>

      <ResponsiveContainer width="100%" height={240}>
        <ComposedChart data={chartData} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
          <CartesianGrid stroke="rgba(255,255,255,0.03)" vertical={false} />
          <XAxis dataKey="date" {...AX} tickLine={false} axisLine={false}
            interval="preserveStartEnd"
            tickFormatter={d => d?.slice(0, 7)}
          />
          <YAxis {...AX} tickLine={false} axisLine={false} width={36} />
          <Tooltip content={<CTooltip fmt={v => v?.toFixed(3)} />} />
          <ReferenceLine y={0} stroke="rgba(255,255,255,0.06)" />
          {selected.map(s => (
            <Area key={s} type="monotone" dataKey={s} name={LABELS[s]}
              stroke={COLORS[s]} fill={COLORS[s] + '12'}
              strokeWidth={1.5} dot={false}
              activeDot={{ r: 3, strokeWidth: 0, fill: COLORS[s] }}
            />
          ))}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}


/* ═══════════════════════════════════════════════════════
   Forecast Chart — historical + forward projection
══════════════════════════════════════════════════════ */
const FC_SIGS = [
  'news_sentiment_score', 'headcount', 'distress_keyword_score', 'cash_ratio',
]

export function ForecastChart({ signals, forecasts }) {
  const [activeSig, setActiveSig] = useState('news_sentiment_score')

  const fc = Array.isArray(forecasts) ? forecasts : (forecasts?.forecasts || [])

  if (!fc?.length) return (
    <div style={{ padding: '60px 0', textAlign: 'center', fontFamily: 'var(--f-mono)', fontSize: 11, color: 'var(--t3)' }}>
      No forecast data. Run phase3_forecasting/forecaster.py first.
    </div>
  )

  const color = COLORS[activeSig] || 'var(--cyan)'

  const hist = (signals || [])
    .filter(d => d[activeSig] != null)
    .map(d => ({ date: d.date?.slice(0, 7), value: d[activeSig] }))

  const fcKey = `${activeSig}_forecast`
  const fwd = fc
    .filter(d => d.feature === fcKey)
    .map(d => ({
      date:  `${d.year}-${String(d.month).padStart(2,'0')}`,
      forecast: d.value,
      lower: d.value_lower,
      upper: d.value_upper,
    }))

  // Bridge: last historical point repeated as first forecast point
  const combined = [
    ...hist,
    ...(hist.length ? [{ date: hist[hist.length-1].date, bridge: hist[hist.length-1].value }] : []),
    ...fwd.map(d => ({ date: d.date, forecast: d.forecast, lower: d.lower, upper: d.upper })),
  ]

  const hasFc = fwd.length > 0

  return (
    <div>
      {/* Signal selector */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 16 }}>
        {FC_SIGS.map(s => {
          const has = fc.some(d => d.feature === `${s}_forecast`)
          return (
            <SignalChip key={s} sig={s}
              active={activeSig === s}
              onClick={() => has && setActiveSig(s)}
            />
          )
        })}
      </div>

      {/* Legend */}
      <div style={{
        display: 'flex', gap: 20, marginBottom: 14,
        fontFamily: 'var(--f-mono)', fontSize: 9,
        letterSpacing: '0.1em', textTransform: 'uppercase',
        color: 'var(--t3)',
      }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <svg width="18" height="2"><line x1="0" y1="1" x2="18" y2="1" stroke={color} strokeWidth="1.5"/></svg>
          Historical
        </span>
        {hasFc && (
          <>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <svg width="18" height="2"><line x1="0" y1="1" x2="18" y2="1" stroke={color} strokeWidth="1.5" strokeDasharray="4 3"/></svg>
              Forecast
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ display: 'inline-block', width: 14, height: 8, background: color+'18', borderRadius: 2 }} />
              Confidence
            </span>
          </>
        )}
      </div>

      <ResponsiveContainer width="100%" height={240}>
        <ComposedChart data={combined} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
          <CartesianGrid stroke="rgba(255,255,255,0.03)" vertical={false} />
          <XAxis dataKey="date" {...AX} tickLine={false} axisLine={false} interval="preserveStartEnd" />
          <YAxis {...AX} tickLine={false} axisLine={false} width={36} />
          <Tooltip content={<CTooltip fmt={v => v?.toFixed(3)} />} />
          <ReferenceLine y={0} stroke="rgba(255,255,255,0.06)" />

          {/* Confidence band */}
          <Area type="monotone" dataKey="upper" stroke="none"
            fill={color + '18'} legendType="none" activeDot={false} />
          <Area type="monotone" dataKey="lower" stroke="none"
            fill="var(--surface)" legendType="none" activeDot={false} />

          {/* Historical */}
          <Line type="monotone" dataKey="value" name={LABELS[activeSig]}
            stroke={color} strokeWidth={1.5}
            dot={false} activeDot={{ r: 3, strokeWidth: 0 }}
          />
          {/* Bridge */}
          <Line type="monotone" dataKey="bridge" name=""
            stroke={color} strokeWidth={1.5}
            dot={false} activeDot={false} legendType="none"
          />
          {/* Forecast dashed */}
          <Line type="monotone" dataKey="forecast" name="Forecast"
            stroke={color} strokeWidth={1.5} strokeDasharray="5 3"
            dot={false} activeDot={{ r: 3, strokeWidth: 0 }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}


/* ═══════════════════════════════════════════════════════
   SHAP Waterfall — centered bar chart
══════════════════════════════════════════════════════ */
export function ShapWaterfall({ values }) {
  if (!values?.length) return (
    <div style={{ padding: '60px 0', textAlign: 'center', fontFamily: 'var(--f-mono)', fontSize: 11, color: 'var(--t3)' }}>
      SHAP values unavailable. Ensure model is loaded.
    </div>
  )

  const maxAbs = Math.max(...values.map(v => Math.abs(v.value)), 0.001)

  const fmt = f => f
    .replace(/_forecast$/, ' (fc)')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase())
    .slice(0, 22)

  return (
    <div>
      {/* Legend */}
      <div style={{
        display: 'flex', gap: 20, marginBottom: 16,
        fontFamily: 'var(--f-mono)', fontSize: 9,
        letterSpacing: '0.1em', textTransform: 'uppercase',
        color: 'var(--t3)',
      }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: 2, background: 'var(--red)', opacity: 0.5 }} />
          Increases risk
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: 2, background: 'var(--green)', opacity: 0.5 }} />
          Reduces risk
        </span>
      </div>

      {values.slice(0, 12).map((item, i) => {
        const pct   = (Math.abs(item.value) / maxAbs) * 45  // max 45% of half-width
        const pos   = item.value > 0
        const color = pos ? 'var(--red)' : 'var(--green)'

        return (
          <div key={i} className="shap-row" style={{
            animationDelay: `${i * 25}ms`,
            animation: 'fadeUp 0.3s ease both',
          }}>
            {/* Feature name */}
            <div style={{
              fontFamily: 'var(--f-mono)', fontSize: 10,
              color: 'var(--t2)', letterSpacing: '0.03em',
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
            }} title={item.feature}>
              {fmt(item.feature)}
            </div>

            {/* Bar centered at 50% */}
            <div style={{ position: 'relative', height: 22 }}>
              {/* Center line */}
              <div style={{
                position: 'absolute', left: '50%', top: 0, bottom: 0,
                width: 1, background: 'var(--line-bright)', transform: 'translateX(-50%)',
              }} />
              {/* Bar */}
              <div style={{
                position: 'absolute',
                top: '20%', height: '60%',
                borderRadius: 3,
                background: color,
                opacity: 0.7,
                width: `${pct}%`,
                ...(pos
                  ? { left: '50%' }
                  : { right: `${50}%`, left: `${50 - pct}%` }
                ),
                transition: 'width 0.5s cubic-bezier(0.4,0,0.2,1)',
              }} />
            </div>

            {/* Value */}
            <div style={{
              fontFamily: 'var(--f-mono)', fontSize: 10,
              color, textAlign: 'right',
            }}>
              {pos ? '+' : ''}{item.value.toFixed(3)}
            </div>
          </div>
        )
      })}
    </div>
  )
}
