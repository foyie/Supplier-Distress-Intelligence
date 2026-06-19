import { useApi } from '../hooks/useApi'
import { api } from '../utils/api'
import { RiskIndicator } from './UI'
import { AlertTriangle, Activity, Database, TrendingUp } from 'lucide-react'

const TIER_META = [
  { tier: 'CRITICAL', icon: AlertTriangle, color: 'var(--red)' },
  { tier: 'HIGH',     icon: TrendingUp,   color: 'var(--orange)' },
  { tier: 'MEDIUM',   icon: Activity,     color: 'var(--yellow)' },
  { tier: 'LOW',      icon: Database,     color: 'var(--green)' },
]

export default function Sidebar() {
  const { data: stats } = useApi(() => api.stats())
  const dist = stats?.risk_distribution || {}
  const total = stats?.total_companies || 0

  return (
    <aside className="sidebar">
      <div style={{ padding: '20px 16px' }}>

        {/* Portfolio summary */}
        <div className="eyebrow mb-12" style={{ paddingLeft: 2 }}>Portfolio</div>

        <div style={{
          fontFamily: 'var(--f-display)',
          fontSize: 34,
          fontWeight: 700,
          color: 'var(--t1)',
          letterSpacing: '-1px',
          lineHeight: 1,
        }}>
          {total || '—'}
        </div>
        <div style={{ fontFamily: 'var(--f-mono)', fontSize: 10, color: 'var(--t3)', marginTop: 4 }}>
          SUPPLIERS TRACKED
        </div>

        <div className="hr mt-16 mb-16" />

        {/* Risk breakdown */}
        <div className="eyebrow mb-12" style={{ paddingLeft: 2 }}>Risk Breakdown</div>

        {TIER_META.map(({ tier, color }) => {
          const count = dist[tier] || 0
          const pct = total ? (count / total) * 100 : 0
          return (
            <div key={tier} style={{ marginBottom: 12 }}>
              <div style={{
                display: 'flex', alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: 5,
              }}>
                <RiskIndicator tier={tier} />
                <span style={{
                  fontFamily: 'var(--f-mono)', fontSize: 11,
                  color: 'var(--t2)',
                }}>
                  {count}
                </span>
              </div>
              {/* Track bar */}
              <div style={{
                height: 3, background: 'var(--raised)',
                borderRadius: 2, overflow: 'hidden',
              }}>
                <div style={{
                  height: '100%',
                  width: `${pct}%`,
                  background: color,
                  borderRadius: 2,
                  transition: 'width 1s cubic-bezier(0.4,0,0.2,1)',
                  boxShadow: `0 0 6px ${color}88`,
                }} />
              </div>
            </div>
          )
        })}

        <div className="hr mt-16 mb-16" />

        {/* Model stats */}
        <div className="eyebrow mb-12" style={{ paddingLeft: 2 }}>Model</div>

        {[
          { label: 'XGB AUC',   value: stats?.model_auc ? (stats.model_auc * 100).toFixed(1) + '%' : '—' },
          { label: 'Horizon',   value: '6 months' },
          { label: 'Updated',   value: stats?.last_updated || '—' },
        ].map(({ label, value }) => (
          <div key={label} style={{
            display: 'flex', justifyContent: 'space-between',
            marginBottom: 10,
          }}>
            <span style={{ fontFamily: 'var(--f-mono)', fontSize: 10, color: 'var(--t3)', letterSpacing: '0.08em' }}>
              {label}
            </span>
            <span style={{ fontFamily: 'var(--f-mono)', fontSize: 11, color: 'var(--t2)' }}>
              {value}
            </span>
          </div>
        ))}

        <div className="hr mt-16 mb-16" />

        {/* Signals legend */}
        <div className="eyebrow mb-10" style={{ paddingLeft: 2 }}>Signal Sources</div>
        {['SEC EDGAR', 'GDELT News', 'LinkedIn', 'Glassdoor'].map(s => (
          <div key={s} style={{
            display: 'flex', alignItems: 'center', gap: 7,
            marginBottom: 8,
          }}>
            <div style={{ width: 4, height: 4, borderRadius: '50%', background: 'var(--cyan)', opacity: 0.5 }} />
            <span style={{ fontFamily: 'var(--f-mono)', fontSize: 10, color: 'var(--t3)' }}>{s}</span>
          </div>
        ))}
        <div className="hr mt-16 mb-16" />

        {/* Author card */}
        <div style={{ paddingLeft: 2 }}>
          <div className="eyebrow mb-10">Built by</div>

          <div style={{
            fontFamily: 'var(--f-display)',
            fontSize: 13,
            fontWeight: 600,
            color: 'var(--t1)',
            marginBottom: 2,
          }}>
            Chandrima Das
          </div>

          <div style={{
            fontFamily: 'var(--f-mono)',
            fontSize: 9,
            color: 'var(--t3)',
            letterSpacing: '0.04em',
            marginBottom: 12,
          }}>
            MS Data Science · UCSD
          </div>

          {/* Links */}
          {[
            { label: 'chdas@ucsd.edu',        href: 'mailto:chdas@ucsd.edu' },
            { label: 'linkedin/foyie',         href: 'https://linkedin.com/in/foyie/' },
            { label: 'github/foyie',           href: 'https://github.com/foyie' },
            { label: 'website', href: 'https://foyie.github.io/foyie' },
          ].map(({ label, href }) => (
            <a
              key={label}
              href={href}
              target="_blank"
              rel="noreferrer"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                marginBottom: 6,
                textDecoration: 'none',
                fontFamily: 'var(--f-mono)',
                fontSize: 9,
                color: 'var(--t3)',
                letterSpacing: '0.04em',
                transition: 'color 0.12s',
              }}
              onMouseEnter={e => e.currentTarget.style.color = 'var(--cyan)'}
              onMouseLeave={e => e.currentTarget.style.color = 'var(--t3)'}
            >
              <span style={{
                width: 3, height: 3, borderRadius: '50%',
                background: 'var(--cyan)', opacity: 0.4, flexShrink: 0,
              }} />
              {label}
            </a>
          ))}
        </div>

      </div>
    </aside>
  )
}
