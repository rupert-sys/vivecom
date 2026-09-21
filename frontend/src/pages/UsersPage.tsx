import { useEffect, useState, type FormEvent } from 'react'
import { ApiError } from '../api/client'
import { listProperties } from '../api/properties'
import { createUser, deleteUser, listUsers, updateUser, type UserAccountChanges } from '../api/users'
import { useAuth } from '../auth/AuthContext'
import type { Property, Rol, UserAccount } from '../types'

const ROLES: { valor: Rol; etiqueta: string }[] = [
  { valor: 'admin', etiqueta: 'Administrador' },
  { valor: 'tesorero', etiqueta: 'Tesorero' },
  { valor: 'comite_aprobador', etiqueta: 'Comité (aprueba)' },
  { valor: 'comite_lectura', etiqueta: 'Comité (solo lectura)' },
  { valor: 'vocero', etiqueta: 'Vocero' },
  { valor: 'guardia', etiqueta: 'Guardia' },
  { valor: 'residente', etiqueta: 'Residente' },
]
const etiquetaDe = (rol: Rol) => ROLES.find((r) => r.valor === rol)?.etiqueta ?? rol

interface Borrador {
  email: string
  password: string
  rol: Rol
  propertyId: string
}

function SelectorDeRol({ valor, onChange }: { valor: Rol; onChange: (rol: Rol) => void }) {
  return (
    <select aria-label="Rol" value={valor} onChange={(e) => onChange(e.target.value as Rol)}>
      {ROLES.map((r) => (
        <option key={r.valor} value={r.valor}>
          {r.etiqueta}
        </option>
      ))}
    </select>
  )
}

function SelectorDeVivienda({
  valor,
  viviendas,
  onChange,
}: {
  valor: string
  viviendas: Property[]
  onChange: (id: string) => void
}) {
  return (
    <select aria-label="Vivienda" value={valor} onChange={(e) => onChange(e.target.value)}>
      <option value="">— sin vivienda —</option>
      {viviendas.map((v) => (
        <option key={v.id} value={v.id}>
          {v.identificador}
        </option>
      ))}
    </select>
  )
}

