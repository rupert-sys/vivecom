import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { PaymentAgreementsPage } from './PaymentAgreementsPage'
import * as agreementsApi from '../api/paymentAgreements'
import * as filesApi from '../api/files'
import * as propertiesApi from '../api/properties'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import type { PaymentAgreement, Property } from '../types'

vi.mock('../auth/AuthContext', () => ({ useAuth: vi.fn() }))

const casa: Property = { id: 'p1', identificador: 'Casa 4', referencia_pago: '0000004', saldo_a_favor: 0 }

function acuerdo(extra: Partial<PaymentAgreement> = {}): PaymentAgreement {
  return {
    id: 'a1',
    property_id: 'p1',
    vivienda: 'Casa 4',
    estado: 'solicitado',
    causa: 'Perdí mi empleo en agosto y regularizo mis ingresos.',
    propuesta_pagos: 3,
    propuesta_primer_pago: '2026-10-05',
    capturado_por_admin: false,
    created_at: '2026-09-18T15:00:00',
    decidido_en: null,
    motivo_rechazo: null,
    archivo_url: null,
    vigente_desde: null,
    calendario: null,
    congela_recargo: null,
    deuda_inicial: null,
    abonado: null,
    pendiente_cubierto: null,
    proximo_pago: null,
    incumplimientos_previos: 0,
    ...extra,
  }
}

const vigente = acuerdo({
  id: 'v1',
  estado: 'vigente',
  vivienda: 'Casa 7',
  deuda_inicial: 750,
  abonado: 250,
  pendiente_cubierto: 500,
  congela_recargo: true,
  calendario: [
    { fecha: '2026-10-05', monto: 250 },
    { fecha: '2026-11-05', monto: 250 },
    { fecha: '2026-12-05', monto: 250 },
  ],
  proximo_pago: { fecha: '2026-11-05', monto: 250 },
})

function mockUser(rol: string) {
  vi.mocked(useAuth).mockReturnValue({
    user: { sub: 'u1', tenant_id: 't1', schema: 's1', rol, property_id: null, exp: 0 },
    login: vi.fn(),
    logout: vi.fn(),
  })
}

function mockApis(acuerdos: PaymentAgreement[]) {
  const lista = vi.spyOn(agreementsApi, 'listPaymentAgreements').mockResolvedValue(acuerdos)
  vi.spyOn(propertiesApi, 'listProperties').mockResolvedValue([casa])
  return lista
}

