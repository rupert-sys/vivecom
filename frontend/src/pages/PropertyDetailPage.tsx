import { useEffect, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  listPropertyResidents,
  linkResidentToProperty,
  unlinkResidentFromProperty,
  updateProperty,
} from '../api/properties'
import { createResident } from '../api/residents'
import { createManualPayment, getAccountStatement, type MetodoPagoManual } from '../api/payments'
import { getReglamento } from '../api/reglamento'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import type { AccountStatement, Reglamento, Resident, RolOcupacion } from '../types'

export function PropertyDetailPage() {
  const { propertyId } = useParams<{ propertyId: string }>()
  const { user } = useAuth()
  const isAdmin = user?.rol === 'admin'
  // El estado de cuenta y el registro de pagos son de tesorería (y del administrador).
  const puedeVerCuenta = user?.rol === 'admin' || user?.rol === 'tesorero'

  const [residents, setResidents] = useState<Resident[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [nombre, setNombre] = useState('')
  const [telefono, setTelefono] = useState('')
  const [email, setEmail] = useState('')
  const [rol, setRol] = useState<RolOcupacion>('propietario')
  const [creating, setCreating] = useState(false)

  const [estadoDeCuenta, setEstadoDeCuenta] = useState<AccountStatement | null>(null)
  const [reglamento, setReglamento] = useState<Reglamento | null>(null)
  const [montoPago, setMontoPago] = useState('')
  const [metodoPago, setMetodoPago] = useState<MetodoPagoManual>('transferencia')
  const [registrandoPago, setRegistrandoPago] = useState(false)
  const [pagoRegistrado, setPagoRegistrado] = useState(false)

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

  // El estado de cuenta es un complemento: si falla, el resto de la vivienda sigue usable.
  async function reloadCuenta() {
    if (!propertyId || !puedeVerCuenta) return
    setEstadoDeCuenta(await getAccountStatement(propertyId).catch(() => null))
  }

  useEffect(() => {
    reload()
    reloadCuenta()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [propertyId])

  useEffect(() => {
    if (!puedeVerCuenta) return
    getReglamento()
      .then(setReglamento)
      .catch(() => setReglamento(null))
  }, [puedeVerCuenta])

  async function handleRegistrarPago(event: FormEvent) {
    event.preventDefault()
    if (!propertyId) return
    setRegistrandoPago(true)
    setPagoRegistrado(false)
    try {
      await createManualPayment(propertyId, Number(montoPago), metodoPago)
      setMontoPago('')
      setPagoRegistrado(true)
      setError(null)
      await reloadCuenta()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo registrar el pago.')
    } finally {
      setRegistrandoPago(false)
    }
  }

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

      {puedeVerCuenta && estadoDeCuenta && (
        <section
          style={{
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius)',
            padding: 'var(--space-3)',
            margin: 'var(--space-3) 0',
          }}
        >
          <h3>Estado de cuenta</h3>
          <p>
            Deuda: <span className="mono">${estadoDeCuenta.deuda_total.toFixed(2)}</span> — Saldo a favor:{' '}
            <span className="mono">${estadoDeCuenta.saldo_a_favor.toFixed(2)}</span>
          </p>
          {estadoDeCuenta.en_mora && (
            <div style={{ color: 'var(--brick)' }}>
              <strong>Vivienda en mora.</strong>
              {estadoDeCuenta.restricciones_por_mora.length > 0 && (
                <ul>
                  {estadoDeCuenta.restricciones_por_mora.map((r) => (
                    <li key={r}>{r}</li>
                  ))}
                </ul>
              )}
            </div>
          )}

          <h4>Registrar un pago</h4>
          <p style={{ color: 'var(--ink-soft)' }}>
            Para un pago que no llegó por SPEI{reglamento?.acepta_pago_efectivo ? ' o en efectivo' : ''}. Se aplica a la
            deuda más antigua y el residente puede descargar su recibo.
          </p>
          {pagoRegistrado && <p style={{ color: 'var(--teal)' }}>Pago registrado.</p>}
          <form onSubmit={handleRegistrarPago} style={{ display: 'flex', gap: 'var(--space-2)', flexWrap: 'wrap' }}>
            <input
              type="number"
              step="0.01"
              min="0.01"
              placeholder="Monto del pago"
              value={montoPago}
              onChange={(e) => setMontoPago(e.target.value)}
              required
            />
            <select
              aria-label="Forma de pago"
              value={metodoPago}
              onChange={(e) => setMetodoPago(e.target.value as MetodoPagoManual)}
            >
              <option value="transferencia">Transferencia</option>
              {reglamento?.acepta_pago_efectivo && <option value="efectivo">Efectivo</option>}
            </select>
            <button type="submit" disabled={registrandoPago}>
              {registrandoPago ? 'Registrando…' : 'Registrar pago'}
            </button>
          </form>
        </section>
      )}

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
