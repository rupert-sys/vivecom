import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ReportsExportPage } from './ReportsExportPage'
import * as reportsExportApi from '../api/reportsExport'
import * as propertiesApi from '../api/properties'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import type { Property } from '../types'

vi.mock('../auth/AuthContext', () => ({ useAuth: vi.fn() }))

const properties: Property[] = [{ id: 'p1', identificador: 'Casa 1', referencia_pago: '0000001', saldo_a_favor: 0, residente_principal: null, residente_principal_rol: null, total_residentes: 0 }]

function mockUser(rol: string | null) {
  vi.mocked(useAuth).mockReturnValue({
    user: rol ? { sub: 'u1', tenant_id: 't1', schema: 's1', rol, property_id: null, exp: 0 } : null,
    login: vi.fn(),
    logout: vi.fn(),
  })
}

describe('ReportsExportPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('un rol sin acceso (ej. residente) ve un mensaje en vez de los botones de exportar', () => {
    mockUser('residente')

    render(<ReportsExportPage />)

    expect(screen.getByText(/no tienes acceso a esta vista/i)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /exportar a excel/i })).not.toBeInTheDocument()
  })

  it('admin puede exportar estados de cuenta filtrando por vivienda', async () => {
    mockUser('admin')
    vi.spyOn(propertiesApi, 'listProperties').mockResolvedValue(properties)
    const exportSpy = vi.spyOn(reportsExportApi, 'exportAccountStatements').mockResolvedValue(undefined)
    const user = userEvent.setup()

    render(<ReportsExportPage />)
    await screen.findByText('Casa 1')

    await user.selectOptions(screen.getAllByRole('combobox')[0], 'p1')
    await user.click(screen.getAllByRole('button', { name: /exportar a excel/i })[0])

    await waitFor(() => expect(exportSpy).toHaveBeenCalledWith('p1'))
  })

  it('tesorero puede exportar gastos con rango de fechas', async () => {
    mockUser('tesorero')
    vi.spyOn(propertiesApi, 'listProperties').mockResolvedValue([])
    const exportSpy = vi.spyOn(reportsExportApi, 'exportExpenses').mockResolvedValue(undefined)
    const user = userEvent.setup()

    render(<ReportsExportPage />)

    await user.type(screen.getByLabelText('Desde'), '2026-09-01')
    await user.type(screen.getByLabelText('Hasta'), '2026-09-30')
    await user.click(screen.getAllByRole('button', { name: /exportar a excel/i })[1])

    await waitFor(() => expect(exportSpy).toHaveBeenCalledWith('2026-09-01', '2026-09-30'))
  })

  it('admin puede exportar el presupuesto de un periodo', async () => {
    mockUser('admin')
    vi.spyOn(propertiesApi, 'listProperties').mockResolvedValue([])
    const exportSpy = vi.spyOn(reportsExportApi, 'exportBudgetReport').mockResolvedValue(undefined)
    const user = userEvent.setup()

    render(<ReportsExportPage />)

    await user.type(screen.getByLabelText('Periodo'), '2026-09')
    await user.click(screen.getAllByRole('button', { name: /exportar a excel/i })[2])

    await waitFor(() => expect(exportSpy).toHaveBeenCalledWith('2026-09-01'))
  })

  it('muestra el error del backend si falla una exportación', async () => {
    mockUser('admin')
    vi.spyOn(propertiesApi, 'listProperties').mockResolvedValue([])
    vi.spyOn(reportsExportApi, 'exportExpenses').mockRejectedValue(new ApiError(403, 'No tienes acceso a este reporte'))
    const user = userEvent.setup()

    render(<ReportsExportPage />)

    await user.click(screen.getAllByRole('button', { name: /exportar a excel/i })[1])

    expect(await screen.findByText('No tienes acceso a este reporte')).toBeInTheDocument()
  })
})
