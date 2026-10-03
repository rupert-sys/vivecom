import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { DashboardPage } from './DashboardPage'
import * as reportsApi from '../api/reports'
import * as propertiesApi from '../api/properties'
import * as expensesApi from '../api/expenses'
import * as cashMovementsApi from '../api/cashMovements'
import * as reservationsApi from '../api/reservations'
import { useAuth } from '../auth/AuthContext'
import type { CollectionsSummary, FinancialSummary, Property, Reservation } from '../types'

vi.mock('../auth/AuthContext', () => ({ useAuth: vi.fn() }))

const properties: Property[] = [
  { id: 'p1', identificador: 'Casa 1', referencia_pago: '0000001', saldo_a_favor: 0, residente_principal: null, residente_principal_rol: null, total_residentes: 0 },
  { id: 'p2', identificador: 'Casa 2', referencia_pago: '0000002', saldo_a_favor: 0, residente_principal: null, residente_principal_rol: null, total_residentes: 0 },
]

const financial: FinancialSummary = {
  desde: null,
  hasta: null,
  ingresos: 5000,
  gastos: 2345,
  saldo: 2655,
  por_cobrar: 0,
  gastos_por_tipo: [],
  gastos_por_categoria: [],
  gastos_por_mes: [],
}

const cashBalance = { chica: 1500, grande: 48000 }

const reservaciones: Reservation[] = [
  { id: 'r1', amenity_id: 'am1', property_id: 'p1', fecha_inicio: '2026-09-10T10:00:00', fecha_fin: '2026-09-10T14:00:00', estado: 'aprobada', cuota: 300, cuota_pagada: true },
  { id: 'r2', amenity_id: 'am1', property_id: 'p2', fecha_inicio: '2026-09-15T10:00:00', fecha_fin: '2026-09-15T14:00:00', estado: 'pendiente', cuota: 450, cuota_pagada: false },
]

// Spies "felices" por defecto para los tres endpoints nuevos del Dashboard (Fase C): cada test que no
// necesite un valor distinto los puede dejar así en vez de repetir el mismo mock siete veces.
function mockEndpointsNuevos() {
  vi.spyOn(expensesApi, 'getFinancialSummary').mockResolvedValue(financial)
  vi.spyOn(cashMovementsApi, 'getCashBalance').mockResolvedValue(cashBalance)
  vi.spyOn(reservationsApi, 'listReservations').mockResolvedValue(reservaciones)
}

// Montos deliberadamente todos distintos entre sí (incluidos los totales)
// para que cada aserción de texto en las pruebas sea inequívoca — con
// valores repetidos (ej. total=1500 y Casa 1 cobrado=1500) getByText lanza
// "found multiple elements" en vez de comparar el número correcto.
const summary: CollectionsSummary = {
  periodo: null,
  cobrado_total: 3333,
  pendiente_total: 9999,
  por_vivienda: [
    { property_id: 'p1', identificador: 'Casa 1', cobrado: 1111, pendiente: 4444 },
    { property_id: 'p2', identificador: 'Casa 2', cobrado: 2222, pendiente: 5555 },
  ],
  por_origen: [
    { concepto: 'Mantenimiento', cobrado: 6666, pendiente: 0 },
    { concepto: 'Amenidades', cobrado: 7777, pendiente: 0 },
    { concepto: 'Proyecto', cobrado: 8888, pendiente: 0 },
  ],
}

