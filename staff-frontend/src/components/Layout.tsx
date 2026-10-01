import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

export function Layout() {
  const { logout } = useAuth()

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <aside
        style={{
          width: 'var(--sidebar-w)',
          flexShrink: 0,
          background: 'var(--ink-2)',
          color: '#cbd5d9',
          display: 'flex',
          flexDirection: 'column',
          position: 'sticky',
          top: 0,
          height: '100vh',
        }}
      >
        <div
          style={{
            padding: 'var(--space-4) var(--space-3)',
            borderBottom: '1px solid rgba(255,255,255,0.08)',
            color: '#fff',
            fontFamily: 'var(--font-heading)',
            fontWeight: 600,
            fontSize: '1.05rem',
          }}
        >
          Vivecom
          <div style={{ fontFamily: 'var(--font-body)', fontWeight: 500, fontSize: '0.78rem', color: '#a9b6bf' }}>
            Administrador principal
          </div>
        </div>

        <nav aria-label="Secciones" style={{ display: 'flex', flexDirection: 'column', gap: 2, padding: 'var(--space-2)', flex: 1 }}>
          <NavLink
            to="/"
            end
            style={({ isActive }) => ({
              padding: '9px var(--space-3)',
              borderRadius: 'var(--radius-sm)',
              textDecoration: 'none',
              fontSize: '0.88rem',
              fontWeight: isActive ? 600 : 500,
              color: isActive ? '#fff' : '#a9b6bf',
              background: isActive ? 'rgba(255,255,255,0.1)' : 'transparent',
            })}
          >
            Condominios
          </NavLink>
          <NavLink
            to="/papelera"
            style={({ isActive }) => ({
              padding: '9px var(--space-3)',
              borderRadius: 'var(--radius-sm)',
              textDecoration: 'none',
              fontSize: '0.88rem',
              fontWeight: isActive ? 600 : 500,
              color: isActive ? '#fff' : '#a9b6bf',
              background: isActive ? 'rgba(255,255,255,0.1)' : 'transparent',
            })}
          >
            Papelera
          </NavLink>
        </nav>

        <div style={{ padding: 'var(--space-3)', borderTop: '1px solid rgba(255,255,255,0.08)' }}>
          <button
            onClick={logout}
            style={{ width: '100%', background: 'transparent', color: '#cbd5d9', borderColor: 'rgba(255,255,255,0.18)' }}
          >
            Cerrar sesión
          </button>
        </div>
      </aside>

      <div style={{ flex: 1, minWidth: 0 }}>
        <main style={{ padding: 'var(--space-5) var(--space-4)', maxWidth: 1080, margin: '0 auto' }}>
          <Outlet />
        </main>
      </div>
    </div>
  )
}
