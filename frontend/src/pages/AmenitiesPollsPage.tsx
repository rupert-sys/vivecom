import { useEffect, useState, type FormEvent } from 'react'
import {
  addAmenityApprover,
  createAmenity,
  listAmenities,
  listAmenityApprovers,
  updateAmenity,
  type AmenityRulesInput,
} from '../api/amenities'
import { AmenityForm } from '../components/AmenityForm'
import { createPoll, listPolls } from '../api/polls'
import { createUser, listUsers } from '../api/users'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import type { Amenity, Poll, Rol, UserAccount } from '../types'

const ROLES: Rol[] = ['admin', 'tesorero', 'comite_lectura', 'comite_aprobador', 'vocero', 'residente', 'guardia']

export function AmenitiesPollsPage() {
  const { user } = useAuth()
  const isAdmin = user?.rol === 'admin'
  const puedeCrearVotaciones = user?.rol === 'admin' || user?.rol === 'vocero'

  const [amenities, setAmenities] = useState<Amenity[]>([])
  const [users, setUsers] = useState<UserAccount[]>([])
  const [polls, setPolls] = useState<Poll[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [creandoAmenidad, setCreandoAmenidad] = useState(false)
  const [amenidadEnEdicion, setAmenidadEnEdicion] = useState<string | null>(null)

  const [emailUsuario, setEmailUsuario] = useState('')
  const [passwordUsuario, setPasswordUsuario] = useState('')
  const [rolUsuario, setRolUsuario] = useState<Rol>('comite_aprobador')
  const [creandoUsuario, setCreandoUsuario] = useState(false)

  const [amenidadParaAprobador, setAmenidadParaAprobador] = useState('')
  const [aprobadores, setAprobadores] = useState<string[]>([])
  const [usuarioAprobador, setUsuarioAprobador] = useState('')
  const [asignandoAprobador, setAsignandoAprobador] = useState(false)

  const [pregunta, setPregunta] = useState('')
  const [opcionesTexto, setOpcionesTexto] = useState('')
  const [fechaCierre, setFechaCierre] = useState('')
  const [resultadosEnVivo, setResultadosEnVivo] = useState(false)
  const [creandoVotacion, setCreandoVotacion] = useState(false)

  async function reload() {
    setLoading(true)
    try {
      const [amenitiesResult, pollsResult] = await Promise.all([listAmenities(), listPolls()])
      setAmenities(amenitiesResult)
      setPolls(pollsResult)
      if (isAdmin) setUsers(await listUsers())
      setError(null)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo cargar amenidades y votaciones.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    reload()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!amenidadParaAprobador) {
      setAprobadores([])
      return
    }
    listAmenityApprovers(amenidadParaAprobador)
      .then(setAprobadores)
      .catch((err) => setError(err instanceof ApiError ? err.message : 'No se pudieron cargar los aprobadores.'))
  }, [amenidadParaAprobador])

  async function handleCreateAmenity(nombre: string, periodoLimiteHoras: number, reglas: AmenityRulesInput) {
    setCreandoAmenidad(true)
    try {
      await createAmenity(nombre, periodoLimiteHoras, reglas)
      setError(null)
      await reload()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo crear la amenidad.')
    } finally {
      setCreandoAmenidad(false)
    }
  }

  async function handleUpdateAmenity(id: string, nombre: string, periodoLimiteHoras: number, reglas: AmenityRulesInput) {
    setCreandoAmenidad(true)
    try {
      await updateAmenity(id, { nombre, periodo_limite_horas: periodoLimiteHoras, ...reglas })
      setAmenidadEnEdicion(null)
      setError(null)
      await reload()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo actualizar la amenidad.')
    } finally {
      setCreandoAmenidad(false)
    }
  }

  async function handleCreateUser(event: FormEvent) {
    event.preventDefault()
    setCreandoUsuario(true)
    try {
      await createUser({ email: emailUsuario, password: passwordUsuario, rol: rolUsuario })
      setEmailUsuario('')
      setPasswordUsuario('')
      await reload()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo crear la cuenta.')
    } finally {
      setCreandoUsuario(false)
    }
  }

  async function handleAssignApprover(event: FormEvent) {
    event.preventDefault()
    setAsignandoAprobador(true)
    try {
      await addAmenityApprover(amenidadParaAprobador, usuarioAprobador)
      setUsuarioAprobador('')
      setAprobadores(await listAmenityApprovers(amenidadParaAprobador))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo designar al aprobador.')
    } finally {
      setAsignandoAprobador(false)
    }
  }

  async function handleCreatePoll(event: FormEvent) {
    event.preventDefault()
    setCreandoVotacion(true)
    try {
      const opciones = opcionesTexto
        .split(',')
        .map((o) => o.trim())
        .filter(Boolean)
      await createPoll({ pregunta, opciones, fecha_cierre: fechaCierre, resultados_en_vivo: resultadosEnVivo })
      setPregunta('')
      setOpcionesTexto('')
      setFechaCierre('')
      setResultadosEnVivo(false)
      await reload()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo crear la votación.')
    } finally {
      setCreandoVotacion(false)
    }
  }

  const usuariosAprobadores = users.filter((u) => u.rol === 'comite_aprobador')

  return (
    <div>
      <h2>Amenidades y votaciones</h2>
      {error && <p style={{ color: 'var(--brick)' }}>{error}</p>}
      {loading && <p>Cargando…</p>}

      <h3>Amenidades</h3>
      {isAdmin && (
        <AmenityForm submitLabel="Agregar amenidad" busy={creandoAmenidad} onSubmit={handleCreateAmenity} />
      )}
      {amenities.length === 0 ? (
        <p>Todavía no hay amenidades configuradas.</p>
      ) : (
        <ul>
          {amenities.map((a) => (
            <li key={a.id} style={{ marginBottom: 'var(--space-2)' }}>
              {a.nombre} — límite de respuesta: <span className="mono">{a.periodo_limite_horas}h</span>
              {isAdmin && amenidadEnEdicion !== a.id && (
                <button onClick={() => setAmenidadEnEdicion(a.id)} style={{ marginLeft: 8 }}>
                  Editar reglas
                </button>
              )}
              {amenidadEnEdicion === a.id ? (
                <AmenityForm
                  inicial={a}
                  submitLabel="Guardar reglas"
                  busy={creandoAmenidad}
                  onSubmit={(nombre, horas, reglas) => handleUpdateAmenity(a.id, nombre, horas, reglas)}
                  onCancel={() => setAmenidadEnEdicion(null)}
                />
              ) : (
                a.reglas.length > 0 && (
                  <ul style={{ color: 'var(--ink-soft)' }}>
                    {a.reglas.map((regla) => (
                      <li key={regla}>{regla}</li>
                    ))}
                  </ul>
                )
              )}
            </li>
          ))}
        </ul>
      )}

      {isAdmin && (
        <>
          <h3>Cuentas de personal</h3>
          <p style={{ color: 'var(--ink-soft)' }}>
            Necesarias para poder designar aprobadores de amenidades (deben tener rol comité aprobador) o crear
            votaciones desde una cuenta de vocero.
          </p>
          <form onSubmit={handleCreateUser} style={{ display: 'flex', gap: 'var(--space-2)', flexWrap: 'wrap', margin: 'var(--space-3) 0' }}>
            <input type="email" placeholder="Email" value={emailUsuario} onChange={(e) => setEmailUsuario(e.target.value)} required />
            <input
              type="password"
              placeholder="Contraseña temporal"
              value={passwordUsuario}
              onChange={(e) => setPasswordUsuario(e.target.value)}
              required
            />
            <select value={rolUsuario} onChange={(e) => setRolUsuario(e.target.value as Rol)}>
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
            <button type="submit" disabled={creandoUsuario}>
              {creandoUsuario ? 'Creando…' : 'Crear cuenta'}
            </button>
          </form>
          {users.length === 0 ? (
            <p>Todavía no hay cuentas de personal creadas.</p>
          ) : (
            <ul>
              {users.map((u) => (
                <li key={u.id}>
                  {u.email} — <span className="mono">{u.rol}</span>
                </li>
              ))}
            </ul>
          )}

          <h3>Aprobadores por amenidad</h3>
          <div style={{ display: 'flex', gap: 'var(--space-2)', marginBottom: 'var(--space-2)' }}>
            <select value={amenidadParaAprobador} onChange={(e) => setAmenidadParaAprobador(e.target.value)}>
              <option value="">Elige una amenidad…</option>
              {amenities.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.nombre}
                </option>
              ))}
            </select>
          </div>
          {amenidadParaAprobador && (
            <>
              {aprobadores.length === 0 ? (
                <p>Esta amenidad todavía no tiene aprobadores designados.</p>
              ) : (
                <ul>
                  {aprobadores.map((userId) => {
                    const cuenta = users.find((u) => u.id === userId)
                    return <li key={userId}>{cuenta ? cuenta.email : userId}</li>
                  })}
                </ul>
              )}
              <form onSubmit={handleAssignApprover} style={{ display: 'flex', gap: 'var(--space-2)' }}>
                <select value={usuarioAprobador} onChange={(e) => setUsuarioAprobador(e.target.value)} required>
                  <option value="">Elige un usuario con rol comité aprobador…</option>
                  {usuariosAprobadores.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.email}
                    </option>
                  ))}
                </select>
                <button type="submit" disabled={asignandoAprobador || !usuarioAprobador}>
                  {asignandoAprobador ? 'Asignando…' : 'Designar aprobador'}
                </button>
              </form>
            </>
          )}
        </>
      )}

      <h3>Votaciones</h3>
      {puedeCrearVotaciones && (
        <form onSubmit={handleCreatePoll} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)', maxWidth: 420, margin: 'var(--space-3) 0' }}>
          <input placeholder="Pregunta" value={pregunta} onChange={(e) => setPregunta(e.target.value)} required />
          <input
            placeholder="Opciones separadas por coma (mínimo 2)"
            value={opcionesTexto}
            onChange={(e) => setOpcionesTexto(e.target.value)}
            required
          />
          <input type="date" aria-label="Fecha de cierre" value={fechaCierre} onChange={(e) => setFechaCierre(e.target.value)} required />
          <label style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <input type="checkbox" checked={resultadosEnVivo} onChange={(e) => setResultadosEnVivo(e.target.checked)} />
            Mostrar resultados en vivo
          </label>
          <button type="submit" disabled={creandoVotacion}>
            {creandoVotacion ? 'Creando…' : 'Crear votación'}
          </button>
        </form>
      )}
      {polls.length === 0 ? (
        <p>Todavía no hay votaciones creadas.</p>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
              <th>Pregunta</th>
              <th>Cierra</th>
              <th>Opciones</th>
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            {polls.map((poll) => (
              <tr key={poll.id} style={{ borderBottom: '1px solid var(--border)' }}>
                <td>{poll.pregunta}</td>
                <td className="mono">{poll.fecha_cierre}</td>
                <td>{poll.opciones.map((o) => o.texto).join(', ')}</td>
                <td style={{ color: poll.quorum_alcanzado ? 'var(--teal)' : 'var(--amber)' }}>
                  {poll.quorum_alcanzado ? 'Quorum alcanzado' : poll.reactivada ? 'Reactivada' : 'Abierta'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
