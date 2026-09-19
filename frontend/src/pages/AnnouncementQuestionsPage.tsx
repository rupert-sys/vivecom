import { useEffect, useState } from 'react'
import { answerQuestion, listAnsweredQuestions, listPendingQuestions, updateQuestion } from '../api/announcementQuestions'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import type { AnnouncementQuestion } from '../types'

const ROLES_QUE_VEN = new Set(['admin', 'comite_lectura', 'comite_aprobador'])
// El comité de solo lectura ve las dudas pero no responde.
const ROLES_QUE_RESPONDEN = new Set(['admin', 'comite_aprobador'])

function fecha(iso: string): string {
  // UTC "naive" del backend: se interpreta como UTC, no como hora local del navegador.
  return new Date(iso.endsWith('Z') ? iso : `${iso}Z`).toLocaleString('es-MX')
}

// Dudas que los residentes mandan sobre un aviso. Llegan solo aquí (administración y comité); una
// pregunta recibe una respuesta, y se puede publicar como aclaración para todos, sin nombre ni vivienda,
// para que los demás no vuelvan a preguntar lo mismo.
export function AnnouncementQuestionsPage() {
  const { user } = useAuth()
  const tieneAcceso = user !== null && ROLES_QUE_VEN.has(user.rol)
  const puedeResponder = user !== null && ROLES_QUE_RESPONDEN.has(user.rol)

  const [pendientes, setPendientes] = useState<AnnouncementQuestion[]>([])
  const [respondidas, setRespondidas] = useState<AnnouncementQuestion[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [respuestas, setRespuestas] = useState<Record<string, string>>({})
  const [publicar, setPublicar] = useState<Record<string, boolean>>({})
  const [trabajando, setTrabajando] = useState<string | null>(null)

  async function reload() {
    setLoading(true)
    try {
      const [p, r] = await Promise.all([listPendingQuestions(), listAnsweredQuestions()])
      setPendientes(p)
      setRespondidas(r)
      setError(null)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudieron cargar las dudas.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (tieneAcceso) reload()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tieneAcceso])

  async function handleResponder(duda: AnnouncementQuestion) {
    const respuesta = (respuestas[duda.id] ?? '').trim()
    if (respuesta === '') return
    setTrabajando(duda.id)
    try {
      await answerQuestion(duda.id, respuesta, publicar[duda.id] === true)
      setError(null)
      await reload()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo enviar la respuesta.')
    } finally {
      setTrabajando(null)
    }
  }

  async function handleAlternarAclaracion(duda: AnnouncementQuestion) {
    setTrabajando(duda.id)
    try {
      await updateQuestion(duda.id, { publica: !duda.publica })
      setError(null)
      await reload()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo cambiar la aclaración.')
    } finally {
      setTrabajando(null)
    }
  }

  if (!tieneAcceso) {
    return (
      <div>
        <h2>Dudas de los residentes</h2>
        <p>No tienes acceso a esta vista — solo administradores y comité.</p>
      </div>
    )
  }

  return (
    <div>
      <h2>Dudas de los residentes</h2>
      <p style={{ color: 'var(--ink-soft)' }}>
        Las dudas que los residentes mandan sobre un aviso llegan solo aquí. Al responder puedes publicarla como
        aclaración: la ven todos debajo del aviso, sin nombre ni vivienda.
        {!puedeResponder && ' Tu rol es de solo lectura: no puedes responder.'}
      </p>
      {error && <p style={{ color: 'var(--brick)' }}>{error}</p>}

      <h3>Por responder ({pendientes.length})</h3>
      {loading ? (
        <p>Cargando…</p>
      ) : pendientes.length === 0 ? (
        <p>No hay dudas por responder.</p>
      ) : (
        <div style={{ display: 'grid', gap: 'var(--space-3)' }}>
          {pendientes.map((d) => (
            <div
              key={d.id}
              style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: 'var(--space-3)' }}
            >
              <div style={{ color: 'var(--ink-soft)' }}>
                {d.vivienda ?? '—'} · {d.aviso_titulo ?? 'Aviso'} · {fecha(d.created_at)}
              </div>
              <p style={{ whiteSpace: 'pre-wrap' }}>{d.texto}</p>
              {puedeResponder && (
                <div style={{ display: 'grid', gap: 'var(--space-2)' }}>
                  <textarea
                    rows={3}
                    maxLength={1000}
                    aria-label={`Respuesta para ${d.vivienda ?? 'la duda'}`}
                    placeholder="Escribe la respuesta"
                    value={respuestas[d.id] ?? ''}
                    onChange={(e) => setRespuestas({ ...respuestas, [d.id]: e.target.value })}
                  />
                  <label style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                    <input
                      type="checkbox"
                      checked={publicar[d.id] === true}
                      onChange={(e) => setPublicar({ ...publicar, [d.id]: e.target.checked })}
                    />
                    Publicar como aclaración (sin nombre ni vivienda)
                  </label>
                  <div>
                    <button
                      onClick={() => handleResponder(d)}
                      disabled={trabajando === d.id || (respuestas[d.id] ?? '').trim() === ''}
                    >
                      {trabajando === d.id ? 'Enviando…' : 'Responder'}
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      <h3 style={{ marginTop: 'var(--space-4)' }}>Respondidas</h3>
      {!loading &&
        (respondidas.length === 0 ? (
          <p>Todavía no hay dudas respondidas.</p>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
                <th>Vivienda</th>
                <th>Aviso</th>
                <th>Duda</th>
                <th>Respuesta</th>
                <th>Aclaración</th>
              </tr>
            </thead>
            <tbody>
              {respondidas.map((d) => (
                <tr key={d.id} style={{ borderBottom: '1px solid var(--border)', verticalAlign: 'top' }}>
                  <td>{d.vivienda ?? '—'}</td>
                  <td>{d.aviso_titulo ?? '—'}</td>
                  <td>{d.texto}</td>
                  <td>{d.respuesta}</td>
                  <td>
                    <span style={{ color: d.publica ? 'var(--teal)' : 'var(--ink-soft)' }}>
                      {d.publica ? 'Publicada' : 'Privada'}
                    </span>
                    {puedeResponder && (
                      <div>
                        <button onClick={() => handleAlternarAclaracion(d)} disabled={trabajando === d.id}>
                          {d.publica ? 'Retirar aclaración' : 'Publicar como aclaración'}
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ))}
    </div>
  )
}
