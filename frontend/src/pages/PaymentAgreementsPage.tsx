import { useEffect, useState, type FormEvent } from 'react'
import {
  approvePaymentAgreement,
  cancelPaymentAgreement,
  listPaymentAgreements,
  rejectPaymentAgreement,
  requestPaymentAgreement,
} from '../api/paymentAgreements'
import { TIPOS_DE_ARCHIVO_ACEPTADOS, uploadFile } from '../api/files'
import { listProperties } from '../api/properties'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { StatCard } from '../components/StatCard'
import type { EstadoAcuerdo, PaymentAgreement, Property } from '../types'
import { rolesDe } from '../permisos'

const ROLES_QUE_VEN = new Set<string>(rolesDe('/payment-agreements'))
// Art. 9 VII: "el comité tendrá la facultad de tomar el acuerdo". El administrador también decide, para
// condominios sin comité configurado. Tesorería y el comité de solo lectura dan seguimiento pero no deciden.
const ROLES_QUE_DECIDEN = new Set(['admin', 'comite_aprobador'])

const ETIQUETA: Record<EstadoAcuerdo, string> = {
  solicitado: 'Por decidir',
  vigente: 'Vigente',
  rechazado: 'Rechazado',
  cumplido: 'Cumplido',
  incumplido: 'Incumplido',
  cancelado: 'Cancelado',
}
const COLOR: Record<EstadoAcuerdo, string> = {
  solicitado: 'var(--amber)',
  vigente: 'var(--dustblue)',
  rechazado: 'var(--brick)',
  cumplido: 'var(--teal)',
  incumplido: 'var(--brick)',
  cancelado: 'var(--ink-soft)',
}

function money(valor: number): string {
  return `$${valor.toFixed(2)}`
}

function fecha(iso: string): string {
  // UTC "naive" del backend: se interpreta como UTC, no como hora local del navegador.
  return new Date(iso.endsWith('Z') ? iso : `${iso}Z`).toLocaleDateString('es-MX')
}

interface FilaCalendario {
  fecha: string
  monto: string
}

