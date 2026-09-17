import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { createProperty, deleteProperty, listProperties } from '../api/properties'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import type { Property } from '../types'

export function PropertiesPage() {
  const { user } = useAuth()
  const isAdmin = user?.rol === 'admin'

  const [properties, setProperties] = useState<Property[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [nuevoIdentificador, setNuevoIdentificador] = useState('')
  const [creating, setCreating] = useState(false)

  async function reload() {
    setLoading(true)
    try {
      setProperties(await listProperties())
      setError(null)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudieron cargar las viviendas.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    reload()
  }, [])

  async function handleCreate(event: FormEvent) {
    event.preventDefault()
    setCreating(true)
    try {
      await createProperty(nuevoIdentificador)
      setNuevoIdentificador('')
      await reload()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo crear la vivienda.')
    } finally {
      setCreating(false)
    }
  }

  async function handleDelete(id: string) {
    if (!window.confirm('¿Eliminar esta vivienda? Esta acción no se puede deshacer.')) return
    try {
      await deleteProperty(id)
      await reload()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo eliminar la vivienda.')
    }
  }

  return (
    <div>
      <h2>Viviendas</h2>
      {error && <p style={{ color: 'var(--brick)' }}>{error}</p>}

      {isAdmin && (
        <form onSubmit={handleCreate} style={{ display: 'flex', gap: 'var(--space-2)', margin: 'var(--space-3) 0' }}>
          <input
            placeholder="Identificador (ej. Casa 12)"
            value={nuevoIdentificador}
            onChange={(e) => setNuevoIdentificador(e.target.value)}
            required
          />
          <button type="submit" disabled={creating}>
            {creating ? 'Creando…' : 'Agregar vivienda'}
          </button>
        </form>
      )}

      {loading ? (
        <p>Cargando…</p>
      ) : properties.length === 0 ? (
        <p>Todavía no hay viviendas registradas.</p>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
              <th>Identificador</th>
              <th>Referencia de pago</th>
              <th>Saldo a favor</th>
              {isAdmin && <th />}
            </tr>
          </thead>
          <tbody>
            {properties.map((p) => (
              <tr key={p.id} style={{ borderBottom: '1px solid var(--border)' }}>
                <td>
                  <Link to={`/properties/${p.id}`}>{p.identificador}</Link>
                </td>
                <td className="mono">{p.referencia_pago}</td>
                <td className="mono">${p.saldo_a_favor.toFixed(2)}</td>
                {isAdmin && (
                  <td>
                    <button onClick={() => handleDelete(p.id)} style={{ color: 'var(--brick)' }}>
                      Eliminar
                    </button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
