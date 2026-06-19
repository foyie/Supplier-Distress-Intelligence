import { Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import Sidebar from './components/Sidebar'
import Dashboard from './pages/Dashboard'
import CompanyDetail from './pages/CompanyDetail'

export default function App() {
  return (
    <div className="app-shell">
      <Navbar />
      <div className="page-body">
        <Sidebar />
        <main className="main-area">
          <Routes>
            <Route path="/"            element={<Dashboard />} />
            <Route path="/company/:id" element={<CompanyDetail />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}
