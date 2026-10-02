import { useEffect, useState, type FormEvent } from 'react'
import { createCashMovement, getCashBalance, listCashMovements } from '../api/cashMovements'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { StatCard } from '../components/StatCard'
import type { CashBalance, CashMovement, TipoCaja, TipoMovimientoCaja } from '../types'
import { rolesDe } from '../permisos'

const ROLES_CON_ACCESO = new Set<string>(rolesDe('/caja'))

const ETIQUETA_CAJA: Record<TipoCaja, string> = { chica: 'Caja chica', grande: 'Caja grande' }

function money(valor: number): string {
  return `$${Math.round(valor).toLocaleString('es-MX')}`
}

function fechaLegible(iso: string): string {
  return new Date(`${iso}T00:00:00`).toLocaleDateString('es-MX')
}

// F0-12: caja chica y caja grande — efectivo físico que administra tesorería, con historial de movimientos
// (a diferencia del dinero en la cuenta bancaria del condominio, que ya se ve en Cuotas/Cobranza). El saldo
// de cada caja se calcula del historial, nunca se captura aparte.
export function CashMovementsPage() {
  const { user } = useAuth()
  const tieneAcceso = user !== null && ROLES_CON_ACCESO.has(user.rol)
  const esTesorero = user?.rol === 'tesorero'

  const [saldo, setSaldo] = useState<CashBalance | null>(null)
  const [movimientos, setMovimientos] = useState<CashMovement[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [caja, setCaja] = useState<TipoCaja>('chica')
  const [tipo, setTipo] = useState<TipoMovimientoCaja>('ingreso')
  const [monto, setMonto] = useState('')
  const [motivo, setMotivo] = useState('')
  const [fecha, setFecha] = useState(() => new Date().toISOString().slice(0, 10))
  const [guardando, setGuardando] = useState(false)

  async function reload() {
    setLoading(true)
    try {
      const [s, m] = await Promise.all([getCashBalance(), listCashMovements()])
      setSaldo(s)
      setMovimientos(m)
      setError(null)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo cargar la caja.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (tieneAcceso) reload()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tieneAcceso])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setGuardando(true)
    try {
      await createCashMovement({ caja, tipo, monto: Number(monto), motivo: motivo.trim(), fecha })
      setMonto('')
      setMotivo('')
      await reload()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo registrar el movimiento.')
    } finally {
      setGuardando(false)
    }
  }

  if (!tieneAcceso) {
    return (
      <div>
        <h2>Caja chica y caja grande</h2>
        <p>No tienes acceso a esta vista.</p>
      </div>
    )
  }

  return (
    <div>
      <h2>Caja chica y caja grande</h2>
      {error && <p style={{ color: 'var(--brick)' }}>{error}</p>}

      {saldo && (
        <div role="group" aria-label="Saldo de caja" style={{ display: 'flex', gap: 'var(--space-3)', margin: 'var(--space-3) 0', flexWrap: 'wrap' }}>
          <StatCard label="Caja chica" color="var(--teal)" tint="var(--teal-tint)">
            {money(saldo.chica)}
          </StatCard>
          <StatCard label="Caja grande" color="var(--dustblue)" tint="var(--dustblue-tint)">
            {money(saldo.grande)}
          </StatCard>
        </div>
      )}

      {esTesorero && (
        <form onSubmit={handleSubmit} style={{ display: 'grid', gap: 'var(--space-2)', maxWidth: 420, margin: 'var(--space-3) 0' }}>
          <label>
            Caja
            <select value={caja} onChange={(e) => setCaja(e.target.value as TipoCaja)} style={{ display: 'block', width: '100%' }}>
              <option value="chica">Caja chica</option>
              <option value="grande">Caja grande</option>
            </select>
          </label>
          <label>
            Movimiento
            <select value={tipo} onChange={(e) => setTipo(e.target.value as TipoMovimientoCaja)} style={{ display: 'block', width: '100%' }}>
              <option value="ingreso">Ingreso (entra dinero)</option>
              <option value="egreso">Egreso (sale dinero)</option>
            </select>
          </label>
          <label>
            Monto
            <input
              type="number" min="0.01" step="0.01" required value={monto}
              onChange={(e) => setMonto(e.target.value)} style={{ display: 'block', width: '100%' }}
            />
          </label>
          <label>
            Motivo
            <input
              type="text" required minLength={1} value={motivo}
              onChange={(e) => setMotivo(e.target.value)} placeholder="Ej. Compra de material de limpieza"
              style={{ display: 'block', width: '100%' }}
            />
          </label>
          <label>
            Fecha
            <input type="date" required value={fecha} onChange={(e) => setFecha(e.target.value)} style={{ display: 'block', width: '100%' }} />
          </label>
          <button type="submit" disabled={guardando}>
            {guardando ? 'Guardando…' : 'Registrar movimiento'}
          </button>
        </form>
      )}

      <h3>Historial</h3>
      {loading ? (
        <p>Cargando…</p>
      ) : movimientos.length === 0 ? (
        <p>Todavía no hay movimientos.</p>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
              <th>Fecha</th>
              <th>Caja</th>
              <th>Movimiento</th>
              <th>Monto</th>
              <th>Motivo</th>
            </tr>
          </thead>
          <tbody>
            {movimientos.map((m) => (
              <tr key={m.id} style={{ borderBottom: '1px solid var(--border)' }}>
                <td className="mono">{fechaLegible(m.fecha)}</td>
                <td>{ETIQUETA_CAJA[m.caja]}</td>
                <td style={{ color: m.tipo === 'ingreso' ? 'var(--teal)' : 'var(--brick)' }}>
                  {m.tipo === 'ingreso' ? 'Ingreso' : 'Egreso'}
                </td>
                <td className="mono">{money(m.monto)}</td>
                <td>{m.motivo}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
