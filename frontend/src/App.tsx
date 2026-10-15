import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import Landing from './pages/Landing'
import Dashboard from './pages/Dashboard'
import Transactions from './pages/Transactions'
import TransactionDetail from './pages/TransactionDetail'
import Import from './pages/Import'
import Recovery from './pages/Recovery'
import Evaluation from './pages/Evaluation'
import AuditTrail from './pages/AuditTrail'
import PolicyConfig from './pages/PolicyConfig'
import Settings from './pages/Settings'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public landing page */}
        <Route path="/" element={<Landing />} />

        {/* App shell */}
        <Route element={<Layout />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/transactions" element={<Transactions />} />
          <Route path="/transactions/:id" element={<TransactionDetail />} />
          <Route path="/import" element={<Import />} />
          <Route path="/recovery" element={<Recovery />} />
          <Route path="/evaluation" element={<Evaluation />} />
          <Route path="/audit" element={<AuditTrail />} />
          <Route path="/policy" element={<PolicyConfig />} />
          <Route path="/settings" element={<Settings />} />
          {/* Catch-all */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
