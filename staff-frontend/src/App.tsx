import { Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { LoginPage } from './pages/LoginPage'
import { TenantsListPage } from './pages/TenantsListPage'
import { TenantDetailPage } from './pages/TenantDetailPage'
import { TenantCreatePage } from './pages/TenantCreatePage'
import { TenantTrashPage } from './pages/TenantTrashPage'
import { RequireAuth } from './auth/RequireAuth'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route path="/" element={<TenantsListPage />} />
        <Route path="/nuevo" element={<TenantCreatePage />} />
        <Route path="/papelera" element={<TenantTrashPage />} />
        <Route path="/:tenantId" element={<TenantDetailPage />} />
      </Route>
    </Routes>
  )
}
