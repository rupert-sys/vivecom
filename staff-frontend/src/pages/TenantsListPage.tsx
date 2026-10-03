import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { listarTenants, type TenantListItem } from '../api/tenants'
import { ApiError } from '../api/client'

export function TenantsListPage() {
  const [tenants, setTenants] = useState<TenantListItem[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busqueda, setBusqueda] = useState('')

  useEffect(() => {
    listarTenants()
      .then(setTenants)
      .catch((err) => setError(err instanceof ApiError ? err.message : 'No se pudo cargar la lista de condominios.'))
  }, [])

  const filtrados = useMemo(() => {
    if (!tenants) return []
    const q = busqueda.trim().toLowerCase()
    if (!q) return tenants
    return tenants.filter((t) => t.nombre.toLowerCase().includes(q))
  }, [tenants, busqueda])

  const totalViviendas = useMemo(() => filtrados.reduce((acc, t) => acc + t.viviendas, 0), [filtrados])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <div>
          <h2>Condominios</h2>
          <p style={{ margin: 0, color: 'var(--ink-soft)' }}>
            {tenants ? `${filtrados.length} condominio(s) · ${totalViviendas} vivienda(s)` : 'Cargando…'}
          </p>
        </div>
        <Link to="/nuevo" className="btn-primary" style={{ textDecoration: 'none', padding: '9px 16px', borderRadius: 'var(--radius-sm)' }}>
          + Nuevo condominio
        </Link>
      </div>

      {error && <p style={{ color: 'var(--brick)' }}>{error}</p>}

      {tenants && (
        <>
          <input
            type="search"
            placeholder="Buscar condominio…"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            style={{ maxWidth: 320 }}
          />

          <table className="card" style={{ width: '100%' }}>
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Viviendas</th>
                <th>Cuota del condominio</th>
                <th>Alta</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {filtrados.map((t) => (
                <tr key={t.tenant_id}>
                  <td>
                    <Link to={`/${t.tenant_id}`}>{t.nombre}</Link>
                  </td>
                  <td className="mono">{t.viviendas}</td>
                  <td className="mono">${(t.precio_por_vivienda * t.viviendas).toFixed(2)}</td>
                  <td className="mono">{new Date(t.fecha_creacion).toLocaleDateString('es-MX')}</td>
                  <td>
                    <span className={t.activo ? 'chip chip-teal' : 'chip chip-brick'}>
                      {t.activo ? 'Activo' : 'Suspendido'}
                    </span>
                  </td>
                </tr>
              ))}
              {filtrados.length === 0 && (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', color: 'var(--ink-faint)' }}>
                    Ningún condominio coincide con la búsqueda.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </>
      )}
    </div>
  )
}
