import { useEffect, useState } from 'react'
import { getCollectionsSummary } from '../api/reports'
import { listProperties } from '../api/properties'
import { getFinancialSummary } from '../api/expenses'
import { getCashBalance } from '../api/cashMovements'
import { listReservations } from '../api/reservations'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { StatCard } from '../components/StatCard'
import type { CashBalance, CollectionsSummary, FinancialSummary, Property, PropertyCollectionsSummary, Reservation } from '../types'
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

// Último día de un mes "YYYY-MM", para pedirle a /expenses/summary el mismo rango que el selector de periodo.
function finDeMes(mes: string): string {
  const [anio, numeroMes] = mes.split('-').map(Number)
  const ultimoDia = new Date(anio, numeroMes, 0).getDate()
  return `${mes}-${String(ultimoDia).padStart(2, '0')}`
}

function fecha(iso: string): string {
  return new Date(iso.endsWith('Z') ? iso : `${iso}Z`).toLocaleDateString('es-MX')
}

// Reservaciones de amenidades con cuota a cobrar, en el mismo periodo/vivienda que el resto del Dashboard —
// mismo filtro (mes calendario de fecha_inicio, property_id exacto) que ya usa el backend para "Amenidades"
// en collections_summary_service.py, para que el detalle cuadre con la tarjeta de ese concepto.
function reservacionesDelPeriodo(reservations: Reservation[], mes: string, propertyId: string): Reservation[] {
  let filtradas = reservations.filter((r) => r.cuota > 0)
  if (mes) {
    const [anio, numeroMes] = mes.split('-').map(Number)
    const finExclusivo = numeroMes === 12 ? `${anio + 1}-01-01` : `${anio}-${String(numeroMes + 1).padStart(2, '0')}-01`
    filtradas = filtradas.filter((r) => r.fecha_inicio >= `${mes}-01` && r.fecha_inicio < finExclusivo)
  }
  if (propertyId) filtradas = filtradas.filter((r) => r.property_id === propertyId)
  return filtradas
}

export function DashboardPage() {
  const { user } = useAuth()
  const tieneAcceso = user !== null && ROLES_CON_ACCESO.has(user.rol)

  const [properties, setProperties] = useState<Property[]>([])
  const [summary, setSummary] = useState<CollectionsSummary | null>(null)
  const [financial, setFinancial] = useState<FinancialSummary | null>(null)
  const [cashBalance, setCashBalance] = useState<CashBalance | null>(null)
  const [reservations, setReservations] = useState<Reservation[]>([])
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
      const [propertiesResult, summaryResult, financialResult, cashBalanceResult, reservationsResult] = await Promise.all([
        listProperties(),
        getCollectionsSummary({ periodo: mes ? `${mes}-01` : undefined, propertyId: propertyId || undefined }),
        // Los egresos no son por vivienda (un gasto es del condominio, no de una casa), así que solo respetan el periodo.
        getFinancialSummary(mes ? `${mes}-01` : undefined, mes ? finDeMes(mes) : undefined),
        getCashBalance(), // saldo acumulado de toda la vida de la caja: no se filtra por periodo ni por vivienda.
        listReservations(),
      ])
      setProperties(propertiesResult)
      setSummary(summaryResult)
      setFinancial(financialResult)
      setCashBalance(cashBalanceResult)
      setReservations(reservationsResult)
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
              {financial && (
                <StatCard label="Egresos" color="var(--brick)" tint="var(--brick-tint)">
                  {formatoDinero(financial.gastos)}
                </StatCard>
              )}
            </div>
            <p style={{ color: 'var(--ink-soft)', marginTop: 0 }}>Pincha una tarjeta para ver el detalle por vivienda.</p>

            {cashBalance && (
              <div role="group" aria-label="Caja chica y grande" style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-3)', marginBottom: 'var(--space-3)' }}>
                <StatCard label="Caja chica" color="var(--dustblue)" tint="var(--dustblue-tint)">
                  {formatoDinero(cashBalance.chica)}
                </StatCard>
                <StatCard label="Caja grande" color="var(--dustblue)" tint="var(--dustblue-tint)">
                  {formatoDinero(cashBalance.grande)}
                </StatCard>
              </div>
            )}

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
                const viviendaPorId = new Map(properties.map((p) => [p.id, p.identificador]))
                const detalleReservaciones =
                  origen.concepto === 'Amenidades' ? reservacionesDelPeriodo(reservations, mes, propertyId) : []
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
                    {origen.concepto === 'Amenidades' &&
                      (detalleReservaciones.length === 0 ? (
                        <p style={{ color: 'var(--ink-soft)' }}>No hay reservaciones con cuota en estos filtros.</p>
                      ) : (
                        <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: 'var(--space-2)' }}>
                          <thead>
                            <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
                              <th>Vivienda</th>
                              <th>Fecha</th>
                              <th>Pago</th>
                            </tr>
                          </thead>
                          <tbody>
                            {detalleReservaciones.map((r) => (
                              <tr key={r.id} style={{ borderBottom: '1px solid var(--border)' }}>
                                <td>{viviendaPorId.get(r.property_id) ?? '—'}</td>
                                <td className="mono">{fecha(r.fecha_inicio)}</td>
                                <td className="mono" style={{ color: r.cuota_pagada ? 'var(--teal)' : 'var(--amber)' }}>
                                  {formatoDinero(r.cuota)}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      ))}
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
