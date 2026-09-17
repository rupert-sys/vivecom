import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { FeesPage } from './FeesPage'
import * as feesApi from '../api/fees'
import { useAuth } from '../auth/AuthContext'
import type { Fee, GlobalRules } from '../types'

vi.mock('../auth/AuthContext', () => ({ useAuth: vi.fn() }))

const fee: Fee = { id: 'fee-1', monto: 1500, periodicidad: 'mensual', activa_desde: '2026-09-01' }
// El backend regresa recargo_porcentaje como fracción (0.10 = 10%), no como entero.
const rules: GlobalRules = { recargo_porcentaje: 0.1, recargo_dia_del_mes: 6 }

function mockUser(rol: string) {
  vi.mocked(useAuth).mockReturnValue({
    user: { sub: 'u1', tenant_id: 't1', schema: 's1', rol, property_id: null, exp: 0 },
    login: vi.fn(),
    logout: vi.fn(),
  })
}

describe('FeesPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('lista las cuotas configuradas y la regla global de recargo', async () => {
    mockUser('tesorero')
    vi.spyOn(feesApi, 'listFees').mockResolvedValue([fee])
    vi.spyOn(feesApi, 'getGlobalRules').mockResolvedValue(rules)

    render(<FeesPage />)

    expect(await screen.findByText('$1500.00')).toBeInTheDocument()
    expect(screen.getByText('Mensual')).toBeInTheDocument()
    expect(screen.getByText('10%')).toBeInTheDocument()
    expect(screen.getAllByText('6').length).toBeGreaterThan(0)
  })

  it('no muestra el formulario de alta ni el botón de editar si el rol no es admin', async () => {
    mockUser('tesorero')
    vi.spyOn(feesApi, 'listFees').mockResolvedValue([fee])
    vi.spyOn(feesApi, 'getGlobalRules').mockResolvedValue(rules)

    render(<FeesPage />)

    await screen.findByText('$1500.00')
    expect(screen.queryByPlaceholderText('Monto')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /editar/i })).not.toBeInTheDocument()
  })

  it('un admin puede crear una cuota nueva', async () => {
    mockUser('admin')
    vi.spyOn(feesApi, 'listFees').mockResolvedValue([])
    vi.spyOn(feesApi, 'getGlobalRules').mockResolvedValue(rules)
    const createSpy = vi.spyOn(feesApi, 'createFee').mockResolvedValue(fee)
    const user = userEvent.setup()

    render(<FeesPage />)
    await screen.findByText(/todavía no hay ninguna cuota/i)

    await user.type(screen.getByPlaceholderText('Monto'), '1500')
    await user.type(screen.getByLabelText('Activa desde'), '2026-09-01')
    await user.click(screen.getByRole('button', { name: /agregar cuota/i }))

    await waitFor(() =>
      expect(createSpy).toHaveBeenCalledWith({ monto: 1500, periodicidad: 'mensual', activa_desde: '2026-09-01' }),
    )
  })

  it('un admin puede editar una cuota existente', async () => {
    mockUser('admin')
    vi.spyOn(feesApi, 'listFees').mockResolvedValue([fee])
    vi.spyOn(feesApi, 'getGlobalRules').mockResolvedValue(rules)
    const updateSpy = vi.spyOn(feesApi, 'updateFee').mockResolvedValue(fee)
    const user = userEvent.setup()

    render(<FeesPage />)
    await screen.findByText('$1500.00')

    await user.click(screen.getByRole('button', { name: /editar/i }))
    const montoInput = screen.getByDisplayValue('1500')
    await user.clear(montoInput)
    await user.type(montoInput, '1650')
    await user.click(screen.getByRole('button', { name: /guardar/i }))

    await waitFor(() =>
      expect(updateSpy).toHaveBeenCalledWith('fee-1', { monto: 1650, periodicidad: 'mensual', activa_desde: '2026-09-01' }),
    )
  })

  it('muestra el error del backend si falla la carga', async () => {
    mockUser('admin')
    vi.spyOn(feesApi, 'listFees').mockRejectedValue(new Error('caída'))
    vi.spyOn(feesApi, 'getGlobalRules').mockResolvedValue(rules)

    render(<FeesPage />)

    expect(await screen.findByText(/no se pudo cargar la configuración de cuotas/i)).toBeInTheDocument()
  })
})
