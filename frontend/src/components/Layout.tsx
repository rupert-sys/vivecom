import { Link, Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { inicioDe, puedeVer, seccionesDe } from '../permisos'

export function Layout() {
  const { user, logout } = useAuth()
  const { pathname } = useLocation()
  const secciones = seccionesDe(user?.rol)
  const inicio = inicioDe(user?.rol)

  // Una dirección escrita a mano (o un marcador viejo) de una sección que no es de su rol lo devuelve a su inicio.
  if (user && inicio && !puedeVer(user.rol, pathname)) return <Navigate to={inicio} replace />

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
            <Link to={inicio ?? '/'} style={{ textDecoration: 'none', color: 'var(--ink)' }}>
              Vivecom — Panel Admin
            </Link>
          </h1>
          <nav style={{ display: 'flex', gap: 'var(--space-3)', flexWrap: 'wrap' }}>
            {secciones.map((seccion) => (
              <Link key={seccion.ruta} to={seccion.ruta}>
                {seccion.etiqueta}
              </Link>
            ))}
          </nav>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
          {user && <span className="mono" style={{ color: 'var(--ink-soft)' }}>{user.rol}</span>}
          <button onClick={logout}>Cerrar sesión</button>
        </div>
      </header>
      <main style={{ padding: 'var(--space-4)', maxWidth: 960, margin: '0 auto' }}>
        {secciones.length === 0 ? (
          <p>
            Tu cuenta ({user?.rol}) no tiene secciones en el panel de administración. Usa la app de Vivecom.
          </p>
        ) : (
          <Outlet />
        )}
      </main>
    </div>
  )
}
