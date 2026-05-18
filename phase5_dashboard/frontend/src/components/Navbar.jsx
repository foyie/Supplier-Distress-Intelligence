import { Link, useLocation } from 'react-router-dom'
import { Activity, ChevronLeft } from 'lucide-react'

export default function Navbar() {
  const { pathname } = useLocation()
  const isDetail = pathname.startsWith('/company/')

  return (
    <nav style={{
      position: 'fixed', top: 0, left: 0, right: 0, zIndex: 100,
      height: 'var(--nav-h)',
      background: 'rgba(8,10,12,0.92)',
      backdropFilter: 'blur(12px)',
      borderBottom: '1px solid var(--border)',
      display: 'flex', alignItems: 'center',
      padding: '0 32px',
      justifyContent: 'space-between',
    }}>
      {/* Left */}
      <div className="flex items-center gap-12">
        {isDetail ? (
          <Link to="/" className="flex items-center gap-8 btn btn-ghost" style={{ padding: '6px 12px' }}>
            <ChevronLeft size={14} />
            <span className="text-sm">All Suppliers</span>
          </Link>
        ) : (
          <Link to="/" className="flex items-center gap-8" style={{ textDecoration: 'none' }}>
            <div style={{
              width: 28, height: 28, borderRadius: 7,
              background: 'var(--amber)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <Activity size={14} color="#0D1015" strokeWidth={2.5} />
            </div>
            <span style={{
              fontFamily: 'var(--font-display)',
              fontWeight: 700,
              fontSize: 16,
              letterSpacing: '-0.3px',
              color: 'var(--text-primary)',
            }}>
              SupplierWatch
            </span>
          </Link>
        )}
      </div>

      {/* Right */}
      <div className="flex items-center gap-8">
        <div style={{
          display: 'flex', alignItems: 'center', gap: 6,
          fontFamily: 'var(--font-mono)', fontSize: 11,
          color: 'var(--text-muted)',
        }}>
          <span style={{
            width: 6, height: 6, borderRadius: '50%',
            background: 'var(--green-low)',
            animation: 'pulse-amber 2s infinite',
            display: 'inline-block',
          }} />
          LIVE
        </div>
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: 11,
          color: 'var(--text-muted)',
          padding: '4px 10px',
          background: 'var(--bg-surface)',
          border: '1px solid var(--border)',
          borderRadius: 6,
        }}>
          ML MODEL v1.0
        </div>
      </div>
    </nav>
  )
}
