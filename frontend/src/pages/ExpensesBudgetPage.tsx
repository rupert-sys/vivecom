import { useEffect, useState, type FormEvent } from 'react'
import { createExpense, listExpenses } from '../api/expenses'
import { createBudget, getBudgetReport } from '../api/budgets'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import type { BudgetComparison, Expense, PeriodicidadPresupuesto } from '../types'

export function ExpensesBudgetPage() {
  const { user } = useAuth()
  const isAdmin = user?.rol === 'admin'

  const [expenses, setExpenses] = useState<Expense[]>([])
  const [reporte, setReporte] = useState<BudgetComparison[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [categoria, setCategoria] = useState('')
  const [monto, setMonto] = useState('')
  const [fecha, setFecha] = useState('')
  const [comprobanteUrl, setComprobanteUrl] = useState('')
  const [creandoGasto, setCreandoGasto] = useState(false)

  const [presupuestoCategoria, setPresupuestoCategoria] = useState('')
  const [presupuestoPeriodicidad, setPresupuestoPeriodicidad] = useState<PeriodicidadPresupuesto>('mensual')
  const [presupuestoPeriodo, setPresupuestoPeriodo] = useState('')
  const [presupuestoMonto, setPresupuestoMonto] = useState('')
  const [creandoPresupuesto, setCreandoPresupuesto] = useState(false)

  async function reload() {
    setLoading(true)
    try {
      const [expensesResult, reporteResult] = await Promise.all([listExpenses(), getBudgetReport()])
      setExpenses(expensesResult)
      setReporte(reporteResult)
      setError(null)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo cargar gastos y presupuesto.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    reload()
  }, [])

  async function handleCreateExpense(event: FormEvent) {
    event.preventDefault()
    setCreandoGasto(true)
    try {
      await createExpense({ categoria, monto: Number(monto), fecha, comprobante_url: comprobanteUrl })
      setCategoria('')
      setMonto('')
      setFecha('')
      setComprobanteUrl('')
      await reload()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo registrar el gasto.')
    } finally {
      setCreandoGasto(false)
    }
  }

  async function handleCreateBudget(event: FormEvent) {
    event.preventDefault()
    setCreandoPresupuesto(true)
    try {
      await createBudget({
        categoria: presupuestoCategoria,
        periodicidad: presupuestoPeriodicidad,
        periodo: presupuestoPeriodo,
        monto_planeado: Number(presupuestoMonto),
      })
      setPresupuestoCategoria('')
      setPresupuestoPeriodo('')
      setPresupuestoMonto('')
      await reload()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo registrar el presupuesto.')
    } finally {
      setCreandoPresupuesto(false)
    }
  }

  return (
    <div>
      <h2>Gastos y presupuesto</h2>
      {error && <p style={{ color: 'var(--brick)' }}>{error}</p>}

      <h3>Gastos</h3>
      {isAdmin && (
        <form onSubmit={handleCreateExpense} style={{ display: 'flex', gap: 'var(--space-2)', flexWrap: 'wrap', margin: 'var(--space-3) 0' }}>
          <input placeholder="Categoría del gasto" value={categoria} onChange={(e) => setCategoria(e.target.value)} required />
          <input type="number" step="0.01" placeholder="Monto" value={monto} onChange={(e) => setMonto(e.target.value)} required />
          <input type="date" aria-label="Fecha del gasto" value={fecha} onChange={(e) => setFecha(e.target.value)} required />
          <input
            placeholder="URL del comprobante"
            value={comprobanteUrl}
            onChange={(e) => setComprobanteUrl(e.target.value)}
            required
          />
          <button type="submit" disabled={creandoGasto}>
            {creandoGasto ? 'Registrando…' : 'Registrar gasto'}
          </button>
        </form>
      )}

      {loading ? (
        <p>Cargando…</p>
      ) : expenses.length === 0 ? (
        <p>Todavía no hay gastos registrados.</p>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: 'var(--space-4)' }}>
          <thead>
            <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
              <th>Fecha</th>
              <th>Categoría</th>
              <th>Monto</th>
              <th>Comprobante</th>
            </tr>
          </thead>
          <tbody>
            {expenses.map((gasto) => (
              <tr key={gasto.id} style={{ borderBottom: '1px solid var(--border)' }}>
                <td className="mono">{gasto.fecha}</td>
                <td>{gasto.categoria}</td>
                <td className="mono">${gasto.monto.toFixed(2)}</td>
                <td>
                  <a href={gasto.comprobante_url} target="_blank" rel="noreferrer">
                    Ver
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h3>Presupuesto vs. real</h3>
      {isAdmin && (
        <form onSubmit={handleCreateBudget} style={{ display: 'flex', gap: 'var(--space-2)', flexWrap: 'wrap', margin: 'var(--space-3) 0' }}>
          <input
            placeholder="Categoría del presupuesto"
            value={presupuestoCategoria}
            onChange={(e) => setPresupuestoCategoria(e.target.value)}
            required
          />
          <select value={presupuestoPeriodicidad} onChange={(e) => setPresupuestoPeriodicidad(e.target.value as PeriodicidadPresupuesto)}>
            <option value="mensual">Mensual</option>
            <option value="anual">Anual</option>
          </select>
          <input
            type="date"
            aria-label="Periodo del presupuesto"
            value={presupuestoPeriodo}
            onChange={(e) => setPresupuestoPeriodo(e.target.value)}
            required
          />
          <input
            type="number"
            step="0.01"
            placeholder="Monto planeado"
            value={presupuestoMonto}
            onChange={(e) => setPresupuestoMonto(e.target.value)}
            required
          />
          <button type="submit" disabled={creandoPresupuesto}>
            {creandoPresupuesto ? 'Registrando…' : 'Registrar presupuesto'}
          </button>
        </form>
      )}

      {reporte.length === 0 ? (
        <p>Todavía no hay presupuesto configurado para este periodo.</p>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
              <th>Categoría</th>
              <th>Periodicidad</th>
              <th>Planeado</th>
              <th>Real</th>
            </tr>
          </thead>
          <tbody>
            {reporte.map((fila) => (
              <tr key={fila.categoria} style={{ borderBottom: '1px solid var(--border)' }}>
                <td>{fila.categoria}</td>
                <td>{fila.periodicidad === 'mensual' ? 'Mensual' : 'Anual'}</td>
                <td className="mono">${fila.monto_planeado.toFixed(2)}</td>
                <td className="mono" style={{ color: fila.monto_real > fila.monto_planeado ? 'var(--brick)' : 'var(--teal)' }}>
                  ${fila.monto_real.toFixed(2)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
