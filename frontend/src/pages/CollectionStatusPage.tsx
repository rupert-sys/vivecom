import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { downloadNoDebtCertificate, getCollectionStatus } from '../api/reports'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { StatCard } from '../components/StatCard'
import type { CollectionStatus, EstatusCobranza } from '../types'
import { rolesDe } from '../permisos'

const ROLES_CON_ACCESO = new Set<string>(rolesDe('/collection'))

const ETIQUETA: Record<EstatusCobranza, string> = {
  moroso: 'Moroso',
  con_acuerdo: 'Con acuerdo',
  pendiente: 'Pendiente',
  al_corriente: 'Al corriente',
}
const COLOR: Record<EstatusCobranza, string> = {
  moroso: 'var(--brick)',
  con_acuerdo: 'var(--dustblue)',
  pendiente: 'var(--amber)',
  al_corriente: 'var(--teal)',
}

type Filtro = 'todas' | EstatusCobranza

// Quién ya pagó, quién falta y quién es moroso (venció el plazo del reglamento), por vivienda.
export function CollectionStatusPage() {
  const { user } = useAuth()
  const tieneAcceso = user !== null && ROLES_CON_ACCESO.has(user.rol)

  const [estado, setEstado] = useState<CollectionStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [mes, setMes] = useState('')
  const [filtro, setFiltro] = useState<Filtro>('todas')
  const [descargando, setDescargando] = useState<string | null>(null)

  useEffect(() => {
    if (!tieneAcceso) return
    setLoading(true)
    getCollectionStatus(mes ? `${mes}-01` : undefined)
      .then((resultado) => {
        setEstado(resultado)
        setError(null)
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : 'No se pudo cargar el estatus de cobranza.'))
      .finally(() => setLoading(false))
  }, [tieneAcceso, mes])

  async function handleConstancia(propertyId: string, identificador: string) {
    setDescargando(propertyId)
    try {
      await downloadNoDebtCertificate(propertyId, identificador)
      setError(null)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo generar la constancia.')
    } finally {
      setDescargando(null)
    }
  }

  if (!tieneAcceso) {
    return (
      <div>
        <h2>Cobranza</h2>
        <p>No tienes acceso a esta vista — solo administradores y tesorero.</p>
      </div>
    )
  }

  const viviendas = (estado?.viviendas ?? []).filter((v) => filtro === 'todas' || v.estatus === filtro)

  return (
    <div>
      <h2>Cobranza</h2>
      <p style={{ color: 'var(--ink-soft)' }}>
        Quién está al corriente, quién falta por pagar dentro del plazo y quién es moroso según el reglamento.
      </p>
      {error && <p style={{ color: 'var(--brick)' }}>{error}</p>}

      <div style={{ display: 'flex', gap: 'var(--space-2)', margin: 'var(--space-3) 0', flexWrap: 'wrap' }}>
        <input type="month" aria-label="Periodo" value={mes} onChange={(e) => setMes(e.target.value)} />
        {(['todas', 'moroso', 'con_acuerdo', 'pendiente', 'al_corriente'] as Filtro[]).map((f) => (
          <button key={f} aria-pressed={filtro === f} onClick={() => setFiltro(f)}>
            {f === 'todas' ? 'Todas' : ETIQUETA[f]}
          </button>
        ))}
      </div>

      {loading ? (
        <p>Cargando…</p>
      ) : (
        estado && (
          <>
            <div style={{ display: 'flex', gap: 'var(--space-3)', marginBottom: 'var(--space-4)', flexWrap: 'wrap' }}>
              <StatCard label="Al corriente" color={COLOR.al_corriente}>
                {estado.al_corriente}
              </StatCard>
              <StatCard label="Pendientes" color={COLOR.pendiente}>
                {estado.pendientes}
              </StatCard>
              <StatCard label="Morosos" color={COLOR.moroso}>
                {estado.morosas}
              </StatCard>
              <StatCard label="Con acuerdo de pago" color={COLOR.con_acuerdo}>
                {estado.con_acuerdo}
              </StatCard>
              <StatCard label="Adeudo total">${estado.adeudo_total.toFixed(2)}</StatCard>
            </div>

            {viviendas.length === 0 ? (
              <p>No hay viviendas con este estatus.</p>
            ) : (
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
                    <th>Vivienda</th>
                    <th>Estatus</th>
                    <th>Adeudo</th>
                    <th>Cargos vencidos</th>
                    <th>Pagó el periodo</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {viviendas.map((v) => (
                    <tr key={v.property_id} style={{ borderBottom: '1px solid var(--border)' }}>
                      <td>
                        <Link to={`/properties/${v.property_id}`}>{v.identificador}</Link>
                      </td>
                      <td style={{ color: COLOR[v.estatus] }}>{ETIQUETA[v.estatus]}</td>
                      <td className="mono">${v.adeudo_total.toFixed(2)}</td>
                      <td className="mono">{v.cargos_vencidos}</td>
                      <td>{v.periodo_pagado === null ? '—' : v.periodo_pagado ? 'Sí' : 'No'}</td>
                      <td>
                        {v.estatus === 'al_corriente' && (
                          <button
                            onClick={() => handleConstancia(v.property_id, v.identificador)}
                            disabled={descargando === v.property_id}
                          >
                            {descargando === v.property_id ? 'Generando…' : 'Constancia de no adeudo'}
                          </button>
                        )}
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
