import { useEffect, useState } from 'react'
import { getCollectionsSummary } from '../api/reports'
import { listProperties } from '../api/properties'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import type { CollectionsSummary, Property } from '../types'

const ROLES_CON_ACCESO = new Set(['admin', 'tesorero'])

export function DashboardPage() {
  const { user } = useAuth()
  const tieneAcceso = user !== null && ROLES_CON_ACCESO.has(user.rol)

  const [properties, setProperties] = useState<Property[]>([])
  const [summary, setSummary] = useState<CollectionsSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [propertyId, setPropertyId] = useState('')
  const [mes, setMes] = useState('')

  async function reload() {
    setLoading(true)
    try {
      const [propertiesResult, summaryResult] = await Promise.all([
        listProperties(),
        getCollectionsSummary({ periodo: mes ? `${mes}-01` : undefined, propertyId: propertyId || undefined }),
      ])
      setProperties(propertiesResult)
      setSummary(summaryResult)
      setError(null)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo cargar el dashboard financiero.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (tieneAcceso) reload()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tieneAcceso, propertyId, mes])

  if (!tieneAcceso) {
    return (
      <div>
        <h2>Dashboard financiero</h2>
        <p>No tienes acceso a esta vista — solo administradores y tesorero.</p>
      </div>
    )
  }

  return (
    <div>
      <h2>Dashboard financiero</h2>
      {error && <p style={{ color: 'var(--brick)' }}>{error}</p>}

      <div style={{ display: 'flex', gap: 'var(--space-2)', margin: 'var(--space-3) 0' }}>
        <select value={propertyId} onChange={(e) => setPropertyId(e.target.value)}>
          <option value="">Todas las viviendas</option>
          {properties.map((p) => (
            <option key={p.id} value={p.id}>
              {p.identificador}
            </option>
          ))}
        </select>
        <input type="month" aria-label="Periodo" value={mes} onChange={(e) => setMes(e.target.value)} />
      </div>

      {loading ? (
        <p>Cargando…</p>
      ) : (
        summary && (
          <>
            <div style={{ display: 'flex', gap: 'var(--space-3)', marginBottom: 'var(--space-4)' }}>
              <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: 'var(--space-3)', flex: 1 }}>
                <div style={{ color: 'var(--ink-soft)' }}>Cobrado</div>
                <div className="mono" style={{ color: 'var(--teal)', fontSize: '1.5rem' }}>
                  ${summary.cobrado_total.toFixed(2)}
                </div>
              </div>
              <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: 'var(--space-3)', flex: 1 }}>
                <div style={{ color: 'var(--ink-soft)' }}>Pendiente</div>
                <div className="mono" style={{ color: 'var(--amber)', fontSize: '1.5rem' }}>
                  ${summary.pendiente_total.toFixed(2)}
                </div>
              </div>
            </div>

            {summary.por_vivienda.length === 0 ? (
              <p>No hay cargos que mostrar con estos filtros.</p>
            ) : (
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
                    <th>Vivienda</th>
                    <th>Cobrado</th>
                    <th>Pendiente</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.por_vivienda.map((fila) => (
                    <tr key={fila.property_id} style={{ borderBottom: '1px solid var(--border)' }}>
                      <td>{fila.identificador}</td>
                      <td className="mono" style={{ color: 'var(--teal)' }}>
                        ${fila.cobrado.toFixed(2)}
                      </td>
                      <td className="mono" style={{ color: 'var(--amber)' }}>
                        ${fila.pendiente.toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </>
        )
      )}
    </div>
  )
}
