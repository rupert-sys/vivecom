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

// Sin centavos: para las cifras del Dashboard no aportan nada (nadie paga $49,500.37 de mantenimiento) y sí
// estorban a simple vista — con separador de miles, que a estos montos ya se le nota la falta.
function formatoDinero(monto: number): string {
  return `$${Math.round(monto).toLocaleString('es-MX')}`
}

// Rotación de color para las tarjetas "cobrado por concepto" (Mantenimiento, Amenidades, Proyecto…) — antes
// eran todas blancas/sin color, lo único vivo en el Dashboard eran Cobrado (teal) y Adeudado (amber).
const PALETA_CONCEPTOS = [
  { color: 'var(--dustblue)', tint: 'var(--dustblue-tint)' },
  { color: 'var(--brick)', tint: 'var(--brick-tint)' },
  { color: 'var(--teal)', tint: 'var(--teal-tint)' },
  { color: 'var(--amber)', tint: 'var(--amber-tint)' },
]

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
  // Qué tarjeta de "cobrado por concepto" está pinchada — null = ninguna. A diferencia de `filtro` (que
  // cambia la tabla de abajo), esto solo expande un detalle bajo las propias tarjetas de concepto.
  const [conceptoAbierto, setConceptoAbierto] = useState<string | null>(null)

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
    setConceptoAbierto(null)
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
            <div role="group" aria-label="Resumen financiero" style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-3)', marginBottom: 'var(--space-3)' }}>
              <StatCard
                label="Viviendas"
                color="var(--dustblue)"
                tint="var(--dustblue-tint)"
                onClick={() => setFiltro('todas')}
                active={filtro === 'todas'}
              >
                {properties.length}
              </StatCard>
              <StatCard
                label="Cobrado"
                color="var(--teal)"
                tint="var(--teal-tint)"
                onClick={() => setFiltro('cobrado')}
                active={filtro === 'cobrado'}
              >
                {formatoDinero(summary.cobrado_total)}
              </StatCard>
              <StatCard
                label="Adeudado"
                color="var(--amber)"
                tint="var(--amber-tint)"
                onClick={() => setFiltro('pendiente')}
                active={filtro === 'pendiente'}
              >
                {formatoDinero(summary.pendiente_total)}
              </StatCard>
            </div>
            <p style={{ color: 'var(--ink-soft)', marginTop: 0 }}>Pincha una tarjeta para ver el detalle por vivienda.</p>

            <div role="group" aria-label="Cobrado por concepto" style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-3)', marginBottom: 'var(--space-3)' }}>
              {summary.por_origen.map((origen, i) => {
                const paleta = PALETA_CONCEPTOS[i % PALETA_CONCEPTOS.length]
                return (
                  <StatCard
                    key={origen.concepto}
                    label={origen.concepto}
                    color={paleta.color}
                    tint={paleta.tint}
                    onClick={() => setConceptoAbierto(conceptoAbierto === origen.concepto ? null : origen.concepto)}
                    active={conceptoAbierto === origen.concepto}
                  >
                    {formatoDinero(origen.cobrado)}
                    {origen.pendiente > 0 && (
                      <span style={{ color: 'var(--amber)', fontSize: '0.85rem', display: 'block' }}>
                        {formatoDinero(origen.pendiente)} pendiente
                      </span>
                    )}
                  </StatCard>
                )
              })}
            </div>

            {conceptoAbierto &&
              (() => {
                const origen = summary.por_origen.find((o) => o.concepto === conceptoAbierto)
                if (!origen) return null
                return (
                  <div className="card" style={{ padding: 'var(--space-3)', marginBottom: 'var(--space-4)' }}>
                    <strong>{origen.concepto}</strong>
                    <p style={{ margin: 'var(--space-2) 0 0' }}>
                      Cobrado: <span className="mono">{formatoDinero(origen.cobrado)}</span>
                      {' · '}
                      Pendiente:{' '}
                      <span className="mono" style={{ color: origen.pendiente > 0 ? 'var(--amber)' : undefined }}>
                        {formatoDinero(origen.pendiente)}
                      </span>
                    </p>
                  </div>
                )
              })()}

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
                          {formatoDinero(fila.cobrado)}
                        </td>
                        <td className="mono" style={{ color: 'var(--amber)' }}>
                          {formatoDinero(fila.pendiente)}
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
