import { Outlet, Link, useLocation } from 'react-router-dom'
import { Activity } from 'lucide-react'

export default function Layout() {
  const { pathname } = useLocation()

  return (
    <div className="min-h-screen flex flex-col">
      {/* Nav */}
      <header className="border-b border-mist bg-white sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5 group">
            <div className="w-7 h-7 bg-ink rounded-md flex items-center justify-center">
              <Activity size={14} className="text-paper" />
            </div>
            <span className="font-display text-lg leading-none">
              Supplier<span className="text-accent">Intel</span>
            </span>
          </Link>

          <nav className="flex items-center gap-6">
            <Link to="/" className={`nav-link ${pathname === '/' ? 'active' : ''}`}>
              Dashboard
            </Link>
            <a
              href="http://localhost:5000"
              target="_blank"
              rel="noreferrer"
              className="nav-link"
            >
              MLflow ↗
            </a>
          </nav>
        </div>
      </header>

      {/* Page */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-6 py-8">
        <Outlet />
      </main>

      <footer className="border-t border-mist py-4 text-center text-xs text-ash font-mono">
        Supplier Distress Intelligence · Model: XGBoost + Cox PH · Signals: SEC · GDELT · LinkedIn
      </footer>
    </div>
  )
}