describe('PaymentAgreementsPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('muestra la solicitud con la causa, lo que propone y el documento de respaldo', async () => {
    mockUser('comite_aprobador')
    mockApis([acuerdo({ archivo_url: 'http://localhost:8000/files/f1/content?t=abc' })])

    render(<PaymentAgreementsPage />)

    expect(await screen.findByText(/Perdí mi empleo/)).toBeInTheDocument()
    expect(screen.getByText(/Casa 4 · solicitado el/)).toBeInTheDocument()
    expect(screen.getByText('3 pagos mensuales')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /documento de respaldo/i })).toHaveAttribute('href', 'http://localhost:8000/files/f1/content?t=abc')
    expect(screen.getByText('Por decidir (1)')).toBeInTheDocument()
  })

  it('una sola fecha se lee como "pagar todo"', async () => {
    mockUser('admin')
    mockApis([acuerdo({ propuesta_pagos: 1 })])

    render(<PaymentAgreementsPage />)

    expect(await screen.findByText('pagar todo')).toBeInTheDocument()
  })

  it('el comité aprueba con el recargo congelado por defecto', async () => {
    mockUser('comite_aprobador')
    const lista = mockApis([acuerdo()])
    const aprobar = vi.spyOn(agreementsApi, 'approvePaymentAgreement').mockResolvedValue(vigente)
    const user = userEvent.setup({ delay: null })

    render(<PaymentAgreementsPage />)
    expect(await screen.findByLabelText(/congelar el recargo/i)).toBeChecked()
    await user.click(screen.getByRole('button', { name: /aprobar acuerdo/i }))

    await waitFor(() => expect(aprobar).toHaveBeenCalledWith('a1', { congela_recargo: true }))
    await waitFor(() => expect(lista).toHaveBeenCalledTimes(2)) // se recarga la lista
  })

  it('el comité decide no congelar el recargo', async () => {
    mockUser('admin')
    mockApis([acuerdo()])
    const aprobar = vi.spyOn(agreementsApi, 'approvePaymentAgreement').mockResolvedValue(vigente)
    const user = userEvent.setup({ delay: null })

    render(<PaymentAgreementsPage />)
    await user.click(await screen.findByLabelText(/congelar el recargo/i))
    await user.click(screen.getByRole('button', { name: /aprobar acuerdo/i }))

    await waitFor(() => expect(aprobar).toHaveBeenCalledWith('a1', { congela_recargo: false }))
  })

  it('aprueba con otro calendario que el propuesto', async () => {
    mockUser('comite_aprobador')
    mockApis([acuerdo()])
    const aprobar = vi.spyOn(agreementsApi, 'approvePaymentAgreement').mockResolvedValue(vigente)
    const user = userEvent.setup({ delay: null })

    render(<PaymentAgreementsPage />)
    await user.click(await screen.findByRole('button', { name: /proponer otro calendario/i }))
    await user.type(screen.getByLabelText('Fecha del pago 1'), '2026-10-10')
    await user.type(screen.getByLabelText('Monto del pago 1'), '500')
    await user.click(screen.getByRole('button', { name: /agregar pago/i }))
    await user.type(screen.getByLabelText('Fecha del pago 2'), '2026-11-10')
    await user.type(screen.getByLabelText('Monto del pago 2'), '250')
    await user.click(screen.getByRole('button', { name: /aprobar acuerdo/i }))

    await waitFor(() =>
      expect(aprobar).toHaveBeenCalledWith('a1', {
        congela_recargo: true,
        pagos: [
          { fecha: '2026-10-10', monto: 500 },
          { fecha: '2026-11-10', monto: 250 },
        ],
      }),
    )
  })

  it('volver al calendario propuesto descarta el propio', async () => {
    mockUser('comite_aprobador')
    mockApis([acuerdo()])
    const aprobar = vi.spyOn(agreementsApi, 'approvePaymentAgreement').mockResolvedValue(vigente)
    const user = userEvent.setup({ delay: null })

    render(<PaymentAgreementsPage />)
    await user.click(await screen.findByRole('button', { name: /proponer otro calendario/i }))
    await user.click(screen.getByRole('button', { name: /usar el propuesto/i }))
    await user.click(screen.getByRole('button', { name: /aprobar acuerdo/i }))

    await waitFor(() => expect(aprobar).toHaveBeenCalledWith('a1', { congela_recargo: true }))
  })

  it('rechazar pide el motivo y no se puede confirmar sin él', async () => {
    mockUser('comite_aprobador')
    mockApis([acuerdo()])
    const rechazar = vi.spyOn(agreementsApi, 'rejectPaymentAgreement').mockResolvedValue(acuerdo({ estado: 'rechazado' }))
    const user = userEvent.setup({ delay: null })

    render(<PaymentAgreementsPage />)
    await user.click(await screen.findByRole('button', { name: 'Rechazar' }))
    expect(screen.getByRole('button', { name: /confirmar rechazo/i })).toBeDisabled()
    await user.type(screen.getByPlaceholderText('Motivo del rechazo'), 'No se acreditó la causa')
    await user.click(screen.getByRole('button', { name: /confirmar rechazo/i }))

    await waitFor(() => expect(rechazar).toHaveBeenCalledWith('a1', 'No se acreditó la causa'))
  })

  it('avisa si la vivienda ya incumplió un acuerdo anterior', async () => {
    mockUser('comite_aprobador')
    mockApis([acuerdo({ incumplimientos_previos: 2 })])

    render(<PaymentAgreementsPage />)

    expect(await screen.findByText(/ya incumplió 2 acuerdos anteriores/i)).toBeInTheDocument()
  })

  it('los vigentes muestran el avance, el próximo pago y si el recargo está congelado', async () => {
    mockUser('tesorero')
    mockApis([vigente, { ...vigente, id: 'v2', vivienda: 'Casa 8', congela_recargo: false }])

    render(<PaymentAgreementsPage />)

    const fila = (await screen.findByText('Casa 7')).closest('tr')!
    expect(within(fila).getByText('$750.00')).toBeInTheDocument()
    expect(within(fila).getByText('$250.00', { selector: 'td' })).toBeInTheDocument() // abonado
    expect(within(fila).getByText('$500.00')).toBeInTheDocument() // falta
    expect(within(fila).getByText('$250.00 el 2026-11-05')).toBeInTheDocument()
    expect(within(fila).getByText('Congelado')).toBeInTheDocument()
    expect(within(screen.getByText('Casa 8').closest('tr')!).getByText('Sigue corriendo')).toBeInTheDocument()
    expect(screen.getByText('$1000.00')).toBeInTheDocument() // deuda que cubren los dos vigentes
  })

  it('el administrador o el comité cancelan un acuerdo vigente, previa confirmación', async () => {
    mockUser('comite_aprobador')
    mockApis([vigente])
    const cancelar = vi.spyOn(agreementsApi, 'cancelPaymentAgreement').mockResolvedValue(acuerdo({ estado: 'cancelado' }))
    const confirmacion = vi.spyOn(window, 'confirm').mockReturnValueOnce(false).mockReturnValueOnce(true)
    const user = userEvent.setup({ delay: null })

    render(<PaymentAgreementsPage />)
    await user.click(await screen.findByRole('button', { name: /cancelar acuerdo/i }))
    expect(cancelar).not.toHaveBeenCalled() // dijo que no
    await user.click(screen.getByRole('button', { name: /cancelar acuerdo/i }))

    await waitFor(() => expect(cancelar).toHaveBeenCalledWith('v1'))
    expect(confirmacion).toHaveBeenCalledTimes(2)
  })

  it('tesorería y el comité de solo lectura ven todo pero no pueden decidir', async () => {
    mockApis([acuerdo(), vigente])
    for (const rol of ['tesorero', 'comite_lectura']) {
      mockUser(rol)
      const { unmount } = render(<PaymentAgreementsPage />)

      expect(await screen.findByText(/Perdí mi empleo/)).toBeInTheDocument()
      expect(screen.queryByRole('button', { name: /aprobar acuerdo/i })).not.toBeInTheDocument()
      expect(screen.queryByRole('button', { name: 'Rechazar' })).not.toBeInTheDocument()
      expect(screen.queryByRole('button', { name: /cancelar acuerdo/i })).not.toBeInTheDocument()
      expect(screen.getByText(/no puedes decidir/i)).toBeInTheDocument()
      unmount()
    }
  })

  it('el historial muestra el motivo de un rechazo', async () => {
    mockUser('admin')
    mockApis([acuerdo({ id: 'r1', estado: 'rechazado', motivo_rechazo: 'No se acreditó la causa' }), acuerdo({ id: 'c1', estado: 'incumplido', vivienda: 'Casa 9', deuda_inicial: 900 })])

    render(<PaymentAgreementsPage />)

    expect(await screen.findByText('No se acreditó la causa')).toBeInTheDocument()
    expect(screen.getByText('Incumplido')).toBeInTheDocument()
    expect(screen.getByText('Deuda acordada $900.00')).toBeInTheDocument()
  })

  it('el administrador captura el escrito de un vecino con su documento', async () => {
    mockUser('admin')
    mockApis([])
    const subir = vi
      .spyOn(filesApi, 'uploadFile')
      .mockResolvedValue({ id: 'arch-1', nombre_original: 'carta.pdf', content_type: 'application/pdf', size: 10, ref: '/files/arch-1' })
    const solicitar = vi.spyOn(agreementsApi, 'requestPaymentAgreement').mockResolvedValue(acuerdo({ capturado_por_admin: true }))
    const user = userEvent.setup({ delay: null })

    render(<PaymentAgreementsPage />)
    await user.click(await screen.findByText(/capturar la solicitud por escrito/i))
    await user.selectOptions(screen.getByLabelText('Vivienda del acuerdo'), 'p1')
    await user.type(screen.getByPlaceholderText(/causa justificada/i), 'Gastos médicos imprevistos de la familia.')
    await user.selectOptions(screen.getByLabelText('Número de pagos'), '2')
    await user.type(screen.getByLabelText('Primer pago'), '2026-10-05')
    await user.upload(screen.getByLabelText('Documento de respaldo'), new File(['%PDF-1.7'], 'carta.pdf', { type: 'application/pdf' }))
    await user.click(screen.getByRole('button', { name: /registrar solicitud/i }))

    await waitFor(() => expect(solicitar).toHaveBeenCalled())
    expect(subir).toHaveBeenCalledWith(expect.any(File), 'acuerdo')
    expect(solicitar).toHaveBeenCalledWith({
      property_id: 'p1',
      causa: 'Gastos médicos imprevistos de la familia.',
      numero_de_pagos: 2,
      primer_pago: '2026-10-05',
      archivo_id: 'arch-1',
    })
  })

  it('solo el administrador ve el formulario de captura', async () => {
    mockUser('comite_aprobador')
    mockApis([])

    render(<PaymentAgreementsPage />)

    await screen.findByText('No hay solicitudes por decidir.')
    expect(screen.queryByText(/capturar la solicitud por escrito/i)).not.toBeInTheDocument()
  })

  it('muestra el error del backend al aprobar (calendario que no suma la deuda)', async () => {
    mockUser('comite_aprobador')
    mockApis([acuerdo()])
    vi.spyOn(agreementsApi, 'approvePaymentAgreement').mockRejectedValue(new ApiError(422, 'Los pagos deben sumar la deuda cubierta ($750.00).'))
    const user = userEvent.setup({ delay: null })

    render(<PaymentAgreementsPage />)
    await user.click(await screen.findByRole('button', { name: /aprobar acuerdo/i }))

    expect(await screen.findByText(/deben sumar la deuda cubierta/i)).toBeInTheDocument()
  })

  it('un rol sin acceso no ve los acuerdos ni los pide', () => {
    mockUser('residente')
    const lista = mockApis([acuerdo()])

    render(<PaymentAgreementsPage />)

    expect(screen.getByText(/no tienes acceso a esta vista/i)).toBeInTheDocument()
    expect(lista).not.toHaveBeenCalled()
  })
})
