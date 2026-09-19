import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { PaymentProofsPage } from './PaymentProofsPage'
import * as proofsApi from '../api/paymentProofs'
import * as propertiesApi from '../api/properties'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import type { PaymentProof, Property } from '../types'

vi.mock('../auth/AuthContext', () => ({ useAuth: vi.fn() }))

const casa: Property = { id: 'p1', identificador: 'Casa 4', referencia_pago: '0000004', saldo_a_favor: 0 }

function prueba(extra: Partial<PaymentProof> = {}): PaymentProof {
  return {
    id: 'c1',
    property_id: 'p1',
    monto: 750,
    fecha_pago: '2026-09-04',
    nota: 'Transferencia BBVA',
    estado: 'pendiente',
    created_at: '2026-09-05T15:00:00',
    revisado_en: null,
    motivo_rechazo: null,
    payment_id: null,
    archivo_url: 'http://localhost:8000/files/f1/content?t=abc',
    ...extra,
  }
}

function mockUser(rol: string) {
  vi.mocked(useAuth).mockReturnValue({
    user: { sub: 'u1', tenant_id: 't1', schema: 's1', rol, property_id: null, exp: 0 },
    login: vi.fn(),
    logout: vi.fn(),
  })
}

function mockApis(comprobantes: PaymentProof[]) {
  const lista = vi.spyOn(proofsApi, 'listPaymentProofs').mockResolvedValue(comprobantes)
  vi.spyOn(propertiesApi, 'listProperties').mockResolvedValue([casa])
  return lista
}

describe('PaymentProofsPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('lista los comprobantes pendientes con la vivienda, el monto y el enlace al archivo', async () => {
    mockUser('tesorero')
    const lista = mockApis([prueba()])

    render(<PaymentProofsPage />)

    const fila = (await screen.findByText('Casa 4')).closest('tr')!
    expect(within(fila).getByText('$750.00')).toBeInTheDocument()
    expect(within(fila).getByText('Transferencia BBVA')).toBeInTheDocument()
    expect(within(fila).getByRole('link', { name: /ver comprobante/i })).toHaveAttribute(
      'href',
      'http://localhost:8000/files/f1/content?t=abc',
    )
    expect(lista).toHaveBeenCalledWith('pendiente') // por defecto, lo que falta revisar
  })

  it('cambiar el filtro pide los aceptados o rechazados', async () => {
    mockUser('tesorero')
    const lista = mockApis([])
    const user = userEvent.setup()

    render(<PaymentProofsPage />)
    await screen.findByText(/no hay comprobantes pendientes/i)
    await user.click(screen.getByRole('button', { name: 'Rechazado' }))

    await waitFor(() => expect(lista).toHaveBeenLastCalledWith('rechazado'))
  })

  it('acepta el comprobante con el monto declarado', async () => {
    mockUser('tesorero')
    const lista = mockApis([prueba()])
    const aceptar = vi.spyOn(proofsApi, 'acceptPaymentProof').mockResolvedValue(prueba({ estado: 'aceptado' }))
    const user = userEvent.setup()

    render(<PaymentProofsPage />)
    await user.click(await screen.findByRole('button', { name: /aceptar y registrar pago/i }))

    await waitFor(() => expect(aceptar).toHaveBeenCalledWith('c1', {}))
    await waitFor(() => expect(lista).toHaveBeenCalledTimes(2)) // se recarga la lista
  })

  it('tesorería corrige el monto que de verdad llegó', async () => {
    mockUser('admin')
    mockApis([prueba()])
    const aceptar = vi.spyOn(proofsApi, 'acceptPaymentProof').mockResolvedValue(prueba({ estado: 'aceptado' }))
    const user = userEvent.setup()

    render(<PaymentProofsPage />)
    await user.type(await screen.findByLabelText(/monto que llegó/i), '700')
    await user.click(screen.getByRole('button', { name: /aceptar y registrar pago/i }))

    await waitFor(() => expect(aceptar).toHaveBeenCalledWith('c1', { monto: 700 }))
  })

  it('si el SPEI ya detectó ese pago, pide confirmar que es otro antes de contarlo', async () => {
    mockUser('tesorero')
    mockApis([prueba()])
    const aceptar = vi
      .spyOn(proofsApi, 'acceptPaymentProof')
      .mockRejectedValueOnce(new ApiError(409, 'El SPEI ya detectó un pago de $750.00 para esta vivienda el 04/09/2026: probablemente es el mismo.'))
      .mockResolvedValueOnce(prueba({ estado: 'aceptado' }))
    const user = userEvent.setup()

    render(<PaymentProofsPage />)
    await user.click(await screen.findByRole('button', { name: /aceptar y registrar pago/i }))

    expect(await screen.findByText(/el spei ya detectó un pago/i)).toBeInTheDocument()
    expect(aceptar).toHaveBeenCalledTimes(1)
    await user.click(screen.getByRole('button', { name: /es otro pago/i }))

    await waitFor(() => expect(aceptar).toHaveBeenLastCalledWith('c1', { forzar: true }))
  })

  it('rechazar pide un motivo y no se puede confirmar sin él', async () => {
    mockUser('tesorero')
    mockApis([prueba()])
    const rechazar = vi.spyOn(proofsApi, 'rejectPaymentProof').mockResolvedValue(prueba({ estado: 'rechazado' }))
    const user = userEvent.setup()

    render(<PaymentProofsPage />)
    await user.click(await screen.findByRole('button', { name: 'Rechazar' }))
    expect(screen.getByRole('button', { name: /confirmar rechazo/i })).toBeDisabled()

    await user.type(screen.getByPlaceholderText('Motivo del rechazo'), 'Comprobante ilegible')
    await user.click(screen.getByRole('button', { name: /confirmar rechazo/i }))

    await waitFor(() => expect(rechazar).toHaveBeenCalledWith('c1', 'Comprobante ilegible'))
  })

  it('los ya revisados no ofrecen acciones y los rechazados muestran su motivo', async () => {
    mockUser('tesorero')
    mockApis([prueba({ estado: 'rechazado', motivo_rechazo: 'No llegó el dinero' })])
    const user = userEvent.setup()

    render(<PaymentProofsPage />)
    await user.click(await screen.findByRole('button', { name: 'Rechazado' }))

    expect(await screen.findByText('No llegó el dinero')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /aceptar y registrar pago/i })).not.toBeInTheDocument()
  })

  it('muestra otros errores del backend al aceptar', async () => {
    mockUser('tesorero')
    mockApis([prueba()])
    vi.spyOn(proofsApi, 'acceptPaymentProof').mockRejectedValue(new ApiError(409, 'Este comprobante ya fue revisado'))
    const user = userEvent.setup()

    render(<PaymentProofsPage />)
    await user.click(await screen.findByRole('button', { name: /aceptar y registrar pago/i }))

    expect(await screen.findByText('Este comprobante ya fue revisado')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /es otro pago/i })).not.toBeInTheDocument()
  })

  it('un rol sin acceso no ve los comprobantes ni los pide', () => {
    mockUser('residente')
    const lista = mockApis([prueba()])

    render(<PaymentProofsPage />)

    expect(screen.getByText(/no tienes acceso a esta vista/i)).toBeInTheDocument()
    expect(lista).not.toHaveBeenCalled()
  })
})
