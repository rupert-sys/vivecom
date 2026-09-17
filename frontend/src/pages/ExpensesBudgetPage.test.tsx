import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ExpensesBudgetPage } from './ExpensesBudgetPage'
import * as expensesApi from '../api/expenses'
import * as budgetsApi from '../api/budgets'
import { useAuth } from '../auth/AuthContext'
import type { BudgetComparison, Expense } from '../types'

vi.mock('../auth/AuthContext', () => ({ useAuth: vi.fn() }))

const gasto: Expense = {
  id: 'g1',
  categoria: 'Jardinería',
  monto: 3200,
  comprobante_url: 'https://ejemplo.com/comprobante.pdf',
  fecha: '2026-09-05',
}

// monto_real deliberadamente distinto del monto del gasto de arriba, para
// que ninguna aserción de texto en las pruebas sea ambigua (ver lección de
// DashboardPage.test.tsx: montos repetidos rompen getByText).
const comparacion: BudgetComparison = {
  categoria: 'Jardinería',
  periodicidad: 'mensual',
  monto_planeado: 5000,
  monto_real: 3210,
}

function mockUser(rol: string) {
  vi.mocked(useAuth).mockReturnValue({
    user: { sub: 'u1', tenant_id: 't1', schema: 's1', rol, property_id: null, exp: 0 },
    login: vi.fn(),
    logout: vi.fn(),
  })
}

describe('ExpensesBudgetPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('lista gastos y el reporte de presupuesto vs. real', async () => {
    mockUser('tesorero')
    vi.spyOn(expensesApi, 'listExpenses').mockResolvedValue([gasto])
    vi.spyOn(budgetsApi, 'getBudgetReport').mockResolvedValue([comparacion])

    render(<ExpensesBudgetPage />)

    expect(await screen.findByText('$3200.00')).toBeInTheDocument()
    expect(screen.getByText('$5000.00')).toBeInTheDocument()
    expect(screen.getByText('$3210.00')).toBeInTheDocument()
    // "Jardinería" aparece dos veces (categoría del gasto y de la fila del
    // presupuesto) — legítimamente ambiguo, solo se confirma que ambas tablas
    // renderizaron su respectiva fila.
    expect(screen.getAllByText('Jardinería')).toHaveLength(2)
  })

  it('no muestra los formularios de alta si el rol no es admin', async () => {
    mockUser('residente')
    vi.spyOn(expensesApi, 'listExpenses').mockResolvedValue([gasto])
    vi.spyOn(budgetsApi, 'getBudgetReport').mockResolvedValue([comparacion])

    render(<ExpensesBudgetPage />)

    await screen.findByText('$3200.00')
    expect(screen.queryByPlaceholderText('Categoría del gasto')).not.toBeInTheDocument()
    expect(screen.queryByPlaceholderText('Monto planeado')).not.toBeInTheDocument()
  })

  it('un admin puede registrar un gasto nuevo', async () => {
    mockUser('admin')
    vi.spyOn(expensesApi, 'listExpenses').mockResolvedValue([])
    vi.spyOn(budgetsApi, 'getBudgetReport').mockResolvedValue([])
    const createSpy = vi.spyOn(expensesApi, 'createExpense').mockResolvedValue(gasto)
    const user = userEvent.setup()

    render(<ExpensesBudgetPage />)
    await screen.findByText(/todavía no hay gastos/i)

    await user.type(screen.getByPlaceholderText('Categoría del gasto'), 'Jardinería')
    await user.type(screen.getByPlaceholderText('Monto'), '3200')
    await user.type(screen.getByLabelText('Fecha del gasto'), '2026-09-05')
    await user.type(screen.getByPlaceholderText('URL del comprobante'), 'https://ejemplo.com/c.pdf')
    await user.click(screen.getByRole('button', { name: /registrar gasto/i }))

    await waitFor(() =>
      expect(createSpy).toHaveBeenCalledWith({
        categoria: 'Jardinería',
        monto: 3200,
        fecha: '2026-09-05',
        comprobante_url: 'https://ejemplo.com/c.pdf',
      }),
    )
  })

  it('un admin puede registrar un presupuesto nuevo', async () => {
    mockUser('admin')
    vi.spyOn(expensesApi, 'listExpenses').mockResolvedValue([])
    vi.spyOn(budgetsApi, 'getBudgetReport').mockResolvedValue([])
    const createSpy = vi.spyOn(budgetsApi, 'createBudget').mockResolvedValue({
      id: 'b1',
      categoria: 'Jardinería',
      periodicidad: 'mensual',
      periodo: '2026-09-01',
      monto_planeado: 5000,
    })
    const user = userEvent.setup()

    render(<ExpensesBudgetPage />)
    await screen.findByText(/todavía no hay presupuesto/i)

    await user.type(screen.getByPlaceholderText('Categoría del presupuesto'), 'Jardinería')
    await user.type(screen.getByLabelText('Periodo del presupuesto'), '2026-09-01')
    await user.type(screen.getByPlaceholderText('Monto planeado'), '5000')
    await user.click(screen.getByRole('button', { name: /registrar presupuesto/i }))

    await waitFor(() =>
      expect(createSpy).toHaveBeenCalledWith({
        categoria: 'Jardinería',
        periodicidad: 'mensual',
        periodo: '2026-09-01',
        monto_planeado: 5000,
      }),
    )
  })

  it('resalta en color de alerta cuando el gasto real supera lo planeado', async () => {
    mockUser('tesorero')
    vi.spyOn(expensesApi, 'listExpenses').mockResolvedValue([])
    vi.spyOn(budgetsApi, 'getBudgetReport').mockResolvedValue([
      { categoria: 'Seguridad', periodicidad: 'mensual', monto_planeado: 1000, monto_real: 1500 },
    ])

    render(<ExpensesBudgetPage />)

    const celda = await screen.findByText('$1500.00')
    expect(celda).toHaveStyle({ color: 'var(--brick)' })
  })

  it('muestra el error del backend si falla la carga', async () => {
    mockUser('admin')
    vi.spyOn(expensesApi, 'listExpenses').mockRejectedValue(new Error('caída'))
    vi.spyOn(budgetsApi, 'getBudgetReport').mockResolvedValue([])

    render(<ExpensesBudgetPage />)

    expect(await screen.findByText(/no se pudo cargar gastos y presupuesto/i)).toBeInTheDocument()
  })
})