export function UsersPage() {
  const { user } = useAuth()
  const isAdmin = user?.rol === 'admin'

  const [usuarios, setUsuarios] = useState<UserAccount[]>([])
  const [viviendas, setViviendas] = useState<Property[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [aviso, setAviso] = useState<string | null>(null)

  const [nuevo, setNuevo] = useState<Borrador>({ email: '', password: '', rol: 'residente', propertyId: '' })
  const [creando, setCreando] = useState(false)

  const [editandoId, setEditandoId] = useState<string | null>(null)
  const [edicion, setEdicion] = useState<Borrador>({ email: '', password: '', rol: 'residente', propertyId: '' })
  const [guardando, setGuardando] = useState(false)

  async function reload() {
    setLoading(true)
    try {
      const [cuentas, casas] = await Promise.all([listUsers(), listProperties()])
      setUsuarios(cuentas)
      setViviendas(casas)
      setError(null)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudieron cargar los usuarios.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!isAdmin) return
    // eslint-disable-next-line react-hooks/set-state-in-effect
    reload()
  }, [isAdmin])

  const viviendaDe = (id?: string | null) => viviendas.find((v) => v.id === id)?.identificador ?? '—'

  async function handleCreate(event: FormEvent) {
    event.preventDefault()
    setCreando(true)
    setAviso(null)
    try {
      await createUser({
        email: nuevo.email,
        password: nuevo.password,
        rol: nuevo.rol,
        property_id: nuevo.propertyId || null,
      })
      setNuevo({ email: '', password: '', rol: 'residente', propertyId: '' })
      setAviso('Cuenta creada. Compártele su contraseña temporal por fuera de la app.')
      await reload()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo crear la cuenta.')
    } finally {
      setCreando(false)
    }
  }

  function empezarEdicion(cuenta: UserAccount) {
    setEditandoId(cuenta.id)
    setEdicion({ email: cuenta.email, password: '', rol: cuenta.rol, propertyId: cuenta.property_id ?? '' })
    setAviso(null)
    setError(null)
  }

  async function handleSave(event: FormEvent, original: UserAccount) {
    event.preventDefault()
    // Solo se manda lo que cambió: así no se pisa nada y una contraseña vacía significa «no cambiarla».
    const cambios: UserAccountChanges = {}
    if (edicion.email !== original.email) cambios.email = edicion.email
    if (edicion.password) cambios.password = edicion.password
    if (edicion.rol !== original.rol) cambios.rol = edicion.rol
    if (edicion.propertyId !== (original.property_id ?? '')) cambios.property_id = edicion.propertyId || null
    if (Object.keys(cambios).length === 0) {
      setEditandoId(null)
      return
    }
    setGuardando(true)
    try {
      await updateUser(original.id, cambios)
      setEditandoId(null)
      setError(null)
      setAviso(cambios.password ? 'Cuenta actualizada. La contraseña nueva rige desde el próximo inicio de sesión.' : 'Cuenta actualizada.')
      await reload()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo guardar la cuenta.')
    } finally {
      setGuardando(false)
    }
  }

  async function handleDelete(cuenta: UserAccount) {
    if (!window.confirm(`¿Eliminar la cuenta ${cuenta.email}? Ya no podrá iniciar sesión.`)) return
    setAviso(null)
    try {
      await deleteUser(cuenta.id)
      setAviso('Cuenta eliminada.')
      await reload()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo eliminar la cuenta.')
    }
  }

  if (!isAdmin) return <p>Solo el administrador puede gestionar las cuentas de usuario.</p>

  return (
    <div>
      <h2>Usuarios</h2>
      {error && <p style={{ color: 'var(--brick)' }}>{error}</p>}
      {aviso && <p style={{ color: 'var(--ink-soft)' }}>{aviso}</p>}

      <form
        onSubmit={handleCreate}
        aria-label="Nueva cuenta"
        style={{ display: 'flex', gap: 'var(--space-2)', flexWrap: 'wrap', margin: 'var(--space-3) 0' }}
      >
        <input
          type="email"
          placeholder="Correo"
          value={nuevo.email}
          onChange={(e) => setNuevo({ ...nuevo, email: e.target.value })}
          required
        />
        <input
          type="text"
          placeholder="Contraseña temporal (mín. 8)"
          value={nuevo.password}
          onChange={(e) => setNuevo({ ...nuevo, password: e.target.value })}
          minLength={8}
          required
        />
        <SelectorDeRol valor={nuevo.rol} onChange={(rol) => setNuevo({ ...nuevo, rol })} />
        {nuevo.rol === 'residente' && (
          <SelectorDeVivienda
            valor={nuevo.propertyId}
            viviendas={viviendas}
            onChange={(propertyId) => setNuevo({ ...nuevo, propertyId })}
          />
        )}
        <button type="submit" disabled={creando}>
          {creando ? 'Creando…' : 'Agregar cuenta'}
        </button>
      </form>

      {loading ? (
        <p>Cargando…</p>
      ) : usuarios.length === 0 ? (
        <p>Todavía no hay cuentas.</p>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
              <th>Correo</th>
              <th>Rol</th>
              <th>Vivienda</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {usuarios.map((cuenta) =>
              editandoId === cuenta.id ? (
                <tr key={cuenta.id} style={{ borderBottom: '1px solid var(--border)' }}>
                  <td colSpan={4}>
                    <form
                      onSubmit={(e) => handleSave(e, cuenta)}
                      aria-label={`Editar ${cuenta.email}`}
                      style={{ display: 'flex', gap: 'var(--space-2)', flexWrap: 'wrap', padding: 'var(--space-2) 0' }}
                    >
                      <input
                        type="email"
                        aria-label="Correo"
                        value={edicion.email}
                        onChange={(e) => setEdicion({ ...edicion, email: e.target.value })}
                        required
                      />
                      <input
                        type="text"
                        aria-label="Contraseña nueva"
                        placeholder="Contraseña nueva (opcional)"
                        value={edicion.password}
                        onChange={(e) => setEdicion({ ...edicion, password: e.target.value })}
                        minLength={8}
                      />
                      <SelectorDeRol valor={edicion.rol} onChange={(rol) => setEdicion({ ...edicion, rol })} />
                      <SelectorDeVivienda
                        valor={edicion.propertyId}
                        viviendas={viviendas}
                        onChange={(propertyId) => setEdicion({ ...edicion, propertyId })}
                      />
                      <button type="submit" disabled={guardando}>
                        {guardando ? 'Guardando…' : 'Guardar'}
                      </button>
                      <button type="button" onClick={() => setEditandoId(null)}>
                        Cancelar
                      </button>
                    </form>
                  </td>
                </tr>
              ) : (
                <tr key={cuenta.id} style={{ borderBottom: '1px solid var(--border)' }}>
                  <td>{cuenta.email}</td>
                  <td>{etiquetaDe(cuenta.rol)}</td>
                  <td>{viviendaDe(cuenta.property_id)}</td>
                  <td style={{ whiteSpace: 'nowrap' }}>
                    <button onClick={() => empezarEdicion(cuenta)} aria-label={`Editar ${cuenta.email}`}>
                      Editar
                    </button>{' '}
                    <button
                      onClick={() => handleDelete(cuenta)}
                      aria-label={`Eliminar ${cuenta.email}`}
                      style={{ color: 'var(--brick)' }}
                    >
                      Eliminar
                    </button>
                  </td>
                </tr>
              ),
            )}
          </tbody>
        </table>
      )}
    </div>
  )
}
