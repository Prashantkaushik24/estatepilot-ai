import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './lib/auth'
import Layout from './components/Layout'
import { SkeletonRows } from './components/ui'
import Login from './pages/Login'
import Overview from './pages/Overview'
import Inbox from './pages/Inbox'
import Leads from './pages/Leads'
import Properties from './pages/Properties'
import Matching from './pages/Matching'
import Followups from './pages/Followups'
import Automation from './pages/Automation'
import Activity from './pages/Activity'
import Analytics from './pages/Analytics'
import SettingsPage from './pages/Settings'

export default function App() {
  const { user, loading } = useAuth()
  if (loading) return <div className="p-10"><SkeletonRows /></div>
  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/" replace /> : <Login />} />
      <Route element={user ? <Layout /> : <Navigate to="/login" replace />}>
        <Route path="/" element={<Overview />} />
        <Route path="/inbox" element={<Inbox />} />
        <Route path="/leads" element={<Leads />} />
        <Route path="/properties" element={<Properties />} />
        <Route path="/matching" element={<Matching />} />
        <Route path="/followups" element={<Followups />} />
        <Route path="/automation" element={<Automation />} />
        <Route path="/activity" element={<Activity />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
