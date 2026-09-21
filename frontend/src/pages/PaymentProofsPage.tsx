import { useEffect, useState } from 'react'
import { acceptPaymentProof, listPaymentProofs, rejectPaymentProof } from '../api/paymentProofs'
import { listProperties } from '../api/properties'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import type { EstadoComprobante, PaymentProof, Property } from '../types'
import { rolesDe } from '../permisos'

const ROLES_CON_ACCESO = new Set<string>(rolesDe('/payment-proofs'))

const ETIQUETA: Record<EstadoComprobante, string> = { pendiente: 'Pendiente', aceptado: 'Aceptado', rechazado: 'Rechazado' }
const COLOR: Record<EstadoComprobante, string> = {
  pendiente: 'var(--amber)',
  aceptado: 'var(--teal)',
  rechazado: 'var(--brick)',
}

function fecha(iso: string): string {
  // UTC "naive" del backend: se interpreta como UTC, no como hora local del navegador.
  return new Date(iso.endsWith('Z') ? iso : `${iso}Z`).toLocaleString('es-MX')
}

// Comprobantes de pago que los residentes adjuntan desde su app (captura o PDF del banco). Tesorería
// abre el archivo, confirma que el dinero llegó y lo acepta (se registra el pago), o lo rechaza con un
// motivo que el residente ve.
export function PaymentProofsPage() {
  const { user } = useAuth()
  const tieneAcceso = user !== null && ROLES_CON_ACCESO.has(user.rol)

  const [comprobantes, setComprobantes] = useState<PaymentProof[]>([])
  const [viviendas, setViviendas] = useState<Property[]>([])
  const [filtro, setFiltro] = useState<EstadoComprobante>('pendiente')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [montos, setMontos] = useState<Record<string, string>>({})
  const [rechazando, setRechazando] = useState<string | null>(null)
  const [motivo, setMotivo] = useState('')
  const [trabajando, setTrabajando] = useState<string | null>(null)
  // El SPEI ya detectó un pago igual: se pide confirmar que este es otro antes de contarlo.
  const [posibleDuplicado, setPosibleDuplicado] = useState<{ id: string; mensaje: string } | null>(null)

  async function reload() {
    setLoading(true)
    try {
      const [c, v] = await Promise.all([listPaymentProofs(filtro), listProperties()])
      setComprobantes(c)
      setViviendas(v)
      setError(null)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudieron cargar los comprobantes.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (tieneAcceso) reload()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tieneAcceso, filtro])

  async function handleAceptar(prueba: PaymentProof, forzar = false) {
    setTrabajando(prueba.id)
    setPosibleDuplicado(null)
    try {
      const montoEditado = montos[prueba.id]
      await acceptPaymentProof(prueba.id, {
        ...(montoEditado !== undefined && montoEditado !== '' ? { monto: Number(montoEditado) } : {}),
        ...(forzar ? { forzar: true } : {}),
      })
      setError(null)
      await reload()
    } catch (err) {
      if (err instanceof ApiError && err.status === 409 && err.message.includes('SPEI ya detectó')) {
        setPosibleDuplicado({ id: prueba.id, mensaje: err.message })
      } else {
        setError(err instanceof ApiError ? err.message : 'No se pudo aceptar el comprobante.')
      }
    } finally {
      setTrabajando(null)
    }
  }

  async function handleRechazar(id: string) {
    if (motivo.trim() === '') return
    setTrabajando(id)
    try {
      await rejectPaymentProof(id, motivo.trim())
      setRechazando(null)
      setMotivo('')
      setError(null)
      await reload()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo rechazar el comprobante.')
    } finally {
      setTrabajando(null)
    }
  }

  if (!tieneAcceso) {
    return (
      <div>
        <h2>Comprobantes de pago</h2>
        <p>No tienes acceso a esta vista — solo administradores y tesorero.</p>
      </div>
    )
  }

  const viviendaPorId = new Map(viviendas.map((v) => [v.id, v.identificador]))

  return (
    <div>
      <h2>Comprobantes de pago</h2>
      <p style={{ color: 'var(--ink-soft)' }}>
        Los residentes adjuntan aquí la captura o el PDF de su transferencia. Al aceptar uno se registra el pago y se
        concilia contra sus cargos; revisa primero que el dinero sí haya llegado a la cuenta.
      </p>
      {error && <p style={{ color: 'var(--brick)' }}>{error}</p>}

      <div style={{ display: 'flex', gap: 'var(--space-2)', margin: 'var(--space-3) 0' }}>
        {(['pendiente', 'aceptado', 'rechazado'] as EstadoComprobante[]).map((estado) => (
          <button key={estado} aria-pressed={filtro === estado} onClick={() => setFiltro(estado)}>
            {ETIQUETA[estado]}
          </button>
        ))}
      </div>

      {loading ? (
        <p>Cargando…</p>
      ) : comprobantes.length === 0 ? (
        <p>No hay comprobantes {ETIQUETA[filtro].toLowerCase()}s.</p>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
              <th>Vivienda</th>
              <th>Monto</th>
              <th>Fecha del pago</th>
              <th>Nota</th>
              <th>Comprobante</th>
              <th>Estado</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {comprobantes.map((p) => (
              <tr key={p.id} style={{ borderBottom: '1px solid var(--border)', verticalAlign: 'top' }}>
                <td>{viviendaPorId.get(p.property_id) ?? '—'}</td>
                <td className="mono">${p.monto.toFixed(2)}</td>
                <td className="mono">{p.fecha_pago ?? '—'}</td>
                <td>{p.nota ?? '—'}</td>
                <td>
                  <a href={p.archivo_url} target="_blank" rel="noreferrer">
                    Ver comprobante
                  </a>
                  <div style={{ color: 'var(--ink-soft)' }}>Enviado {fecha(p.created_at)}</div>
                </td>
                <td style={{ color: COLOR[p.estado] }}>
                  {ETIQUETA[p.estado]}
                  {p.estado === 'rechazado' && p.motivo_rechazo && (
                    <div style={{ color: 'var(--ink-soft)' }}>{p.motivo_rechazo}</div>
                  )}
                </td>
                <td>
                  {p.estado === 'pendiente' && (
                    <div style={{ display: 'grid', gap: 'var(--space-2)' }}>
                      <input
                        type="number"
                        step="0.01"
                        min="0.01"
                        aria-label={`Monto que llegó (${viviendaPorId.get(p.property_id) ?? p.id})`}
                        placeholder={`Llegó: $${p.monto.toFixed(2)}`}
                        value={montos[p.id] ?? ''}
                        onChange={(e) => setMontos({ ...montos, [p.id]: e.target.value })}
                      />
                      <button onClick={() => handleAceptar(p)} disabled={trabajando === p.id}>
                        {trabajando === p.id ? 'Procesando…' : 'Aceptar y registrar pago'}
                      </button>
                      {posibleDuplicado?.id === p.id && (
                        <div style={{ color: 'var(--amber)' }}>
                          <p>{posibleDuplicado.mensaje}</p>
                          <button onClick={() => handleAceptar(p, true)}>Es otro pago: aceptar de todos modos</button>
                        </div>
                      )}
                      {rechazando === p.id ? (
                        <>
                          <input
                            placeholder="Motivo del rechazo"
                            value={motivo}
                            onChange={(e) => setMotivo(e.target.value)}
                          />
                          <button onClick={() => handleRechazar(p.id)} disabled={motivo.trim() === '' || trabajando === p.id}>
                            Confirmar rechazo
                          </button>
                        </>
                      ) : (
                        <button onClick={() => setRechazando(p.id)} style={{ color: 'var(--brick)' }}>
                          Rechazar
                        </button>
                      )}
                    </div>
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
