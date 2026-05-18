import { Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import Dashboard from './pages/Dashboard'
import CompanyDetail from './pages/CompanyDetail'

export default function App() {
  return (
    <div className="app-shell">
      <Navbar />
      <main className="main-content">
        <Routes>
          <Route path="/"           element={<Dashboard />} />
          <Route path="/company/:id" element={<CompanyDetail />} />
        </Routes>
      </main>
    </div>
  )
}
