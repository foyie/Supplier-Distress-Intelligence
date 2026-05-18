// src/components/Charts.jsx
import { useState } from 'react'
import {
  LineChart, Line, AreaChart, Area,
  BarChart, Bar, ComposedChart,
  XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, ResponsiveContainer,
  Cell, PieChart, Pie, Legend,
} from 'recharts'
import { ChartTooltip } from './UI'

/* ── Colour map for signals ───────────────────────────── */
const SIGNAL_COLORS = {
  news_sentiment_score:    '#4A9EFF',
  distress_keyword_score:  '#FF3B3B',
  headcount_mom_pct:       '#F5A623',
  glassdoor_rating:        '#A78BFA',
  cash_ratio:              '#22C55E',
  debt_to_equity:          '#FF6B35',
  operating_margin:        '#34D399',
  pct_ops_finance_roles:   '#F87171',
  job_postings_total:      '#60A5FA',
}

const SIGNAL_LABELS = {
  news_sentiment_score:    'News Sentiment',
  distress_keyword_score:  'Distress Keywords',
  headcount_mom_pct:       'Headcount Δ%',
  glassdoor_rating:        'Glassdoor Rating',
  cash_ratio:              'Cash Ratio',
  debt_to_equity:          'Debt / Equity',
  operating_margin:        'Operating Margin',
  pct_ops_finance_roles:   'Ops/Finance Roles %',
  job_postings_total:      'Job Postings',
}

/* ── Shared axis styles ───────────────────────────────── */
const axisStyle = {
  tick: { fontFamily: 'DM Mono, monospace', fontSize: 10, fill: '#3D4E5E' },
  style: { fontFamily: 'DM Mono, monospace', fontSize: 10, fill: '#3D4E5E' },
}

/* ═══════════════════════════════════════════════════════
   Signal Timeline Chart
   Multi-signal selector + area/line chart
══════════════════════════════════════════════════════ */
const TIMELINE_SIGNALS = [
  'news_sentiment_score',
  'distress_keyword_score',
  'headcount_mom_pct',
  'cash_ratio',
  'operating_margin',
]

export function SignalTimelineChart({ data }) {
  const [selected, setSelected] = useState(['news_sentiment_score', 'distress_keyword_score'])

  if (!data?.length) {
    return (
      <div style={{
        padding: '60px 24px', textAlign: 'center',
        color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: 12,
      }}>
        No signal data available
      </div>
    )
  }

  const chartData = data.map(d => ({
    ...d,
    date: d.date?.slice(0, 7), // YYYY-MM
  }))

  const toggle = (sig) => {
    setSelected(prev =>
      prev.includes(sig)
        ? prev.filter(s => s !== sig)
        : [...prev, sig]
    )
  }

  return (
    <div>
      {/* Signal selector pills */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 20 }}>
        {TIMELINE_SIGNALS.map(sig => (
          <button
            key={sig}
            onClick={() => toggle(sig)}
            style={{
              padding: '4px 10px',
              borderRadius: 20,
              border: `1px solid ${selected.includes(sig)
                ? SIGNAL_COLORS[sig] + '80'
                : 'var(--border)'}`,
              background: selected.includes(sig)
                ? SIGNAL_COLORS[sig] + '18'
                : 'transparent',
              color: selected.includes(sig)
                ? SIGNAL_COLORS[sig]
                : 'var(--text-muted)',
              fontFamily: 'var(--font-mono)',
              fontSize: 10,
              cursor: 'pointer',
              transition: 'all 0.15s',
              display: 'flex', alignItems: 'center', gap: 5,
            }}
          >
            <span style={{
              width: 6, height: 6, borderRadius: '50%',
              background: SIGNAL_COLORS[sig],
              display: 'inline-block',
            }} />
            {SIGNAL_LABELS[sig] || sig}
          </button>
        ))}
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={260}>
        <ComposedChart data={chartData} margin={{ top: 4, right: 8, bottom: 4, left: -8 }}>
          <CartesianGrid stroke="rgba(255,255,255,0.04)" strokeDasharray="0" vertical={false} />
          <XAxis dataKey="date" {...axisStyle}
            tickFormatter={d => d?.slice(0, 7)} interval="preserveStartEnd"
          />
          <YAxis {...axisStyle} width={40} />
          <Tooltip
            content={<ChartTooltip formatter={v => v?.toFixed(3)} />}
          />
          <ReferenceLine y={0} stroke="rgba(255,255,255,0.08)" />

          {selected.map(sig => (
            <Area
              key={sig}
              type="monotone"
              dataKey={sig}
              name={SIGNAL_LABELS[sig]}
              stroke={SIGNAL_COLORS[sig]}
              fill={SIGNAL_COLORS[sig] + '18'}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, strokeWidth: 0 }}
            />
          ))}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}


/* ═══════════════════════════════════════════════════════
   Forecast Chart
   Shows historical + 6-month forward with confidence band
══════════════════════════════════════════════════════ */
const FORECAST_SIGNALS = [
  'news_sentiment_score',
  'headcount',
  'distress_keyword_score',
  'cash_ratio',
]

