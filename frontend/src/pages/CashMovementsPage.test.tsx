import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { CashMovementsPage } from './CashMovementsPage'
import * as cashApi from '../api/cashMovements'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import type { CashBalance, CashMovement } from '../types'

vi.mock('../auth/AuthContext', () => ({ useAuth: vi.fn() }))

const saldo: CashBalance = { chica: 1500, grande: 20000 }

function movimiento(extra: Partial<CashMovement> = {}): CashMovement {
  return { id: 'm1', caja: 'chica', tipo: 'ingreso', monto: 500, motivo: 'Fondo inicial', fecha: '2026-09-10', registrado_por: 'u1', ...extra }
}

function mockUser(rol: string) {
  vi.mocked(useAuth).mockReturnValue({
    user: { sub: 'u1', tenant_id: 't1', schema: 's1', rol, property_id: null, exp: 0 },
    login: vi.fn(),
    logout: vi.fn(),
  })
}

function mockApis(movimientos: CashMovement[], balance: CashBalance = saldo) {
  vi.spyOn(cashApi, 'listCashMovements').mockResolvedValue(movimientos)
  vi.spyOn(cashApi, 'getCashBalance').mockResolvedValue(balance)
}

describe('CashMovementsPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('muestra el saldo de ambas cajas y el historial', async () => {
    mockUser('admin')
    mockApis([movimiento()])

    render(<CashMovementsPage />)

    expect(await screen.findByText('$1,500')).toBeInTheDocument()
    expect(screen.getByText('$20,000')).toBeInTheDocument()
    expect(screen.getByText('Fondo inicial')).toBeInTheDocument()
  })

  it('tesorería ve el formulario para registrar un movimiento y lo envía', async () => {
    mockUser('tesorero')
    mockApis([])
    const spy = vi.spyOn(cashApi, 'createCashMovement').mockResolvedValue(movimiento())
    const user = userEvent.setup()

    render(<CashMovementsPage />)
    await screen.findByText('$1,500')

    await user.type(screen.getByLabelText('Monto'), '500')
    await user.type(screen.getByLabelText('Motivo'), 'Compra de papelería')
    // userEvent.type no funciona con <input type="date">: se cambia el valor directo.
    fireEvent.change(screen.getByLabelText('Fecha'), { target: { value: '2026-09-15' } })
    await user.click(screen.getByRole('button', { name: /registrar movimiento/i }))

    await waitFor(() =>
      expect(spy).toHaveBeenCalledWith({ caja: 'chica', tipo: 'ingreso', monto: 500, motivo: 'Compra de papelería', fecha: '2026-09-15' }),
    )
  })

  it('un admin no ve el formulario de captura, solo el historial', async () => {
    mockUser('admin')
    mockApis([movimiento()])

    render(<CashMovementsPage />)
    await screen.findByText('$1,500')

    expect(screen.queryByRole('button', { name: /registrar movimiento/i })).not.toBeInTheDocument()
  })

  it('sin movimientos lo dice', async () => {
    mockUser('tesorero')
    mockApis([])

    render(<CashMovementsPage />)

    expect(await screen.findByText(/todavía no hay movimientos/i)).toBeInTheDocument()
  })

  it('un rol sin acceso no ve la caja ni la pide', async () => {
    mockUser('guardia')
    mockApis([movimiento()])

    render(<CashMovementsPage />)

    expect(screen.getByText(/no tienes acceso a esta vista/i)).toBeInTheDocument()
    expect(cashApi.listCashMovements).not.toHaveBeenCalled()
  })

  it('muestra el error del backend si falla la carga', async () => {
    mockUser('tesorero')
    vi.spyOn(cashApi, 'listCashMovements').mockRejectedValue(new ApiError(500, 'Error del servidor'))
    vi.spyOn(cashApi, 'getCashBalance').mockResolvedValue(saldo)

    render(<CashMovementsPage />)

    expect(await screen.findByText('Error del servidor')).toBeInTheDocument()
  })
})
