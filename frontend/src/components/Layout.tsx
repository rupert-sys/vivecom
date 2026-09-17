import { Link, Outlet } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

export function Layout() {
  const { user, logout } = useAuth()

  return (
    <div>
      <header
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: 'var(--space-3) var(--space-4)',
          background: 'var(--surface)',
          borderBottom: '1px solid var(--border)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)' }}>
          <h1 style={{ fontSize: '1.25rem' }}>
            <Link to="/properties" style={{ textDecoration: 'none', color: 'var(--ink)' }}>
              Vivecom — Panel Admin
            </Link>
          </h1>
          <nav style={{ display: 'flex', gap: 'var(--space-3)' }}>
            <Link to="/properties">Viviendas</Link>
            <Link to="/fees">Cuotas</Link>
            <Link to="/clabe">CLABE</Link>
            <Link to="/dashboard">Dashboard</Link>
          </nav>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
          {user && <span className="mono" style={{ color: 'var(--ink-soft)' }}>{user.rol}</span>}
          <button onClick={logout}>Cerrar sesión</button>
        </div>
      </header>
      <main style={{ padding: 'var(--space-4)', maxWidth: 960, margin: '0 auto' }}>
        <Outlet />
      </main>
    </div>
  )
}
