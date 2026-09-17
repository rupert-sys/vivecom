import { useEffect, useState } from 'react'
import { listIncidents } from '../api/incidents'
import { listAccessLogs } from '../api/accessLog'
import { listProperties } from '../api/properties'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import type { AccessLogEntry, Incident, Property } from '../types'

const ROLES_ACCESOS = new Set(['admin', 'guardia'])
const ROLES_INCIDENCIAS = new Set(['admin', 'guardia', 'comite_lectura', 'comite_aprobador'])

function horasEntre(desde: string, hasta: string): number {
  return (new Date(hasta).getTime() - new Date(desde).getTime()) / (1000 * 60 * 60)
}

export function SecurityDashboardPage() {
  const { user } = useAuth()
  const puedeVerAccesos = user !== null && ROLES_ACCESOS.has(user.rol)
  const puedeVerIncidencias = user !== null && ROLES_INCIDENCIAS.has(user.rol)

  const [incidents, setIncidents] = useState<Incident[]>([])
  const [accessLogs, setAccessLogs] = useState<AccessLogEntry[]>([])
  const [properties, setProperties] = useState<Property[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function reload() {
      setLoading(true)
      try {
        if (puedeVerIncidencias) setIncidents(await listIncidents())
        if (puedeVerAccesos) {
          setAccessLogs(await listAccessLogs())
          setProperties(await listProperties())
        }
        setError(null)
      } catch (err) {
        setError(err instanceof ApiError ? err.message : 'No se pudo cargar el dashboard de seguridad.')
      } finally {
        setLoading(false)
      }
    }
    reload()
  }, [puedeVerAccesos, puedeVerIncidencias])

  if (!puedeVerAccesos && !puedeVerIncidencias) {
    return (
      <div>
        <h2>Dashboard de seguridad</h2>
        <p>No tienes acceso a esta vista.</p>
      </div>
    )
  }

  const abiertas = incidents.filter((i) => i.estado === 'abierta').length
  const enProceso = incidents.filter((i) => i.estado === 'en_proceso').length
  const resueltas = incidents.filter((i) => i.estado === 'resuelta').length
  const incidenciasAbiertas = incidents.filter((i) => i.estado !== 'resuelta')

  const resolucionesEnHoras = incidents
    .filter((i): i is Incident & { resolved_at: string } => i.estado === 'resuelta' && i.resolved_at !== null)
    .map((i) => horasEntre(i.created_at, i.resolved_at))
  const promedioResolucionHoras =
    resolucionesEnHoras.length > 0 ? resolucionesEnHoras.reduce((a, b) => a + b, 0) / resolucionesEnHoras.length : null

  const propiedadPorId = new Map(properties.map((p) => [p.id, p.identificador]))
  const accesosPorTipo = { residente: 0, visitante: 0, proveedor: 0 }
  for (const log of accessLogs) accesosPorTipo[log.tipo] += 1

  return (
    <div>
      <h2>Dashboard de seguridad</h2>
      {error && <p style={{ color: 'var(--brick)' }}>{error}</p>}
      {loading && <p>Cargando…</p>}

      {puedeVerIncidencias && (
        <>
          <h3>Incidencias</h3>
          <div style={{ display: 'flex', gap: 'var(--space-3)', marginBottom: 'var(--space-3)', flexWrap: 'wrap' }}>
            <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: 'var(--space-3)', flex: 1 }}>
              <div style={{ color: 'var(--ink-soft)' }}>Abiertas</div>
              <div className="mono" style={{ color: 'var(--brick)', fontSize: '1.5rem' }}>
                {abiertas}
              </div>
            </div>
            <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: 'var(--space-3)', flex: 1 }}>
              <div style={{ color: 'var(--ink-soft)' }}>En proceso</div>
              <div className="mono" style={{ color: 'var(--amber)', fontSize: '1.5rem' }}>
                {enProceso}
              </div>
            </div>
            <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: 'var(--space-3)', flex: 1 }}>
              <div style={{ color: 'var(--ink-soft)' }}>Resueltas</div>
              <div className="mono" style={{ color: 'var(--teal)', fontSize: '1.5rem' }}>
                {resueltas}
              </div>
            </div>
            <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: 'var(--space-3)', flex: 1 }}>
              <div style={{ color: 'var(--ink-soft)' }}>Tiempo promedio de resolución</div>
              <div className="mono" style={{ fontSize: '1.5rem' }}>
                {promedioResolucionHoras === null ? 'Sin datos aún' : `${promedioResolucionHoras.toFixed(1)}h`}
              </div>
            </div>
          </div>

          {incidenciasAbiertas.length === 0 ? (
            <p>No hay incidencias abiertas ni en proceso.</p>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: 'var(--space-4)' }}>
              <thead>
                <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
                  <th>Descripción</th>
                  <th>Estado</th>
                  <th>Reportada</th>
                </tr>
              </thead>
              <tbody>
                {incidenciasAbiertas.map((i) => (
                  <tr key={i.id} style={{ borderBottom: '1px solid var(--border)' }}>
                    <td>{i.descripcion}</td>
                    <td style={{ color: i.estado === 'abierta' ? 'var(--brick)' : 'var(--amber)' }}>
                      {i.estado === 'abierta' ? 'Abierta' : 'En proceso'}
                    </td>
                    <td className="mono">{new Date(i.created_at).toLocaleString('es-MX')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}

      {puedeVerAccesos && (
        <>
          <h3>Accesos</h3>
          <div style={{ display: 'flex', gap: 'var(--space-3)', marginBottom: 'var(--space-3)', flexWrap: 'wrap' }}>
            <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: 'var(--space-3)', flex: 1 }}>
              <div style={{ color: 'var(--ink-soft)' }}>Residentes</div>
              <div className="mono" style={{ fontSize: '1.5rem' }}>
                {accesosPorTipo.residente}
              </div>
            </div>
            <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: 'var(--space-3)', flex: 1 }}>
              <div style={{ color: 'var(--ink-soft)' }}>Visitantes</div>
              <div className="mono" style={{ fontSize: '1.5rem' }}>
                {accesosPorTipo.visitante}
              </div>
            </div>
            <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: 'var(--space-3)', flex: 1 }}>
              <div style={{ color: 'var(--ink-soft)' }}>Proveedores</div>
              <div className="mono" style={{ fontSize: '1.5rem' }}>
                {accesosPorTipo.proveedor}
              </div>
            </div>
          </div>

          {accessLogs.length === 0 ? (
            <p>Todavía no hay accesos registrados.</p>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
                  <th>Tipo</th>
                  <th>Vivienda</th>
                  <th>Entrada</th>
                  <th>Salida</th>
                </tr>
              </thead>
              <tbody>
                {accessLogs.map((log) => (
                  <tr key={log.id} style={{ borderBottom: '1px solid var(--border)' }}>
                    <td>{log.tipo}</td>
                    <td>{log.property_id ? (propiedadPorId.get(log.property_id) ?? '—') : 'General'}</td>
                    <td className="mono">{new Date(log.hora_entrada).toLocaleString('es-MX')}</td>
                    <td className="mono">{log.hora_salida ? new Date(log.hora_salida).toLocaleString('es-MX') : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </div>
  )
}
