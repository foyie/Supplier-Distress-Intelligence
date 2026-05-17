import { Routes, Route } from 'react-router-dom'
import Layout        from './components/Layout'
import Dashboard     from './pages/Dashboard'
import CompanyDetail from './pages/CompanyDetail'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index         element={<Dashboard />} />
        <Route path="company/:id" element={<CompanyDetail />} />
      </Route>
    </Routes>
  )
}