function mockUser(rol: string | null) {
  vi.mocked(useAuth).mockReturnValue({
    user: rol ? { sub: 'u1', tenant_id: 't1', schema: 's1', rol, property_id: null, exp: 0 } : null,
    login: vi.fn(),
    logout: vi.fn(),
  })
}

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('muestra los totales de cobrado y pendiente, y el desglose por vivienda', async () => {
    mockUser('admin')
    vi.spyOn(propertiesApi, 'listProperties').mockResolvedValue(properties)
    vi.spyOn(reportsApi, 'getCollectionsSummary').mockResolvedValue(summary)
    mockEndpointsNuevos()

    render(<DashboardPage />)

    expect(await screen.findByText('$3,333')).toBeInTheDocument()
    expect(screen.getByText('$9,999')).toBeInTheDocument()
    expect(screen.getByText('$1,111')).toBeInTheDocument()
    expect(screen.getByText('$2,222')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument() // tarjeta "Viviendas": 2 propiedades
    expect(screen.getByText('$6,666')).toBeInTheDocument() // Mantenimiento
    expect(screen.getByText('$7,777')).toBeInTheDocument() // Amenidades
    expect(screen.getByText('$8,888')).toBeInTheDocument() // Proyecto
    expect(screen.getByText('$2,345')).toBeInTheDocument() // Egresos (FinancialSummary.gastos)
    expect(screen.getByText('$1,500')).toBeInTheDocument() // Caja chica
    expect(screen.getByText('$48,000')).toBeInTheDocument() // Caja grande
    const tabla = within(screen.getByRole('table'))
    expect(tabla.getByText('Casa 1')).toBeInTheDocument()
    expect(tabla.getByText('Casa 2')).toBeInTheDocument()
  })

  it('al abrir "Amenidades" se ve el detalle de cada reservación: vivienda, fecha y pago', async () => {
    mockUser('admin')
    vi.spyOn(propertiesApi, 'listProperties').mockResolvedValue(properties)
    vi.spyOn(reportsApi, 'getCollectionsSummary').mockResolvedValue(summary)
    mockEndpointsNuevos()
    const user = userEvent.setup()

    render(<DashboardPage />)
    await screen.findByText('$3,333')

    await user.click(screen.getByRole('button', { name: /amenidades/i }))

    // "Pago" solo existe en la tabla de detalle de reservaciones (la otra tabla, siempre visible,
    // tiene "Cobrado"/"Pendiente"); se escopa ahí para no chocar con "Casa 1"/"Casa 2" del <select>.
    const tablaDetalle = within((await screen.findByText('Pago')).closest('table')!)
    expect(tablaDetalle.getByText('Casa 1')).toBeInTheDocument()
    expect(tablaDetalle.getByText('Casa 2')).toBeInTheDocument()
    expect(tablaDetalle.getByText('$300')).toBeInTheDocument()
    expect(tablaDetalle.getByText('$450')).toBeInTheDocument()
  })

  it('pinchar la tarjeta "Cobrado" filtra el detalle a quién pagó, y "Adeudado" a quién debe', async () => {
    mockUser('admin')
    vi.spyOn(propertiesApi, 'listProperties').mockResolvedValue(properties)
    vi.spyOn(reportsApi, 'getCollectionsSummary').mockResolvedValue(summary)
    mockEndpointsNuevos()
    const user = userEvent.setup()

    render(<DashboardPage />)
    await screen.findByText('$3,333')
    let tabla = within(screen.getByRole('table'))
    expect(tabla.getByText('Casa 1')).toBeInTheDocument()
    expect(tabla.getByText('Casa 2')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /cobrado/i }))
    expect(await screen.findByText('Quién pagó')).toBeInTheDocument()
    tabla = within(screen.getByRole('table'))
    expect(tabla.getByText('Casa 2')).toBeInTheDocument() // Casa 2 cobrado (2222) > Casa 1 (1111): va primero
    expect(tabla.getAllByRole('row')).toHaveLength(3) // encabezado + 2 viviendas, ambas cobraron algo

    await user.click(screen.getByRole('button', { name: /adeudado/i }))
    expect(await screen.findByText('Quién debe')).toBeInTheDocument()
    tabla = within(screen.getByRole('table'))
    expect(tabla.getAllByRole('row')).toHaveLength(3) // ambas deben algo también

    await user.click(screen.getByRole('button', { name: /^viviendas/i }))
    expect(await screen.findByText('Detalle por vivienda')).toBeInTheDocument()
  })

  it('pinchar una tarjeta de concepto muestra su detalle de cobrado/pendiente', async () => {
    mockUser('admin')
    vi.spyOn(propertiesApi, 'listProperties').mockResolvedValue(properties)
    vi.spyOn(reportsApi, 'getCollectionsSummary').mockResolvedValue(summary)
    mockEndpointsNuevos()
    const user = userEvent.setup()

    render(<DashboardPage />)
    await screen.findByText('$3,333')

    await user.click(screen.getByRole('button', { name: /mantenimiento/i }))
    await waitFor(() => expect(screen.getAllByText('$6,666')).toHaveLength(2)) // tarjeta + detalle expandido
    expect(screen.getByText(/cobrado:/i)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /mantenimiento/i }))
    expect(screen.getAllByText('$6,666')).toHaveLength(1) // se cierra al pinchar otra vez
  })

  it('tesorero también tiene acceso', async () => {
    mockUser('tesorero')
    vi.spyOn(propertiesApi, 'listProperties').mockResolvedValue([])
    vi.spyOn(reportsApi, 'getCollectionsSummary').mockResolvedValue({
      periodo: null,
      cobrado_total: 0,
      pendiente_total: 0,
      por_vivienda: [],
      por_origen: [
        { concepto: 'Mantenimiento', cobrado: 0, pendiente: 0 },
        { concepto: 'Amenidades', cobrado: 0, pendiente: 0 },
        { concepto: 'Proyecto', cobrado: 0, pendiente: 0 },
      ],
    })
    mockEndpointsNuevos()

    render(<DashboardPage />)

    expect(await screen.findByText(/no hay cargos que mostrar/i)).toBeInTheDocument()
  })

  it('un rol sin acceso (ej. guardia) ve un mensaje en vez del dashboard, sin llamar a la API', async () => {
    mockUser('guardia')
    const summarySpy = vi.spyOn(reportsApi, 'getCollectionsSummary')

    render(<DashboardPage />)

    expect(await screen.findByText(/no tienes acceso a esta vista/i)).toBeInTheDocument()
    expect(summarySpy).not.toHaveBeenCalled()
  })

  it('cambiar el filtro de vivienda vuelve a pedir el resumen con ese property_id', async () => {
    mockUser('admin')
    vi.spyOn(propertiesApi, 'listProperties').mockResolvedValue(properties)
    const summarySpy = vi.spyOn(reportsApi, 'getCollectionsSummary').mockResolvedValue(summary)
    mockEndpointsNuevos()
    const user = userEvent.setup()

    render(<DashboardPage />)
    await screen.findByText('$3,333')

    await user.selectOptions(screen.getByRole('combobox'), 'p2')

    await waitFor(() => expect(summarySpy).toHaveBeenLastCalledWith({ periodo: undefined, propertyId: 'p2' }))
  })

  it('cambiar el periodo le pide a egresos el mismo rango de fechas (los gastos no son por vivienda)', async () => {
    mockUser('admin')
    vi.spyOn(propertiesApi, 'listProperties').mockResolvedValue(properties)
    vi.spyOn(reportsApi, 'getCollectionsSummary').mockResolvedValue(summary)
    const financialSpy = vi.spyOn(expensesApi, 'getFinancialSummary').mockResolvedValue(financial)
    vi.spyOn(cashMovementsApi, 'getCashBalance').mockResolvedValue(cashBalance)
    vi.spyOn(reservationsApi, 'listReservations').mockResolvedValue(reservaciones)

    render(<DashboardPage />)
    await screen.findByText('$3,333')

    fireEvent.change(screen.getByLabelText('Periodo'), { target: { value: '2026-09' } })

    await waitFor(() => expect(financialSpy).toHaveBeenLastCalledWith('2026-09-01', '2026-09-30'))
  })

  it('muestra el error del backend si falla la carga', async () => {
    mockUser('admin')
    vi.spyOn(propertiesApi, 'listProperties').mockResolvedValue([])
    vi.spyOn(reportsApi, 'getCollectionsSummary').mockRejectedValue(new Error('caída'))
    mockEndpointsNuevos()

    render(<DashboardPage />)

    expect(await screen.findByText(/no se pudo cargar el dashboard financiero/i)).toBeInTheDocument()
  })
})
