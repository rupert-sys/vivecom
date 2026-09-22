import { useEffect, useState } from 'react'
import { Navigate, NavLink, Outlet, useLocation } from 'react-router-dom'
import { fetchLogoObjectUrl, getTenantConfig } from '../api/tenant'
import { useAuth } from '../auth/AuthContext'
import { aplicarFaviconDelDocumento, aplicarTituloDelDocumento, restablecerBrandingDelDocumento } from '../utils/documentBranding'
import { inicioDe, puedeVer, seccionesDe } from '../permisos'

const ETIQUETAS_DE_ROL: Record<string, string> = {
  admin: 'Administrador',
  tesorero: 'Tesorero',
  comite_aprobador: 'Comité (aprueba)',
  comite_lectura: 'Comité (lectura)',
  vocero: 'Vocero',
  guardia: 'Guardia',
  residente: 'Residente',
}

export function Layout() {
  const { user, logout } = useAuth()
  const { pathname } = useLocation()
  const secciones = seccionesDe(user?.rol)
  const inicio = inicioDe(user?.rol)

  const [nombreCondominio, setNombreCondominio] = useState('Vivecom')
  const [logoUrl, setLogoUrl] = useState<string | null>(null)

  useEffect(() => {
    let vigente = true
    let urlCreada: string | null = null
    getTenantConfig()
      .then(async (config) => {
        if (!vigente) return
        setNombreCondominio(config.nombre)
        aplicarTituloDelDocumento(config.nombre)
        if (config.tiene_logo) {
          const url = await fetchLogoObjectUrl()
          if (vigente && url) {
            urlCreada = url
            setLogoUrl(url)
            aplicarFaviconDelDocumento(url)
          }
        }
      })
      .catch(() => {
        /* El encabezado se ve bien sin el nombre real del condominio; no hay nada que mostrarle al usuario aquí. */
      })
    // Al salir del panel (logout, o esta pestaña deja de mostrar Layout) la pestaña vuelve a su identidad genérica:
    // que no se quede con el nombre o el logo de un condominio cuya sesión ya terminó.
    return () => {
      vigente = false
      if (urlCreada) URL.revokeObjectURL(urlCreada)
      restablecerBrandingDelDocumento()
    }
  }, [])

  // Una dirección escrita a mano (o un marcador viejo) de una sección que no es de su rol lo devuelve a su inicio.
  if (user && inicio && !puedeVer(user.rol, pathname)) return <Navigate to={inicio} replace />

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
          overflowY: 'auto',
        }}
      >
        <NavLink
          to={inicio ?? '/'}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--space-2)',
            padding: 'var(--space-4) var(--space-3)',
            textDecoration: 'none',
            color: '#fff',
            borderBottom: '1px solid rgba(255,255,255,0.08)',
          }}
        >
          {logoUrl ? (
            <img
              src={logoUrl}
              alt={nombreCondominio}
              style={{ width: 32, height: 32, borderRadius: 'var(--radius-sm)', objectFit: 'cover', flexShrink: 0 }}
            />
          ) : (
            <span
              style={{
                width: 32, height: 32, borderRadius: 'var(--radius-sm)', flexShrink: 0,
                background: 'var(--teal)', display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontFamily: 'var(--font-heading)', fontWeight: 700, fontSize: '0.95rem',
              }}
            >
              {nombreCondominio.trim().charAt(0).toUpperCase() || 'V'}
            </span>
          )}
          <span style={{ fontFamily: 'var(--font-heading)', fontWeight: 600, fontSize: '1.05rem', lineHeight: 1.2 }}>
            {nombreCondominio}
          </span>
        </NavLink>

        <nav aria-label="Secciones del panel" style={{ display: 'flex', flexDirection: 'column', gap: 2, padding: 'var(--space-2)', flex: 1 }}>
          {secciones.map((seccion) => (
            <NavLink
              key={seccion.ruta}
              to={seccion.ruta}
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
              {seccion.etiqueta}
            </NavLink>
          ))}
        </nav>

        <div style={{ padding: 'var(--space-3)', borderTop: '1px solid rgba(255,255,255,0.08)' }}>
          {user && (
            <div style={{ marginBottom: 'var(--space-2)' }}>
              <div style={{ fontSize: '0.8rem', color: '#fff', fontWeight: 600 }}>
                {ETIQUETAS_DE_ROL[user.rol] ?? user.rol}
              </div>
            </div>
          )}
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
          {secciones.length === 0 ? (
            <p>
              Tu cuenta ({user?.rol}) no tiene secciones en el panel de administración. Usa la app de Vivecom.
            </p>
          ) : (
            <Outlet />
          )}
        </main>
      </div>
    </div>
  )
}
