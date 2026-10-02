import { useEffect, useState } from 'react'
import { listPackages } from '../api/packages'
import { listProperties } from '../api/properties'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { StatCard } from '../components/StatCard'
import type { Package, Property } from '../types'
import { rolesDe } from '../permisos'

const ROLES_CON_ACCESO = new Set<string>(rolesDe('/packages'))

function fechaHora(iso: string): string {
  // El backend guarda UTC "naive" (sin zona): se interpreta como UTC, no como hora local del navegador.
  return new Date(iso.endsWith('Z') ? iso : `${iso}Z`).toLocaleString('es-MX')
}

function diasEsperando(fechaLlegada: string): number {
  const llegada = new Date(fechaLlegada.endsWith('Z') ? fechaLlegada : `${fechaLlegada}Z`)
  const ms = Date.now() - llegada.getTime()
  return Math.max(0, Math.floor(ms / (1000 * 60 * 60 * 24)))
}

// Pedido explícito de administradores (alcance_vivecom.md): un resumen de paquetería en el panel admin — hasta
// ahora solo se veía desde la app de caseta, el admin no tenía forma de saber qué sigue esperando ser recogido.
export function PackagesPage() {
  const { user } = useAuth()
  const tieneAcceso = user !== null && ROLES_CON_ACCESO.has(user.rol)

  const [paquetes, setPaquetes] = useState<Package[]>([])
  const [viviendas, setViviendas] = useState<Property[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  async function reload() {
    setLoading(true)
    try {
      const [p, v] = await Promise.all([listPackages(), listProperties()])
      setPaquetes(p)
      setViviendas(v)
      setError(null)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo cargar la paquetería.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (tieneAcceso) reload()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tieneAcceso])

  if (!tieneAcceso) {
    return (
      <div>
        <h2>Paquetería</h2>
        <p>No tienes acceso a esta vista — solo administradores.</p>
      </div>
    )
  }

  const viviendaPorId = new Map(viviendas.map((v) => [v.id, v.identificador]))
  const pendientes = paquetes
    .filter((p) => p.fecha_recogido === null)
    .sort((a, b) => new Date(a.fecha_llegada).getTime() - new Date(b.fecha_llegada).getTime())
  const recogidos = paquetes.filter((p) => p.fecha_recogido !== null)
  const masDeTresDias = pendientes.filter((p) => diasEsperando(p.fecha_llegada) >= 3).length

  return (
    <div>
      <h2>Paquetería</h2>
      {error && <p style={{ color: 'var(--brick)' }}>{error}</p>}

      <div role="group" aria-label="Resumen de paquetería" style={{ display: 'flex', gap: 'var(--space-3)', margin: 'var(--space-3) 0', flexWrap: 'wrap' }}>
        <StatCard label="Pendientes de recoger" color="var(--amber)" tint="var(--amber-tint)">
          {pendientes.length}
        </StatCard>
        <StatCard label="Con 3+ días esperando" color="var(--brick)" tint="var(--brick-tint)">
          {masDeTresDias}
        </StatCard>
        <StatCard label="Recogidos" color="var(--teal)" tint="var(--teal-tint)">
          {recogidos.length}
        </StatCard>
      </div>

      {loading ? (
        <p>Cargando…</p>
      ) : pendientes.length === 0 ? (
        <p>No hay paquetes pendientes de recoger.</p>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
              <th>Vivienda</th>
              <th>Llegó</th>
              <th>Días esperando</th>
            </tr>
          </thead>
          <tbody>
            {pendientes.map((p) => {
              const dias = diasEsperando(p.fecha_llegada)
              return (
                <tr key={p.id} style={{ borderBottom: '1px solid var(--border)' }}>
                  <td>{viviendaPorId.get(p.property_id) ?? '—'}</td>
                  <td className="mono">{fechaHora(p.fecha_llegada)}</td>
                  <td className="mono" style={{ color: dias >= 3 ? 'var(--brick)' : undefined }}>
                    {dias}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      )}
    </div>
  )
}