export function ForecastChart({ signals, forecasts }) {
  const [activeSig, setActiveSig] = useState('news_sentiment_score')

  if (!forecasts?.length) {
    return (
      <div style={{
        padding: '60px 24px', textAlign: 'center',
        color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: 12,
      }}>
        No forecast data. Run Phase 3 forecaster.py first.
      </div>
    )
  }

  const color = SIGNAL_COLORS[activeSig] || 'var(--amber)'

  // Historical series
  const hist = (signals || [])
    .filter(d => d[activeSig] != null)
    .map(d => ({
      date:   d.date?.slice(0, 7),
      value:  d[activeSig],
      type:   'historical',
    }))

  // Forecast series for selected signal
  const fcKey = `${activeSig}_forecast`
  const fc = forecasts
    .filter(d => d.feature === fcKey)
    .map(d => ({
      date:  `${d.year}-${String(d.month).padStart(2, '0')}`,
      value: d.value,
      lower: d.value_lower,
      upper: d.value_upper,
      type:  'forecast',
    }))

  // Merge — last historical point bridges to forecast
  const lastHist = hist[hist.length - 1]
  const combined = [
    ...hist,
    ...(lastHist ? [{ ...lastHist, forecast: lastHist.value }] : []),
    ...fc.map(d => ({ date: d.date, forecast: d.value, lower: d.lower, upper: d.upper })),
  ]

  return (
    <div>
      {/* Signal selector */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 20, flexWrap: 'wrap' }}>
        {FORECAST_SIGNALS.map(sig => {
          const hasData = forecasts.some(f => f.feature === `${sig}_forecast`)
          return (
            <button
              key={sig}
              onClick={() => hasData && setActiveSig(sig)}
              style={{
                padding: '4px 10px', borderRadius: 20,
                border: `1px solid ${activeSig === sig
                  ? SIGNAL_COLORS[sig] + '80'
                  : 'var(--border)'}`,
                background: activeSig === sig ? SIGNAL_COLORS[sig] + '18' : 'transparent',
                color: activeSig === sig ? SIGNAL_COLORS[sig] : 'var(--text-muted)',
                fontFamily: 'var(--font-mono)', fontSize: 10,
                cursor: hasData ? 'pointer' : 'not-allowed',
                opacity: hasData ? 1 : 0.4,
                transition: 'all 0.15s',
              }}
            >
              {SIGNAL_LABELS[sig] || sig}
            </button>
          )
        })}
      </div>

      {/* Forecast label */}
      <div style={{
        display: 'flex', gap: 20, marginBottom: 12,
        fontFamily: 'var(--font-mono)', fontSize: 10,
        color: 'var(--text-muted)',
      }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
          <span style={{ display: 'inline-block', width: 20, height: 2, background: color }} />
          Historical
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
          <span style={{ display: 'inline-block', width: 20, height: 2, background: color, opacity: 0.5, borderTop: '2px dashed' }} />
          6-month forecast
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
          <span style={{ display: 'inline-block', width: 20, height: 8, background: color + '20', borderRadius: 2 }} />
          Confidence band
        </span>
      </div>

      <ResponsiveContainer width="100%" height={260}>
        <ComposedChart data={combined} margin={{ top: 4, right: 8, bottom: 4, left: -8 }}>
          <CartesianGrid stroke="rgba(255,255,255,0.04)" strokeDasharray="0" vertical={false} />
          <XAxis dataKey="date" {...axisStyle} interval="preserveStartEnd" />
          <YAxis {...axisStyle} width={40} />
          <Tooltip content={<ChartTooltip formatter={v => v?.toFixed(3)} />} />
          <ReferenceLine y={0} stroke="rgba(255,255,255,0.08)" />

          {/* Confidence band */}
          <Area
            type="monotone" dataKey="upper"
            stroke="none" fill={color + '20'}
            activeDot={false} legendType="none"
          />
          <Area
            type="monotone" dataKey="lower"
            stroke="none" fill="var(--bg-surface)"
            activeDot={false} legendType="none"
          />

          {/* Historical line */}
          <Line
            type="monotone" dataKey="value" name={SIGNAL_LABELS[activeSig]}
            stroke={color} strokeWidth={2}
            dot={false} activeDot={{ r: 4, strokeWidth: 0 }}
          />

          {/* Forecast line (dashed) */}
          <Line
            type="monotone" dataKey="forecast" name="Forecast"
            stroke={color} strokeWidth={2} strokeDasharray="5 4"
            dot={false} activeDot={{ r: 4, strokeWidth: 0 }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}


/* ═══════════════════════════════════════════════════════
   SHAP Waterfall
   Horizontal bar chart showing feature attribution
══════════════════════════════════════════════════════ */
export function ShapWaterfall({ values }) {
  if (!values?.length) {
    return (
      <div style={{
        padding: '40px 24px', textAlign: 'center',
        color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: 12,
      }}>
        <div style={{ marginBottom: 8 }}>⚙️ SHAP values not available</div>
        <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
          Run Phase 4 to generate model & SHAP values:<br/>
          <code style={{ background: 'var(--bg-elevated)', padding: '4px 8px', borderRadius: 4, display: 'inline-block', marginTop: 8 }}>
            python phase4_modeling/train_models.py
          </code>
        </div>
      </div>
    )
  }

  const maxAbs = Math.max(...values.map(v => Math.abs(v.value)), 0.001)

  const formatFeature = (f) =>
    (SIGNAL_LABELS[f] || f)
      .replace(/_/g, ' ')
      .replace(/\b\w/g, c => c.toUpperCase())

  return (
    <div>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: 10,
        color: 'var(--text-muted)', marginBottom: 16,
        display: 'flex', gap: 20,
      }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
          <span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: 2, background: '#FF3B3B60' }} />
          Increases distress risk
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
          <span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: 2, background: '#22C55E60' }} />
          Reduces distress risk
        </span>
      </div>

      {values.map((item, i) => {
        const pct  = (Math.abs(item.value) / maxAbs) * 100
        const pos  = item.value > 0
        const color = pos ? '#FF3B3B' : '#22C55E'

        return (
          <div key={i} className="shap-row" style={{
            animation: `fadeUp 0.3s ease both`,
            animationDelay: `${i * 30}ms`,
          }}>
            <div className="shap-label" title={item.feature}>
              {formatFeature(item.feature)}
            </div>
            <div className="shap-bar-container">
              {/* Zero line */}
              <div style={{
                position: 'absolute', left: '50%', top: 0, bottom: 0,
                width: 1, background: 'var(--border-bright)',
              }} />
              {/* Bar — extends left or right from center */}
              <div style={{
                position: 'absolute',
                top: '15%', height: '70%',
                borderRadius: 3,
                background: color + 'CC',
                width: `${pct / 2}%`,
                ...(pos
                  ? { left: '50%' }
                  : { right: `${50}%`, left: `${50 - pct / 2}%` }
                ),
                transition: 'width 0.6s cubic-bezier(0.4,0,0.2,1)',
              }} />
            </div>
            <div className="shap-val" style={{ color }}>
              {pos ? '+' : ''}{item.value.toFixed(3)}
            </div>
          </div>
        )
      })}
    </div>
  )
}


