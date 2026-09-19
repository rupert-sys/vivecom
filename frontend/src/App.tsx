import { Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { LoginPage } from './pages/LoginPage'
import { SignupPage } from './pages/SignupPage'
import { PropertiesPage } from './pages/PropertiesPage'
import { PropertyDetailPage } from './pages/PropertyDetailPage'
import { FeesPage } from './pages/FeesPage'
import { ClabePage } from './pages/ClabePage'
import { DashboardPage } from './pages/DashboardPage'
import { ExpensesBudgetPage } from './pages/ExpensesBudgetPage'
import { ReportsExportPage } from './pages/ReportsExportPage'
import { AmenitiesPollsPage } from './pages/AmenitiesPollsPage'
import { SecurityDashboardPage } from './pages/SecurityDashboardPage'
import { AnnouncementsPage } from './pages/AnnouncementsPage'
import { CollectionStatusPage } from './pages/CollectionStatusPage'
import { ReservationsPage } from './pages/ReservationsPage'
import { ReglamentoPage } from './pages/ReglamentoPage'
import { PaymentProofsPage } from './pages/PaymentProofsPage'
import { RequireAuth } from './auth/RequireAuth'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />
      <Route
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route path="/properties" element={<PropertiesPage />} />
        <Route path="/properties/:propertyId" element={<PropertyDetailPage />} />
        <Route path="/fees" element={<FeesPage />} />
        <Route path="/clabe" element={<ClabePage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/expenses" element={<ExpensesBudgetPage />} />
        <Route path="/reports/export" element={<ReportsExportPage />} />
        <Route path="/amenities" element={<AmenitiesPollsPage />} />
        <Route path="/security" element={<SecurityDashboardPage />} />
        <Route path="/announcements" element={<AnnouncementsPage />} />
        <Route path="/collection" element={<CollectionStatusPage />} />
        <Route path="/payment-proofs" element={<PaymentProofsPage />} />
        <Route path="/reservations" element={<ReservationsPage />} />
        <Route path="/reglamento" element={<ReglamentoPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/properties" replace />} />
    </Routes>
  )
}