// Acuerdos de pago (prórroga de cuotas). El residente los solicita por escrito desde su app; el comité decide;
// mientras se cumplen, la vivienda no cuenta como morosa y, si el comité lo decide, su recargo se congela.
export function PaymentAgreementsPage() {
  const { user } = useAuth()
  const tieneAcceso = user !== null && ROLES_QUE_VEN.has(user.rol)
  const puedeDecidir = user !== null && ROLES_QUE_DECIDEN.has(user.rol)
  const esAdmin = user?.rol === 'admin'

  const [acuerdos, setAcuerdos] = useState<PaymentAgreement[]>([])
  const [viviendas, setViviendas] = useState<Property[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [trabajando, setTrabajando] = useState<string | null>(null)

  // Decisión por solicitud
  const [congela, setCongela] = useState<Record<string, boolean>>({})
  const [calendarioPropio, setCalendarioPropio] = useState<Record<string, FilaCalendario[] | undefined>>({})
  const [rechazando, setRechazando] = useState<string | null>(null)
  const [motivo, setMotivo] = useState('')

  // Captura del administrador
  const [propertyId, setPropertyId] = useState('')
  const [causa, setCausa] = useState('')
  const [pagos, setPagos] = useState('1')
  const [primerPago, setPrimerPago] = useState('')
  const [documento, setDocumento] = useState<File | null>(null)
  const [capturando, setCapturando] = useState(false)

  async function reload() {
    setLoading(true)
    try {
      const [a, v] = await Promise.all([listPaymentAgreements(), listProperties()])
      setAcuerdos(a)
      setViviendas(v)
      setError(null)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudieron cargar los acuerdos de pago.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (tieneAcceso) reload()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tieneAcceso])

  async function handleAprobar(acuerdo: PaymentAgreement) {
    setTrabajando(acuerdo.id)
    try {
      const propio = calendarioPropio[acuerdo.id]
      await approvePaymentAgreement(acuerdo.id, {
        congela_recargo: congela[acuerdo.id] ?? true,
        ...(propio ? { pagos: propio.map((f) => ({ fecha: f.fecha, monto: Number(f.monto) })) } : {}),
      })
      setError(null)
      await reload()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo aprobar el acuerdo.')
    } finally {
      setTrabajando(null)
    }
  }

  async function handleRechazar(id: string) {
    if (motivo.trim() === '') return
    setTrabajando(id)
    try {
      await rejectPaymentAgreement(id, motivo.trim())
      setRechazando(null)
      setMotivo('')
      setError(null)
      await reload()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo rechazar el acuerdo.')
    } finally {
      setTrabajando(null)
    }
  }

  async function handleCancelar(acuerdo: PaymentAgreement) {
    if (!window.confirm(`¿Cancelar el acuerdo de ${acuerdo.vivienda ?? 'la vivienda'}? Lo cubierto volverá a contar como mora.`)) return
    setTrabajando(acuerdo.id)
    try {
      await cancelPaymentAgreement(acuerdo.id)
      setError(null)
      await reload()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo cancelar el acuerdo.')
    } finally {
      setTrabajando(null)
    }
  }

  async function handleCapturar(event: FormEvent) {
    event.preventDefault()
    setCapturando(true)
    try {
      const archivo = documento ? await uploadFile(documento, 'acuerdo') : null
      await requestPaymentAgreement({
        property_id: propertyId,
        causa,
        numero_de_pagos: Number(pagos),
        primer_pago: primerPago,
        ...(archivo ? { archivo_id: archivo.id } : {}),
      })
      setPropertyId('')
      setCausa('')
      setPagos('1')
      setPrimerPago('')
      setDocumento(null)
      setError(null)
      await reload()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo registrar la solicitud.')
    } finally {
      setCapturando(false)
    }
  }

  if (!tieneAcceso) {
    return (
      <div>
        <h2>Acuerdos de pago</h2>
        <p>No tienes acceso a esta vista — solo administración, comité y tesorería.</p>
      </div>
    )
  }

  const porDecidir = acuerdos.filter((a) => a.estado === 'solicitado')
  const vigentes = acuerdos.filter((a) => a.estado === 'vigente')
  const historial = acuerdos.filter((a) => !['solicitado', 'vigente'].includes(a.estado))
  const deudaCubierta = vigentes.reduce((suma, a) => suma + (a.pendiente_cubierto ?? 0), 0)

  const tarjeta = {
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius)',
    padding: 'var(--space-3)',
  } as const

  return (
    <div>
      <h2>Acuerdos de pago</h2>
      <p style={{ color: 'var(--ink-soft)' }}>
        Prórroga de cuotas por causas justificadas (reglamento, Art. 1 VIII y 9 VII). Mientras se cumple, la vivienda no
        cuenta como morosa: conserva su voto y las áreas comunes. Una solicitud pendiente no cambia nada hasta que se aprueba.
        {!puedeDecidir && ' Tu rol es de seguimiento: no puedes decidir.'}
      </p>
      {error && <p style={{ color: 'var(--brick)' }}>{error}</p>}

      <div style={{ display: 'flex', gap: 'var(--space-3)', margin: 'var(--space-3) 0', flexWrap: 'wrap' }}>
        <StatCard label="Por decidir" color="var(--amber)">
          {porDecidir.length}
        </StatCard>
        <StatCard label="Vigentes" color="var(--dustblue)">
          {vigentes.length}
        </StatCard>
        <StatCard label="Deuda que cubren">{money(deudaCubierta)}</StatCard>
      </div>

      {esAdmin && (
        <details style={{ marginBottom: 'var(--space-4)' }}>
          <summary>Capturar la solicitud por escrito de un vecino</summary>
          <form onSubmit={handleCapturar} style={{ display: 'grid', gap: 'var(--space-2)', maxWidth: 480, marginTop: 'var(--space-2)' }}>
            <select aria-label="Vivienda del acuerdo" value={propertyId} onChange={(e) => setPropertyId(e.target.value)} required>
              <option value="">Vivienda…</option>
              {viviendas.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.identificador}
                </option>
              ))}
            </select>
            <textarea
              rows={3}
              placeholder="Causa justificada (mínimo 20 caracteres)"
              value={causa}
              onChange={(e) => setCausa(e.target.value)}
              minLength={20}
              required
            />
            <label>
              Número de pagos mensuales (1 = una nueva fecha)
              <select aria-label="Número de pagos" value={pagos} onChange={(e) => setPagos(e.target.value)} style={{ display: 'block' }}>
                {[1, 2, 3, 4, 5, 6].map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Fecha del primer pago
              <input type="date" aria-label="Primer pago" value={primerPago} onChange={(e) => setPrimerPago(e.target.value)} required style={{ display: 'block' }} />
            </label>
            <label>
              Escrito o documento de respaldo (opcional)
              <input
                type="file"
                accept={TIPOS_DE_ARCHIVO_ACEPTADOS}
                aria-label="Documento de respaldo"
                onChange={(e) => setDocumento(e.target.files?.[0] ?? null)}
                style={{ display: 'block' }}
              />
            </label>
            <button type="submit" disabled={capturando}>
              {capturando ? 'Registrando…' : 'Registrar solicitud'}
            </button>
          </form>
        </details>
      )}

      <h3>Por decidir ({porDecidir.length})</h3>
      {loading ? (
        <p>Cargando…</p>
      ) : porDecidir.length === 0 ? (
        <p>No hay solicitudes por decidir.</p>
      ) : (
        <div style={{ display: 'grid', gap: 'var(--space-3)' }}>
          {porDecidir.map((a) => (
            <div key={a.id} style={tarjeta}>
              <div style={{ color: 'var(--ink-soft)' }}>
                {a.vivienda ?? '—'} · solicitado el {fecha(a.created_at)}
                {a.capturado_por_admin && ' · capturado por la administración'}
              </div>
              <p style={{ whiteSpace: 'pre-wrap' }}>{a.causa}</p>
              <p>
                Propone <strong>{a.propuesta_pagos === 1 ? 'pagar todo' : `${a.propuesta_pagos} pagos mensuales`}</strong> desde el{' '}
                <span className="mono">{a.propuesta_primer_pago}</span>.{' '}
                {a.archivo_url && (
                  <a href={a.archivo_url} target="_blank" rel="noreferrer">
                    Ver documento de respaldo
                  </a>
                )}
              </p>
              {a.incumplimientos_previos > 0 && (
                <p style={{ color: 'var(--brick)' }}>
                  Atención: esta vivienda ya incumplió {a.incumplimientos_previos}{' '}
                  {a.incumplimientos_previos === 1 ? 'acuerdo anterior' : 'acuerdos anteriores'}.
                </p>
              )}

              {puedeDecidir && (
                <div style={{ display: 'grid', gap: 'var(--space-2)' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                    <input
                      type="checkbox"
                      checked={congela[a.id] ?? true}
                      onChange={(e) => setCongela({ ...congela, [a.id]: e.target.checked })}
                    />
                    Congelar el recargo mientras se cumpla el acuerdo
                  </label>

                  {calendarioPropio[a.id] ? (
                    <div style={{ display: 'grid', gap: 'var(--space-2)' }}>
                      {calendarioPropio[a.id]!.map((fila, i) => (
                        <div key={i} style={{ display: 'flex', gap: 'var(--space-2)' }}>
                          <input
                            type="date"
                            aria-label={`Fecha del pago ${i + 1}`}
                            value={fila.fecha}
                            onChange={(e) =>
                              setCalendarioPropio({
                                ...calendarioPropio,
                                [a.id]: calendarioPropio[a.id]!.map((f, j) => (j === i ? { ...f, fecha: e.target.value } : f)),
                              })
                            }
                          />
                          <input
                            type="number"
                            step="0.01"
                            aria-label={`Monto del pago ${i + 1}`}
                            placeholder="Monto"
                            value={fila.monto}
                            onChange={(e) =>
                              setCalendarioPropio({
                                ...calendarioPropio,
                                [a.id]: calendarioPropio[a.id]!.map((f, j) => (j === i ? { ...f, monto: e.target.value } : f)),
                              })
                            }
                          />
                        </div>
                      ))}
                      <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
                        <button
                          type="button"
                          onClick={() =>
                            setCalendarioPropio({ ...calendarioPropio, [a.id]: [...calendarioPropio[a.id]!, { fecha: '', monto: '' }] })
                          }
                        >
                          Agregar pago
                        </button>
                        <button type="button" onClick={() => setCalendarioPropio({ ...calendarioPropio, [a.id]: undefined })}>
                          Usar el propuesto
                        </button>
                      </div>
                      <small style={{ color: 'var(--ink-soft)' }}>Los pagos deben sumar la deuda de la vivienda al aprobar.</small>
                    </div>
                  ) : (
                    <div>
                      <button type="button" onClick={() => setCalendarioPropio({ ...calendarioPropio, [a.id]: [{ fecha: '', monto: '' }] })}>
                        Proponer otro calendario
                      </button>
                    </div>
                  )}

                  <div style={{ display: 'flex', gap: 'var(--space-2)', flexWrap: 'wrap' }}>
                    <button onClick={() => handleAprobar(a)} disabled={trabajando === a.id}>
                      {trabajando === a.id ? 'Procesando…' : 'Aprobar acuerdo'}
                    </button>
                    {rechazando === a.id ? (
                      <>
                        <input placeholder="Motivo del rechazo" value={motivo} onChange={(e) => setMotivo(e.target.value)} />
                        <button onClick={() => handleRechazar(a.id)} disabled={motivo.trim() === '' || trabajando === a.id}>
                          Confirmar rechazo
                        </button>
                      </>
                    ) : (
                      <button onClick={() => setRechazando(a.id)} style={{ color: 'var(--brick)' }}>
                        Rechazar
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      <h3 style={{ marginTop: 'var(--space-4)' }}>Vigentes ({vigentes.length})</h3>
      {!loading &&
        (vigentes.length === 0 ? (
          <p>No hay acuerdos vigentes.</p>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
                <th>Vivienda</th>
                <th>Deuda acordada</th>
                <th>Abonado</th>
                <th>Falta</th>
                <th>Próximo pago</th>
                <th>Recargo</th>
                {puedeDecidir && <th />}
              </tr>
            </thead>
            <tbody>
              {vigentes.map((a) => (
                <tr key={a.id} style={{ borderBottom: '1px solid var(--border)' }}>
                  <td>{a.vivienda ?? '—'}</td>
                  <td className="mono">{money(a.deuda_inicial ?? 0)}</td>
                  <td className="mono">{money(a.abonado ?? 0)}</td>
                  <td className="mono">{money(a.pendiente_cubierto ?? 0)}</td>
                  <td className="mono">{a.proximo_pago ? `${money(a.proximo_pago.monto)} el ${a.proximo_pago.fecha}` : '—'}</td>
                  <td>{a.congela_recargo ? 'Congelado' : 'Sigue corriendo'}</td>
                  {puedeDecidir && (
                    <td>
                      <button onClick={() => handleCancelar(a)} disabled={trabajando === a.id}>
                        Cancelar acuerdo
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        ))}

      <h3 style={{ marginTop: 'var(--space-4)' }}>Historial</h3>
      {!loading &&
        (historial.length === 0 ? (
          <p>Todavía no hay acuerdos cerrados.</p>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
                <th>Vivienda</th>
                <th>Estado</th>
                <th>Solicitado</th>
                <th>Detalle</th>
              </tr>
            </thead>
            <tbody>
              {historial.map((a) => (
                <tr key={a.id} style={{ borderBottom: '1px solid var(--border)' }}>
                  <td>{a.vivienda ?? '—'}</td>
                  <td style={{ color: COLOR[a.estado] }}>{ETIQUETA[a.estado]}</td>
                  <td>{fecha(a.created_at)}</td>
                  <td>{a.estado === 'rechazado' ? a.motivo_rechazo : a.deuda_inicial !== null ? `Deuda acordada ${money(a.deuda_inicial)}` : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ))}
    </div>
  )
}
