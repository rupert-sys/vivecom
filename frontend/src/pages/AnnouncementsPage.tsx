import { Fragment, useEffect, useState, type FormEvent } from 'react'
import { createAnnouncement, getReadStatus, listAnnouncements, updateAnnouncement } from '../api/announcements'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import type { Announcement, ReadStatusEntry } from '../types'
import { dateToDatetimeLocalValue, datetimeLocalValueToUtcIso, utcNaiveToDate } from '../utils/dates'

export function AnnouncementsPage() {
  const { user } = useAuth()
  const isAdmin = user?.rol === 'admin'

  const [avisos, setAvisos] = useState<Announcement[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [titulo, setTitulo] = useState('')
  const [contenido, setContenido] = useState('')
  const [fechaPublicacion, setFechaPublicacion] = useState('')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [guardando, setGuardando] = useState(false)

  const [avisoParaLectura, setAvisoParaLectura] = useState<string | null>(null)
  const [lectura, setLectura] = useState<ReadStatusEntry[]>([])

  async function reload() {
    setLoading(true)
    try {
      setAvisos(await listAnnouncements())
      setError(null)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudieron cargar los avisos.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    reload()
  }, [])

  function limpiarFormulario() {
    setTitulo('')
    setContenido('')
    setFechaPublicacion('')
    setEditingId(null)
  }

  function editar(aviso: Announcement) {
    setEditingId(aviso.id)
    setTitulo(aviso.titulo)
    setContenido(aviso.contenido)
    setFechaPublicacion(dateToDatetimeLocalValue(utcNaiveToDate(aviso.fecha_publicacion)))
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setGuardando(true)
    try {
      const payload = {
        titulo,
        contenido,
        fecha_publicacion: fechaPublicacion ? datetimeLocalValueToUtcIso(fechaPublicacion) : undefined,
      }
      if (editingId) {
        await updateAnnouncement(editingId, payload)
      } else {
        await createAnnouncement(payload)
      }
      limpiarFormulario()
      await reload()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo guardar el aviso.')
    } finally {
      setGuardando(false)
    }
  }

  async function verLectura(avisoId: string) {
    if (avisoParaLectura === avisoId) {
      setAvisoParaLectura(null)
      return
    }
    try {
      setLectura(await getReadStatus(avisoId))
      setAvisoParaLectura(avisoId)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo cargar quién ha leído este aviso.')
    }
  }

  const ahora = new Date()

  return (
    <div>
      <h2>Avisos y circulares</h2>
      {error && <p style={{ color: 'var(--brick)' }}>{error}</p>}

      {isAdmin && (
        <div style={{ display: 'flex', gap: 'var(--space-4)', marginBottom: 'var(--space-4)', flexWrap: 'wrap' }}>
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)', flex: 1, minWidth: 280 }}>
            <h3>{editingId ? 'Editar aviso' : 'Nuevo aviso'}</h3>
            <input placeholder="Título" value={titulo} onChange={(e) => setTitulo(e.target.value)} required />
            <textarea
              placeholder="Contenido"
              value={contenido}
              onChange={(e) => setContenido(e.target.value)}
              required
              rows={5}
            />
            <label>
              Programar publicación (opcional — vacío = publicar de inmediato)
              <input
                type="datetime-local"
                aria-label="Fecha de publicación"
                value={fechaPublicacion}
                onChange={(e) => setFechaPublicacion(e.target.value)}
                style={{ display: 'block', width: '100%', marginTop: 4 }}
              />
            </label>
            <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
              <button type="submit" disabled={guardando}>
                {guardando ? 'Guardando…' : editingId ? 'Guardar cambios' : 'Publicar aviso'}
              </button>
              {editingId && (
                <button type="button" onClick={limpiarFormulario}>
                  Cancelar
                </button>
              )}
            </div>
          </form>

          <div style={{ flex: 1, minWidth: 280 }}>
            <h3>Vista previa</h3>
            <div
              style={{
                background: 'var(--surface)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius)',
                padding: 'var(--space-3)',
                borderLeft: '4px solid var(--dustblue)',
              }}
            >
              <h3 style={{ marginTop: 0 }}>{titulo || 'Título del aviso'}</h3>
              <p style={{ whiteSpace: 'pre-wrap' }}>{contenido || 'El contenido del aviso aparecerá aquí…'}</p>
            </div>
          </div>
        </div>
      )}

      {loading ? (
        <p>Cargando…</p>
      ) : avisos.length === 0 ? (
        <p>Todavía no hay avisos.</p>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
              <th>Título</th>
              <th>Publicación</th>
              <th>Estado</th>
              {isAdmin && <th />}
            </tr>
          </thead>
          <tbody>
            {avisos.map((aviso) => {
              const fechaPublicacionDate = utcNaiveToDate(aviso.fecha_publicacion)
              const programado = fechaPublicacionDate > ahora
              return (
                <Fragment key={aviso.id}>
                  <tr style={{ borderBottom: '1px solid var(--border)' }}>
                    <td>{aviso.titulo}</td>
                    <td className="mono">{fechaPublicacionDate.toLocaleString('es-MX')}</td>
                    <td style={{ color: programado ? 'var(--amber)' : 'var(--teal)' }}>
                      {programado ? 'Programado' : 'Publicado'}
                    </td>
                    {isAdmin && (
                      <td style={{ display: 'flex', gap: 'var(--space-2)' }}>
                        <button onClick={() => editar(aviso)}>Editar</button>
                        {!programado && <button onClick={() => verLectura(aviso.id)}>Ver lectura</button>}
                      </td>
                    )}
                  </tr>
                  {avisoParaLectura === aviso.id && (
                    <tr>
                      <td colSpan={4}>
                        <ul>
                          {lectura.map((entrada) => (
                            <li key={entrada.property_id}>
                              {entrada.identificador} —{' '}
                              <span style={{ color: entrada.leido ? 'var(--teal)' : 'var(--ink-soft)' }}>
                                {entrada.leido ? `Leído (${utcNaiveToDate(entrada.leido_at!).toLocaleString('es-MX')})` : 'No leído'}
                              </span>
                            </li>
                          ))}
                        </ul>
                      </td>
                    </tr>
                  )}
                </Fragment>
              )
            })}
          </tbody>
        </table>
      )}
    </div>
  )
}
