import { useEffect, useState } from 'react'
import { getCollectionsSummary } from '../api/reports'
import { listProperties } from '../api/properties'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { StatCard } from '../components/StatCard'
import type { CollectionsSummary, Property, PropertyCollectionsSummary } from '../types'
import { rolesDe } from '../permisos'

const ROLES_CON_ACCESO = new Set<string>(rolesDe('/dashboard'))

type Filtro = 'todas' | 'cobrado' | 'pendiente'

const TITULO_DETALLE: Record<Filtro, string> = {
  todas: 'Detalle por vivienda',
  cobrado: 'Quién pagó',
  pendiente: 'Quién debe',
}

function filasDelDetalle(porVivienda: PropertyCollectionsSummary[], filtro: Filtro): PropertyCollectionsSummary[] {
  if (filtro === 'cobrado') return porVivienda.filter((f) => f.cobrado > 0).sort((a, b) => b.cobrado - a.cobrado)
  if (filtro === 'pendiente') return porVivienda.filter((f) => f.pendiente > 0).sort((a, b) => b.pendiente - a.pendiente)
  return porVivienda
}

export function DashboardPage() {
  const { user } = useAuth()
  const tieneAcceso = user !== null && ROLES_CON_ACCESO.has(user.rol)

  const [properties, setProperties] = useState<Property[]>([])
  const [summary, setSummary] = useState<CollectionsSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [propertyId, setPropertyId] = useState('')
  const [mes, setMes] = useState('')
  const [filtro, setFiltro] = useState<Filtro>('todas')

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

  useEffect(() => {
    setFiltro('todas') // un filtro de vivienda/periodo nuevo invalida el "quién pagó/debe" que se estaba viendo
  }, [propertyId, mes])

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
            <div role="group" aria-label="Resumen financiero" style={{ display: 'flex', gap: 'var(--space-3)', marginBottom: 'var(--space-3)' }}>
              <StatCard label="Viviendas" onClick={() => setFiltro('todas')} active={filtro === 'todas'}>
                {properties.length}
              </StatCard>
              <StatCard
                label="Cobrado"
                color="var(--teal)"
                onClick={() => setFiltro('cobrado')}
                active={filtro === 'cobrado'}
              >
                ${summary.cobrado_total.toFixed(2)}
              </StatCard>
              <StatCard
                label="Adeudado"
                color="var(--amber)"
                onClick={() => setFiltro('pendiente')}
                active={filtro === 'pendiente'}
              >
                ${summary.pendiente_total.toFixed(2)}
              </StatCard>
            </div>
            <p style={{ color: 'var(--ink-soft)', marginTop: 0 }}>Pincha una tarjeta para ver el detalle por vivienda.</p>

            <div role="group" aria-label="Cobrado por concepto" style={{ display: 'flex', gap: 'var(--space-3)', marginBottom: 'var(--space-4)' }}>
              {summary.por_origen.map((origen) => (
                <StatCard key={origen.concepto} label={origen.concepto}>
                  ${origen.cobrado.toFixed(2)}
                  {origen.pendiente > 0 && (
                    <span style={{ color: 'var(--amber)', fontSize: '0.85rem', display: 'block' }}>
                      ${origen.pendiente.toFixed(2)} pendiente
                    </span>
                  )}
                </StatCard>
              ))}
            </div>

            <h3>{TITULO_DETALLE[filtro]}</h3>
            {(() => {
              const filas = filasDelDetalle(summary.por_vivienda, filtro)
              if (filas.length === 0) {
                return (
                  <p>
                    {filtro === 'todas'
                      ? 'No hay cargos que mostrar con estos filtros.'
                      : filtro === 'cobrado'
                        ? 'Nadie ha pagado con estos filtros.'
                        : 'Nadie debe con estos filtros.'}
                  </p>
                )
              }
              return (
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
                      <th>Vivienda</th>
                      <th>Cobrado</th>
                      <th>Pendiente</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filas.map((fila) => (
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
              )
            })()}
          </>
        )
      )}
    </div>
  )
}
