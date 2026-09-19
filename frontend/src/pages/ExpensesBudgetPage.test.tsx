import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ExpensesBudgetPage } from './ExpensesBudgetPage'
import * as expensesApi from '../api/expenses'
import * as budgetsApi from '../api/budgets'
import * as reglamentoApi from '../api/reglamento'
import * as filesApi from '../api/files'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import type { BudgetComparison, Expense, FinancialSummary, Reglamento } from '../types'

vi.mock('../auth/AuthContext', () => ({ useAuth: vi.fn() }))

const gasto: Expense = {
  id: 'g1',
  categoria: 'Jardinería',
  monto: 3200,
  comprobante_url: 'https://ejemplo.com/comprobante.pdf',
  fecha: '2026-09-05',
  tipo: 'operativo',
  aprobado_en_asamblea: false,
  acta_referencia: null,
  cotizaciones: null,
  tipo_comprobante: null,
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

// Cifras deliberadamente distintas de las de los gastos y del presupuesto de arriba.
const resumen: FinancialSummary = {
  desde: null,
  hasta: null,
  ingresos: 9000.5,
  gastos: 4321.25,
  saldo: 4679.25,
  por_cobrar: 111.11,
  gastos_por_tipo: [{ concepto: 'operativo', total: 4321.25, cantidad: 3 }],
  gastos_por_categoria: [
    { concepto: 'Limpieza', total: 4000, cantidad: 2 },
    { concepto: 'Portería', total: 321.25, cantidad: 1 },
  ],
}

const reglamento: Reglamento = {
  dia_limite_pago: 5,
  dia_recargo: 6,
  recargo_porcentaje: 0.05,
  recargo_modalidad: 'mensual_sobre_saldo',
  acepta_pago_efectivo: true,
  morosos_sin_voto: true,
  morosos_sin_areas_comunes: true,
  gasto_umbral_asamblea: 10000,
  cotizaciones_minimas: 3,
  cajones_visitas: 7,
  horas_max_estacionamiento_visitas: 24,
  dudas_en_avisos_por_defecto: false,
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
    vi.spyOn(expensesApi, 'getFinancialSummary').mockResolvedValue(resumen)
    vi.spyOn(reglamentoApi, 'getReglamento').mockResolvedValue(reglamento)
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
    const user = userEvent.setup({ delay: null })

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
        tipo: 'operativo',
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
    const user = userEvent.setup({ delay: null })

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

  it('el resumen dice ingresos, gastos y saldo a favor, y cuánto se gastó por categoría', async () => {
    mockUser('tesorero')
    vi.spyOn(expensesApi, 'listExpenses').mockResolvedValue([])
    vi.spyOn(budgetsApi, 'getBudgetReport').mockResolvedValue([])

    render(<ExpensesBudgetPage />)

    expect(await screen.findByText('$9000.50')).toBeInTheDocument()
    expect(screen.getByText('Saldo a favor')).toBeInTheDocument()
    expect(screen.getAllByText('$4321.25').length).toBeGreaterThan(0) // la tarjeta de gastos (y el saldo en contra no aparece)
    expect(screen.getByText('$4679.25')).toBeInTheDocument()
    expect(screen.getByText('$111.11')).toBeInTheDocument()
    expect(screen.getByText('Limpieza')).toBeInTheDocument()
    expect(screen.getByText('Portería')).toBeInTheDocument()
  })

  it('con más gastos que ingresos el saldo se muestra en contra y en positivo', async () => {
    mockUser('tesorero')
    vi.spyOn(expensesApi, 'listExpenses').mockResolvedValue([])
    vi.spyOn(budgetsApi, 'getBudgetReport').mockResolvedValue([])
    vi.spyOn(expensesApi, 'getFinancialSummary').mockResolvedValue({ ...resumen, saldo: -777.7 })

    render(<ExpensesBudgetPage />)

    expect(await screen.findByText('Saldo en contra')).toBeInTheDocument()
    expect(screen.getByText('$777.70')).toBeInTheDocument()
  })

  it('cambiar el rango de fechas pide el resumen de ese rango', async () => {
    mockUser('tesorero')
    vi.spyOn(expensesApi, 'listExpenses').mockResolvedValue([])
    vi.spyOn(budgetsApi, 'getBudgetReport').mockResolvedValue([])
    const spy = vi.spyOn(expensesApi, 'getFinancialSummary').mockResolvedValue(resumen)
    const user = userEvent.setup({ delay: null })

    render(<ExpensesBudgetPage />)
    await screen.findByText('$9000.50')
    await user.type(screen.getByLabelText('Resumen desde'), '2026-01-01')
    await user.type(screen.getByLabelText('Resumen hasta'), '2026-06-30')

    await waitFor(() => expect(spy).toHaveBeenLastCalledWith('2026-01-01', '2026-06-30'))
  })

  it('si el resumen falla, los gastos y el presupuesto siguen visibles', async () => {
    mockUser('tesorero')
    vi.spyOn(expensesApi, 'listExpenses').mockResolvedValue([gasto])
    vi.spyOn(budgetsApi, 'getBudgetReport').mockResolvedValue([comparacion])
    vi.spyOn(expensesApi, 'getFinancialSummary').mockRejectedValue(new Error('caída'))

    render(<ExpensesBudgetPage />)

    expect(await screen.findByText('$3200.00')).toBeInTheDocument()
    expect(screen.queryByText('Saldo a favor')).not.toBeInTheDocument()
    expect(screen.queryByText(/no se pudo cargar/i)).not.toBeInTheDocument()
  })

  it('la lista muestra el tipo del gasto y su sustento (asamblea y cotizaciones)', async () => {
    mockUser('tesorero')
    vi.spyOn(expensesApi, 'listExpenses').mockResolvedValue([
      {
        ...gasto,
        id: 'g2',
        categoria: 'Portón',
        monto: 45000,
        tipo: 'extraordinario',
        aprobado_en_asamblea: true,
        tipo_comprobante: 'factura',
        cotizaciones: [
          { proveedor: 'A', monto: 45000 },
          { proveedor: 'B', monto: 52000 },
          { proveedor: 'C', monto: 48000 },
        ],
      },
    ])
    vi.spyOn(budgetsApi, 'getBudgetReport').mockResolvedValue([])

    render(<ExpensesBudgetPage />)

    expect(await screen.findByText('Extraordinario')).toBeInTheDocument()
    expect(screen.getByText('Asamblea · 3 cotizaciones')).toBeInTheDocument()
    expect(screen.getByText('(factura)')).toBeInTheDocument()
  })

  it('un gasto operativo no pide sustento; uno extraordinario sí y avisa el umbral del reglamento', async () => {
    mockUser('admin')
    vi.spyOn(expensesApi, 'listExpenses').mockResolvedValue([])
    vi.spyOn(budgetsApi, 'getBudgetReport').mockResolvedValue([])
    const user = userEvent.setup({ delay: null })

    render(<ExpensesBudgetPage />)
    await screen.findByText(/todavía no hay gastos/i)
    expect(screen.queryByText('Sustento del gasto')).not.toBeInTheDocument()

    await user.selectOptions(screen.getByLabelText('Tipo de gasto'), 'extraordinario')

    expect(screen.getByText('Sustento del gasto')).toBeInTheDocument()
    expect(screen.getByText('$10000.00')).toBeInTheDocument()
    expect(screen.getByText(/al menos 3 cotizaciones/i)).toBeInTheDocument()
  })

  it('registra un gasto extraordinario con asamblea, acta y cotizaciones', async () => {
    mockUser('admin')
    vi.spyOn(expensesApi, 'listExpenses').mockResolvedValue([])
    vi.spyOn(budgetsApi, 'getBudgetReport').mockResolvedValue([])
    const createSpy = vi.spyOn(expensesApi, 'createExpense').mockResolvedValue(gasto)
    const user = userEvent.setup({ delay: null })

    render(<ExpensesBudgetPage />)
    await screen.findByText(/todavía no hay gastos/i)
    await user.type(screen.getByPlaceholderText('Categoría del gasto'), 'Portón')
    await user.type(screen.getByPlaceholderText('Monto'), '45000')
    await user.type(screen.getByLabelText('Fecha del gasto'), '2026-09-05')
    await user.type(screen.getByPlaceholderText('URL del comprobante'), 'https://ejemplo.com/f.pdf')
    await user.selectOptions(screen.getByLabelText('Tipo de gasto'), 'extraordinario')
    await user.selectOptions(screen.getByLabelText('Tipo de comprobante'), 'factura')
    await user.click(screen.getByLabelText(/aprobado en asamblea/i))
    await user.type(screen.getByPlaceholderText(/acta o referencia/i), 'Asamblea 18-ene-2026')
    await user.type(screen.getByPlaceholderText('Proveedor de la cotización 1'), 'Herrería López')
    await user.type(screen.getByLabelText('Monto de la cotización 1'), '45000')
    await user.click(screen.getByRole('button', { name: /agregar cotización/i }))
    await user.type(screen.getByPlaceholderText('Proveedor de la cotización 2'), 'Portones MX')
    await user.type(screen.getByLabelText('Monto de la cotización 2'), '52000')
    await user.click(screen.getByRole('button', { name: /registrar gasto/i }))

    await waitFor(() => expect(createSpy).toHaveBeenCalledTimes(1))
    expect(createSpy).toHaveBeenCalledWith({
      categoria: 'Portón',
      monto: 45000,
      fecha: '2026-09-05',
      comprobante_url: 'https://ejemplo.com/f.pdf',
      tipo: 'extraordinario',
      tipo_comprobante: 'factura',
      aprobado_en_asamblea: true,
      acta_referencia: 'Asamblea 18-ene-2026',
      cotizaciones: [
        { proveedor: 'Herrería López', monto: 45000 },
        { proveedor: 'Portones MX', monto: 52000 },
      ],
    })
  })

  it('muestra el rechazo del backend cuando falta asamblea o cotizaciones', async () => {
    mockUser('admin')
    vi.spyOn(expensesApi, 'listExpenses').mockResolvedValue([])
    vi.spyOn(budgetsApi, 'getBudgetReport').mockResolvedValue([])
    vi.spyOn(expensesApi, 'createExpense').mockRejectedValue(
      new ApiError(422, 'Un gasto extraordinario mayor a $10,000.00 requiere aprobación de la asamblea.'),
    )
    const user = userEvent.setup({ delay: null })

    render(<ExpensesBudgetPage />)
    await screen.findByText(/todavía no hay gastos/i)
    await user.type(screen.getByPlaceholderText('Categoría del gasto'), 'Portón')
    await user.type(screen.getByPlaceholderText('Monto'), '45000')
    await user.type(screen.getByLabelText('Fecha del gasto'), '2026-09-05')
    await user.type(screen.getByPlaceholderText('URL del comprobante'), 'https://ejemplo.com/f.pdf')
    await user.selectOptions(screen.getByLabelText('Tipo de gasto'), 'extraordinario')
    await user.click(screen.getByRole('button', { name: /registrar gasto/i }))

    expect(await screen.findByText(/mayor a \$10,000\.00 requiere aprobación/i)).toBeInTheDocument()
  })

  it('sube el comprobante como archivo y el gasto lleva su identificador, no un enlace', async () => {
    mockUser('admin')
    vi.spyOn(expensesApi, 'listExpenses').mockResolvedValue([])
    vi.spyOn(budgetsApi, 'getBudgetReport').mockResolvedValue([])
    const uploadSpy = vi
      .spyOn(filesApi, 'uploadFile')
      .mockResolvedValue({ id: 'arch-1', nombre_original: 'factura.pdf', content_type: 'application/pdf', size: 10, ref: '/files/arch-1' })
    const createSpy = vi.spyOn(expensesApi, 'createExpense').mockResolvedValue(gasto)
    const user = userEvent.setup({ delay: null })

    render(<ExpensesBudgetPage />)
    await screen.findByText(/todavía no hay gastos/i)
    await user.type(screen.getByPlaceholderText('Categoría del gasto'), 'Jardinería')
    await user.type(screen.getByPlaceholderText('Monto'), '3200')
    await user.type(screen.getByLabelText('Fecha del gasto'), '2026-09-05')
    const archivo = new File(['%PDF-1.7'], 'factura.pdf', { type: 'application/pdf' })
    await user.upload(screen.getByLabelText(/comprobante \(foto o pdf/i), archivo)
    await user.click(screen.getByRole('button', { name: /registrar gasto/i }))

    await waitFor(() => expect(createSpy).toHaveBeenCalledTimes(1))
    expect(uploadSpy).toHaveBeenCalledWith(archivo, 'gasto')
    expect(createSpy).toHaveBeenCalledWith({
      categoria: 'Jardinería',
      monto: 3200,
      fecha: '2026-09-05',
      comprobante_archivo_id: 'arch-1',
      tipo: 'operativo',
    })
  })

  it('sin archivo ni enlace no se manda el gasto y se pide adjuntar el comprobante', async () => {
    mockUser('admin')
    vi.spyOn(expensesApi, 'listExpenses').mockResolvedValue([])
    vi.spyOn(budgetsApi, 'getBudgetReport').mockResolvedValue([])
    const createSpy = vi.spyOn(expensesApi, 'createExpense').mockResolvedValue(gasto)
    const user = userEvent.setup({ delay: null })

    render(<ExpensesBudgetPage />)
    await screen.findByText(/todavía no hay gastos/i)
    await user.type(screen.getByPlaceholderText('Categoría del gasto'), 'Jardinería')
    await user.type(screen.getByPlaceholderText('Monto'), '3200')
    await user.type(screen.getByLabelText('Fecha del gasto'), '2026-09-05')
    await user.click(screen.getByRole('button', { name: /registrar gasto/i }))

    expect(await screen.findByText(/adjunta el comprobante del gasto/i)).toBeInTheDocument()
    expect(createSpy).not.toHaveBeenCalled()
  })

  it('sube también el archivo de cada cotización', async () => {
    mockUser('admin')
    vi.spyOn(expensesApi, 'listExpenses').mockResolvedValue([])
    vi.spyOn(budgetsApi, 'getBudgetReport').mockResolvedValue([])
    let contador = 0
    vi.spyOn(filesApi, 'uploadFile').mockImplementation(async () => ({
      id: `arch-${++contador}`,
      nombre_original: 'a.pdf',
      content_type: 'application/pdf',
      size: 1,
      ref: '/files/x',
    }))
    const createSpy = vi.spyOn(expensesApi, 'createExpense').mockResolvedValue(gasto)
    const user = userEvent.setup({ delay: null })

    render(<ExpensesBudgetPage />)
    await screen.findByText(/todavía no hay gastos/i)
    await user.type(screen.getByPlaceholderText('Categoría del gasto'), 'Portón')
    await user.type(screen.getByPlaceholderText('Monto'), '45000')
    await user.type(screen.getByLabelText('Fecha del gasto'), '2026-09-05')
    await user.type(screen.getByLabelText(/o pega el enlace/i), 'https://ejemplo.com/f.pdf')
    await user.selectOptions(screen.getByLabelText('Tipo de gasto'), 'programado')
    await user.type(screen.getByPlaceholderText('Proveedor de la cotización 1'), 'Herrería López')
    await user.type(screen.getByLabelText('Monto de la cotización 1'), '45000')
    await user.upload(
      screen.getByLabelText('Archivo de la cotización 1'),
      new File(['%PDF-1.7'], 'cot.pdf', { type: 'application/pdf' }),
    )
    await user.click(screen.getByRole('button', { name: /registrar gasto/i }))

    await waitFor(() => expect(createSpy).toHaveBeenCalledTimes(1))
    expect(createSpy.mock.calls[0][0]).toMatchObject({
      comprobante_url: 'https://ejemplo.com/f.pdf', // sin archivo de comprobante: sigue valiendo el enlace
      cotizaciones: [{ proveedor: 'Herrería López', monto: 45000, archivo_id: 'arch-1' }],
    })
  })

  it('si la subida falla, muestra el motivo y no registra el gasto', async () => {
    mockUser('admin')
    vi.spyOn(expensesApi, 'listExpenses').mockResolvedValue([])
    vi.spyOn(budgetsApi, 'getBudgetReport').mockResolvedValue([])
    vi.spyOn(filesApi, 'uploadFile').mockRejectedValue(new ApiError(415, 'Solo se aceptan fotos (JPG, PNG, WEBP, HEIC) o PDF.'))
    const createSpy = vi.spyOn(expensesApi, 'createExpense').mockResolvedValue(gasto)
    // El input filtra por `accept`; se desactiva para simular un archivo no aceptado que el navegador dejó pasar.
    const user = userEvent.setup({ delay: null, applyAccept: false })

    render(<ExpensesBudgetPage />)
    await screen.findByText(/todavía no hay gastos/i)
    await user.type(screen.getByPlaceholderText('Categoría del gasto'), 'Jardinería')
    await user.type(screen.getByPlaceholderText('Monto'), '3200')
    await user.type(screen.getByLabelText('Fecha del gasto'), '2026-09-05')
    await user.upload(screen.getByLabelText(/comprobante \(foto o pdf/i), new File(['x'], 'x.exe', { type: 'application/octet-stream' }))
    await user.click(screen.getByRole('button', { name: /registrar gasto/i }))

    expect(await screen.findByText(/solo se aceptan fotos/i)).toBeInTheDocument()
    expect(createSpy).not.toHaveBeenCalled()
  })
})
