import { useEffect, useState } from 'react'
import { listAmenities } from '../api/amenities'
import { listProperties } from '../api/properties'
import { listReservations, markReservationFeePaid } from '../api/reservations'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { StatCard } from '../components/StatCard'
import type { Amenity, EstadoReserva, Property, Reservation } from '../types'
import { rolesDe } from '../permisos'

const ROLES_CON_ACCESO = new Set<string>(rolesDe('/reservations'))
const ROLES_QUE_RECIBEN_CUOTA = new Set(['admin', 'tesorero'])

const ETIQUETA_ESTADO: Record<EstadoReserva, string> = {
  pendiente: 'Pendiente',
  aprobada: 'Aprobada',
  rechazada: 'Rechazada',
  expirada: 'Expirada',
}

function fechaHora(iso: string): string {
  // El backend guarda UTC "naive" (sin zona): se interpreta como UTC, no como hora local del navegador.
  return new Date(iso.endsWith('Z') ? iso : `${iso}Z`).toLocaleString('es-MX')
}

// Reservaciones de las amenidades y las cuotas de uso que tesorería recibe al solicitarlas
// (reglamento: la cuota se entrega a tesorería y el tesorero deja constancia de haberla recibido).
export function ReservationsPage() {
  const { user } = useAuth()
  const tieneAcceso = user !== null && ROLES_CON_ACCESO.has(user.rol)
  const puedeRecibirCuota = user !== null && ROLES_QUE_RECIBEN_CUOTA.has(user.rol)

  const [reservaciones, setReservaciones] = useState<Reservation[]>([])
  const [amenidades, setAmenidades] = useState<Amenity[]>([])
  const [viviendas, setViviendas] = useState<Property[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [soloCuotaPendiente, setSoloCuotaPendiente] = useState(false)
  const [marcando, setMarcando] = useState<string | null>(null)

  async function reload() {
    setLoading(true)
    try {
      const [r, a, v] = await Promise.all([listReservations(), listAmenities(), listProperties()])
      setReservaciones(r)
      setAmenidades(a)
      setViviendas(v)
      setError(null)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudieron cargar las reservaciones.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (tieneAcceso) reload()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tieneAcceso])

  async function handleMarcar(id: string) {
    setMarcando(id)
    try {
      const actualizada = await markReservationFeePaid(id)
      setReservaciones((actuales) => actuales.map((r) => (r.id === id ? actualizada : r)))
      setError(null)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo marcar la cuota como recibida.')
    } finally {
      setMarcando(null)
    }
  }

  if (!tieneAcceso) {
    return (
      <div>
        <h2>Reservaciones</h2>
        <p>No tienes acceso a esta vista — solo administradores, tesorero y comité aprobador.</p>
      </div>
    )
  }

  const amenidadPorId = new Map(amenidades.map((a) => [a.id, a.nombre]))
  const viviendaPorId = new Map(viviendas.map((v) => [v.id, v.identificador]))

  // Una cuota "pendiente de entregar" solo cuenta si la reservación no se descartó.
  const activa = (r: Reservation) => r.estado === 'pendiente' || r.estado === 'aprobada'
  const conCuotaPendiente = reservaciones.filter((r) => r.cuota > 0 && !r.cuota_pagada && activa(r))
  const totalPendiente = conCuotaPendiente.reduce((suma, r) => suma + r.cuota, 0)
  const totalRecibido = reservaciones.filter((r) => r.cuota > 0 && r.cuota_pagada).reduce((suma, r) => suma + r.cuota, 0)
  const visibles = soloCuotaPendiente ? conCuotaPendiente : reservaciones

  return (
    <div>
      <h2>Reservaciones</h2>
      {error && <p style={{ color: 'var(--brick)' }}>{error}</p>}

      <div style={{ display: 'flex', gap: 'var(--space-3)', margin: 'var(--space-3) 0', flexWrap: 'wrap' }}>
        <StatCard label="Cuotas por recibir" color="var(--amber)">
          ${totalPendiente.toFixed(2)}
        </StatCard>
        <StatCard label="Cuotas recibidas" color="var(--teal)">
          ${totalRecibido.toFixed(2)}
        </StatCard>
      </div>

      <label style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-3)' }}>
        <input type="checkbox" checked={soloCuotaPendiente} onChange={(e) => setSoloCuotaPendiente(e.target.checked)} />
        Solo con cuota pendiente de recibir
      </label>

      {loading ? (
        <p>Cargando…</p>
      ) : visibles.length === 0 ? (
        <p>{soloCuotaPendiente ? 'No hay cuotas pendientes de recibir.' : 'Todavía no hay reservaciones.'}</p>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
              <th>Amenidad</th>
              <th>Vivienda</th>
              <th>Horario</th>
              <th>Estado</th>
              <th>Cuota</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {visibles.map((r) => (
              <tr key={r.id} style={{ borderBottom: '1px solid var(--border)' }}>
                <td>{amenidadPorId.get(r.amenity_id) ?? '—'}</td>
                <td>{viviendaPorId.get(r.property_id) ?? '—'}</td>
                <td className="mono">
                  {fechaHora(r.fecha_inicio)} → {fechaHora(r.fecha_fin)}
                </td>
                <td>{ETIQUETA_ESTADO[r.estado]}</td>
                <td className="mono">{r.cuota > 0 ? `$${r.cuota.toFixed(2)}` : '—'}</td>
                <td>
                  {r.cuota > 0 && r.cuota_pagada && <span style={{ color: 'var(--teal)' }}>Recibida</span>}
                  {r.cuota > 0 && !r.cuota_pagada && activa(r) && puedeRecibirCuota && (
                    <button onClick={() => handleMarcar(r.id)} disabled={marcando === r.id}>
                      {marcando === r.id ? 'Marcando…' : 'Marcar cuota recibida'}
                    </button>
                  )}
                  {r.cuota > 0 && !r.cuota_pagada && activa(r) && !puedeRecibirCuota && (
                    <span style={{ color: 'var(--amber)' }}>Pendiente</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