/* ═══════════════════════════════════════════════════════
   Risk Distribution Donut (Dashboard)
══════════════════════════════════════════════════════ */
const DONUT_COLORS = {
  CRITICAL: '#FF3B3B',
  HIGH:     '#FF6B35',
  MEDIUM:   '#F5C518',
  LOW:      '#22C55E',
}

const CustomDonutLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, value, name }) => {
  if (value === 0) return null
  const RADIAN = Math.PI / 180
  const r  = innerRadius + (outerRadius - innerRadius) * 0.5
  const x  = cx + r * Math.cos(-midAngle * RADIAN)
  const y  = cy + r * Math.sin(-midAngle * RADIAN)
  return (
    <text x={x} y={y} textAnchor="middle" dominantBaseline="central"
      style={{ fontFamily: 'DM Mono, monospace', fontSize: 11, fill: 'rgba(255,255,255,0.7)' }}
    >
      {value}
    </text>
  )
}

export function RiskDistributionChart({ data }) {
  const chartData = Object.entries(data)
    .filter(([, v]) => v > 0)
    .map(([tier, count]) => ({ name: tier, value: count, color: DONUT_COLORS[tier] }))

  if (!chartData.length) return null

  return (
    <ResponsiveContainer width="100%" height="100%">
      <PieChart>
        <Pie
          data={chartData}
          cx="50%" cy="55%"
          innerRadius={52}
          outerRadius={80}
          paddingAngle={3}
          dataKey="value"
          labelLine={false}
          label={CustomDonutLabel}
        >
          {chartData.map((entry, index) => (
            <Cell key={index} fill={entry.color + 'CC'} stroke={entry.color} strokeWidth={1} />
          ))}
        </Pie>
        <Tooltip
          content={({ active, payload }) => {
            if (!active || !payload?.length) return null
            const { name, value } = payload[0].payload
            return (
              <div style={{
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border-bright)',
                borderRadius: 8, padding: '8px 12px',
                fontFamily: 'DM Mono, monospace', fontSize: 12,
              }}>
                <span className={`tier-badge tier-${name}`}>{name}</span>
                <div style={{ marginTop: 6, color: 'var(--text-primary)' }}>
                  {value} suppliers
                </div>
              </div>
            )
          }}
        />
        <Legend
          iconType="circle"
          iconSize={8}
          formatter={(value) => (
            <span style={{
              fontFamily: 'DM Mono, monospace',
              fontSize: 11, color: 'var(--text-secondary)',
            }}>{value}</span>
          )}
        />
      </PieChart>
    </ResponsiveContainer>
  )
}
