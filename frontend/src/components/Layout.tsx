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

// Solo para la barra inferior de celular (ver .bottom-tabs en index.css) — una app real se distingue de una
// página web sobre todo por esto: navegación fija abajo con ícono, no un menú escondido nada más.
const ICONO_DE_SECCION: Record<string, string> = {
  '/dashboard': '📊',
  '/properties': '🏠',
  '/users': '👥',
  '/organizacion': '🏛️',
  '/fees': '💰',
  '/collection': '📥',
  '/payment-proofs': '🧾',
  '/payment-agreements': '🤝',
  '/clabe': '🏦',
  '/expenses': '💸',
  '/reports/export': '📤',
  '/amenities': '🏊',
  '/packages': '📦',
  '/reservations': '📅',
  '/security': '🛡️',
  '/announcements': '📢',
  '/announcement-questions': '❓',
  '/reglamento': '📜',
}
const CANTIDAD_TABS_ABAJO = 4

export function Layout() {
  const { user, logout } = useAuth()
  const { pathname } = useLocation()
  const secciones = seccionesDe(user?.rol)
  const inicio = inicioDe(user?.rol)

  const [nombreCondominio, setNombreCondominio] = useState('Vivecom')
  const [logoUrl, setLogoUrl] = useState<string | null>(null)
  // Menú lateral en celular: por default fuera de pantalla (ver .sidebar/.sidebar--open en index.css — este
  // componente nunca tuvo tratamiento para pantallas angostas, todo era el layout de escritorio fijo).
  const [menuAbierto, setMenuAbierto] = useState(false)

  // Cambiar de sección cierra el menú solo — sin esto, en celular se queda abierto tapando la página nueva.
  useEffect(() => {
    setMenuAbierto(false)
  }, [pathname])

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

  const tabsAbajo = secciones.slice(0, CANTIDAD_TABS_ABAJO)

  return (
    <div>
      {/* Fuera del contenedor de abajo a propósito: ese es un flex ROW (sidebar + contenido lado a lado) —
          meterla ahí adentro la vuelve un flex item más y hereda align-items:stretch (la altura de TODA la
          fila, no una franja delgada arriba). Bug real: encontrado en vivo en producción, 2026-09-29. */}
      <header className="mobile-topbar">
        <span style={{ fontFamily: 'var(--font-heading)', fontWeight: 600 }}>{nombreCondominio}</span>
      </header>

      {menuAbierto && <div className="sidebar-backdrop" onClick={() => setMenuAbierto(false)} />}

      {/* Barra inferior fija (solo celular, ver .bottom-tabs en index.css): las primeras secciones del rol,
          más "Más" para las demás — esto, más que cualquier detalle de color, es lo que hace que algo se
          sienta "app" y no "página web abierta en el celular". */}
      <nav className="bottom-tabs" aria-label="Navegación principal">
        {tabsAbajo.map((seccion) => (
          <NavLink
            key={seccion.ruta}
            to={seccion.ruta}
            className={({ isActive }) => `bottom-tab${isActive ? ' bottom-tab--active' : ''}`}
          >
            <span className="bottom-tab-icono" aria-hidden="true">{ICONO_DE_SECCION[seccion.ruta] ?? '•'}</span>
            <span className="bottom-tab-etiqueta">{seccion.etiqueta}</span>
          </NavLink>
        ))}
        {/* Siempre presente, aunque el rol tenga pocas secciones (ej. guardia, una sola): es también la
            única forma de llegar a "Cerrar sesión" en celular, así que nunca debe faltar. */}
        <button
          type="button"
          className={`bottom-tab${menuAbierto ? ' bottom-tab--active' : ''}`}
          onClick={() => setMenuAbierto((v) => !v)}
          aria-expanded={menuAbierto}
        >
          <span className="bottom-tab-icono" aria-hidden="true">⋯</span>
          <span className="bottom-tab-etiqueta">Más</span>
        </button>
      </nav>

      <div style={{ display: 'flex', minHeight: '100vh' }}>
        <aside
          className={`sidebar${menuAbierto ? ' sidebar--open' : ''}`}
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

        <div className="app-content" style={{ flex: 1, minWidth: 0 }}>
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
    </div>
  )
}
