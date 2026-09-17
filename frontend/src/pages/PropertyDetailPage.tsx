import { useEffect, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  listPropertyResidents,
  linkResidentToProperty,
  unlinkResidentFromProperty,
  updateProperty,
} from '../api/properties'
import { createResident } from '../api/residents'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import type { Resident, RolOcupacion } from '../types'

export function PropertyDetailPage() {
  const { propertyId } = useParams<{ propertyId: string }>()
  const { user } = useAuth()
  const isAdmin = user?.rol === 'admin'

  const [residents, setResidents] = useState<Resident[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [nombre, setNombre] = useState('')
  const [telefono, setTelefono] = useState('')
  const [email, setEmail] = useState('')
  const [rol, setRol] = useState<RolOcupacion>('propietario')
  const [creating, setCreating] = useState(false)

  const [editingIdentificador, setEditingIdentificador] = useState(false)
  const [identificador, setIdentificador] = useState('')

  async function reload() {
    if (!propertyId) return
    setLoading(true)
    try {
      setResidents(await listPropertyResidents(propertyId))
      setError(null)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudieron cargar los residentes.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    reload()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [propertyId])

  async function handleAddResident(event: FormEvent) {
    event.preventDefault()
    if (!propertyId) return
    setCreating(true)
    try {
      const resident = await createResident({ nombre, telefono, email: email || undefined })
      await linkResidentToProperty(propertyId, resident.id, rol)
      setNombre('')
      setTelefono('')
      setEmail('')
      await reload()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo agregar al residente.')
    } finally {
      setCreating(false)
    }
  }

  async function handleUnlink(residentId: string) {
    if (!propertyId) return
    if (!window.confirm('¿Quitar a este residente de la vivienda?')) return
    try {
      await unlinkResidentFromProperty(propertyId, residentId)
      await reload()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo quitar al residente.')
    }
  }

  async function handleSaveIdentificador(event: FormEvent) {
    event.preventDefault()
    if (!propertyId) return
    try {
      await updateProperty(propertyId, identificador)
      setEditingIdentificador(false)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo actualizar la vivienda.')
    }
  }

  return (
    <div>
      <p>
        <Link to="/properties">← Viviendas</Link>
      </p>
      <h2>Residentes de la vivienda</h2>
      {error && <p style={{ color: 'var(--brick)' }}>{error}</p>}

      {isAdmin &&
        (editingIdentificador ? (
          <form onSubmit={handleSaveIdentificador} style={{ display: 'flex', gap: 'var(--space-2)' }}>
            <input value={identificador} onChange={(e) => setIdentificador(e.target.value)} required />
            <button type="submit">Guardar</button>
          </form>
        ) : (
          <button onClick={() => setEditingIdentificador(true)}>Editar identificador</button>
        ))}

      {loading ? (
        <p>Cargando…</p>
      ) : residents.length === 0 ? (
        <p>Esta vivienda todavía no tiene residentes registrados.</p>
      ) : (
        <ul>
          {residents.map((r) => (
            <li key={r.id}>
              {r.nombre} — <span className="mono">{r.telefono}</span>
              {r.email && ` — ${r.email}`}
              {isAdmin && (
                <button onClick={() => handleUnlink(r.id)} style={{ marginLeft: 8, color: 'var(--brick)' }}>
                  Quitar
                </button>
              )}
            </li>
          ))}
        </ul>
      )}

      {isAdmin && (
        <>
          <h3>Agregar residente</h3>
          <form onSubmit={handleAddResident} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)', maxWidth: 320 }}>
            <input placeholder="Nombre" value={nombre} onChange={(e) => setNombre(e.target.value)} required />
            <input placeholder="Teléfono" value={telefono} onChange={(e) => setTelefono(e.target.value)} required />
            <input placeholder="Email (opcional)" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
            <select value={rol} onChange={(e) => setRol(e.target.value as RolOcupacion)}>
              <option value="propietario">Propietario</option>
              <option value="inquilino">Inquilino</option>
            </select>
            <button type="submit" disabled={creating}>
              {creating ? 'Agregando…' : 'Agregar'}
            </button>
          </form>
        </>
      )}
    </div>
  )
}
