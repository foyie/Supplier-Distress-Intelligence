import { Link, useLocation } from 'react-router-dom'
import { Activity, ChevronLeft, Zap } from 'lucide-react'

export default function Navbar() {
  const { pathname } = useLocation()
  const isDetail = pathname.startsWith('/company/')

  return (
    <nav style={{
      position: 'fixed', top: 0, left: 0, right: 0, zIndex: 100,
      height: 'var(--nav-h)',
      background: 'rgba(6,10,15,0.95)',
      backdropFilter: 'blur(16px)',
      borderBottom: '1px solid var(--line)',
      display: 'flex', alignItems: 'center',
      padding: '0 24px',
      justifyContent: 'space-between',
    }}>
      {/* Left */}
      <div className="flex items-c gap-16">
        {isDetail ? (
          <Link to="/" style={{
            display: 'flex', alignItems: 'center', gap: 6,
            textDecoration: 'none', color: 'var(--t2)',
            fontFamily: 'var(--f-body)', fontSize: 12,
            padding: '5px 10px',
            border: '1px solid var(--line-bright)',
            borderRadius: 6,
            transition: 'all 0.12s',
          }}
          onMouseEnter={e => { e.currentTarget.style.color = 'var(--t1)'; e.currentTarget.style.background = 'var(--hover)'; }}
          onMouseLeave={e => { e.currentTarget.style.color = 'var(--t2)'; e.currentTarget.style.background = 'transparent'; }}
          >
            <ChevronLeft size={12} /> All Suppliers
          </Link>
        ) : (
          <Link to="/" style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 10 }}>
            {/* Logo mark */}
            <div style={{
              width: 30, height: 30,
              background: 'var(--cyan)',
              borderRadius: 8,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              boxShadow: '0 0 12px rgba(0,212,255,0.35)',
            }}>
              <Activity size={14} color="var(--base)" strokeWidth={2.5} />
            </div>
            <div>
              <div style={{
                fontFamily: 'var(--f-display)',
                fontWeight: 700,
                fontSize: 15,
                letterSpacing: '-0.3px',
                color: 'var(--t1)',
                lineHeight: 1,
              }}>
                SupplierWatch
              </div>
              <div style={{
                fontFamily: 'var(--f-mono)',
                fontSize: 9,
                letterSpacing: '0.12em',
                color: 'var(--t3)',
                textTransform: 'uppercase',
                lineHeight: 1,
                marginTop: 2,
              }}>
                Risk Intelligence
              </div>
            </div>
          </Link>
        )}
      </div>

      {/* Right */}
      <div className="flex items-c gap-12">
        {/* Live indicator */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 6,
          fontFamily: 'var(--f-mono)', fontSize: 10,
          letterSpacing: '0.1em',
          color: 'var(--t3)',
        }}>
          <span style={{
            width: 5, height: 5, borderRadius: '50%',
            background: 'var(--green)',
            animation: 'pulseGlow 2.5s infinite',
            display: 'inline-block',
          }} />
          LIVE
        </div>

        <div style={{ width: 1, height: 16, background: 'var(--line)' }} />

        <div style={{
          fontFamily: 'var(--f-mono)', fontSize: 10,
          color: 'var(--t3)',
          letterSpacing: '0.08em',
        }}>
          MODEL v1.0
        </div>

        <div style={{ width: 1, height: 16, background: 'var(--line)' }} />

        <div style={{
          display: 'flex', alignItems: 'center', gap: 5,
          fontFamily: 'var(--f-mono)', fontSize: 10,
          color: 'var(--cyan)',
        }}>
          <Zap size={10} />
          XGB + Cox PH
        </div>
      </div>
    </nav>
  )
}
