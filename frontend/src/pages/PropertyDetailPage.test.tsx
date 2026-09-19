import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { PropertyDetailPage } from './PropertyDetailPage'
import * as propertiesApi from '../api/properties'
import * as residentsApi from '../api/residents'
import * as paymentsApi from '../api/payments'
import * as reglamentoApi from '../api/reglamento'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import type { AccountStatement, Reglamento, Resident } from '../types'

vi.mock('../auth/AuthContext', () => ({ useAuth: vi.fn() }))

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

const cuenta: AccountStatement = {
  property_id: 'prop-1',
  identificador: 'Casa 1',
  saldo_a_favor: 50,
  deuda_total: 1500,
  en_mora: true,
  restricciones_por_mora: ['No puedes votar en las votaciones.', 'No puedes reservar áreas comunes.'],
}

const resident: Resident = { id: 'res-1', nombre: 'Ana Pérez', telefono: '5511112222', email: null }

function mockUser(rol: string) {
  vi.mocked(useAuth).mockReturnValue({
    user: { sub: 'u1', tenant_id: 't1', schema: 's1', rol, property_id: null, exp: 0 },
    login: vi.fn(),
    logout: vi.fn(),
  })
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/properties/prop-1']}>
      <Routes>
        <Route path="/properties/:propertyId" element={<PropertyDetailPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('PropertyDetailPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(paymentsApi, 'getAccountStatement').mockResolvedValue(cuenta)
    vi.spyOn(reglamentoApi, 'getReglamento').mockResolvedValue(reglamento)
  })

  it('lista a los residentes ligados a la vivienda', async () => {
    mockUser('admin')
    vi.spyOn(propertiesApi, 'listPropertyResidents').mockResolvedValue([resident])

    renderPage()

    expect(await screen.findByText(/Ana Pérez/)).toBeInTheDocument()
    expect(screen.getByText(/5511112222/)).toBeInTheDocument()
  })

  it('un admin puede agregar un residente nuevo (crear + ligar)', async () => {
    mockUser('admin')
    vi.spyOn(propertiesApi, 'listPropertyResidents').mockResolvedValue([])
    const createSpy = vi.spyOn(residentsApi, 'createResident').mockResolvedValue(resident)
    const linkSpy = vi.spyOn(propertiesApi, 'linkResidentToProperty').mockResolvedValue(undefined)
    const user = userEvent.setup()

    renderPage()
    await screen.findByText(/todavía no tiene residentes/i)

    await user.type(screen.getByPlaceholderText('Nombre'), 'Ana Pérez')
    await user.type(screen.getByPlaceholderText('Teléfono'), '5511112222')
    await user.click(screen.getByRole('button', { name: /^agregar$/i }))

    await waitFor(() => expect(createSpy).toHaveBeenCalledWith({ nombre: 'Ana Pérez', telefono: '5511112222', email: undefined }))
    await waitFor(() => expect(linkSpy).toHaveBeenCalledWith('prop-1', 'res-1', 'propietario'))
  })

  it('un no-admin no ve el formulario de agregar residente ni el botón de quitar', async () => {
    mockUser('guardia')
    vi.spyOn(propertiesApi, 'listPropertyResidents').mockResolvedValue([resident])

    renderPage()

    await screen.findByText(/Ana Pérez/)
    expect(screen.queryByPlaceholderText('Nombre')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /quitar/i })).not.toBeInTheDocument()
  })

  it('el tesorero ve la deuda, el saldo a favor y las restricciones de una vivienda en mora', async () => {
    mockUser('tesorero')
    vi.spyOn(propertiesApi, 'listPropertyResidents').mockResolvedValue([resident])

    renderPage()

    expect(await screen.findByText('$1500.00')).toBeInTheDocument()
    expect(screen.getByText('$50.00')).toBeInTheDocument()
    expect(screen.getByText(/vivienda en mora/i)).toBeInTheDocument()
    expect(screen.getByText('No puedes votar en las votaciones.')).toBeInTheDocument()
  })

  it('una vivienda al corriente no muestra el aviso de mora', async () => {
    mockUser('tesorero')
    vi.spyOn(propertiesApi, 'listPropertyResidents').mockResolvedValue([])
    vi.spyOn(paymentsApi, 'getAccountStatement').mockResolvedValue({ ...cuenta, en_mora: false, restricciones_por_mora: [], deuda_total: 0 })

    renderPage()

    expect(await screen.findByText('$0.00')).toBeInTheDocument()
    expect(screen.queryByText(/vivienda en mora/i)).not.toBeInTheDocument()
  })

  it('el tesorero registra un pago en efectivo y el estado de cuenta se refresca', async () => {
    mockUser('tesorero')
    vi.spyOn(propertiesApi, 'listPropertyResidents').mockResolvedValue([])
    const pagoSpy = vi.spyOn(paymentsApi, 'createManualPayment').mockResolvedValue({})
    const cuentaSpy = vi.spyOn(paymentsApi, 'getAccountStatement').mockResolvedValue(cuenta)
    const user = userEvent.setup()

    renderPage()
    await user.type(await screen.findByPlaceholderText('Monto del pago'), '750')
    await user.selectOptions(screen.getByLabelText('Forma de pago'), 'efectivo')
    await user.click(screen.getByRole('button', { name: /registrar pago/i }))

    await waitFor(() => expect(pagoSpy).toHaveBeenCalledWith('prop-1', 750, 'efectivo'))
    expect(await screen.findByText('Pago registrado.')).toBeInTheDocument()
    expect(cuentaSpy).toHaveBeenCalledTimes(2) // al abrir y después del pago
  })

  it('si el condominio no acepta efectivo, esa forma de pago no se ofrece', async () => {
    mockUser('tesorero')
    vi.spyOn(propertiesApi, 'listPropertyResidents').mockResolvedValue([])
    vi.spyOn(reglamentoApi, 'getReglamento').mockResolvedValue({ ...reglamento, acepta_pago_efectivo: false })

    renderPage()
    const forma = await screen.findByLabelText('Forma de pago')

    await waitFor(() => expect(within(forma).queryByRole('option', { name: 'Efectivo' })).not.toBeInTheDocument())
    expect(within(forma).getByRole('option', { name: 'Transferencia' })).toBeInTheDocument()
  })

  it('muestra el rechazo del backend al registrar el pago', async () => {
    mockUser('admin')
    vi.spyOn(propertiesApi, 'listPropertyResidents').mockResolvedValue([])
    vi.spyOn(paymentsApi, 'createManualPayment').mockRejectedValue(
      new ApiError(409, 'Este condominio no acepta pagos en efectivo'),
    )
    const user = userEvent.setup()

    renderPage()
    await user.type(await screen.findByPlaceholderText('Monto del pago'), '750')
    await user.click(screen.getByRole('button', { name: /registrar pago/i }))

    expect(await screen.findByText('Este condominio no acepta pagos en efectivo')).toBeInTheDocument()
    expect(screen.queryByText('Pago registrado.')).not.toBeInTheDocument()
  })

  it('otros roles no ven el estado de cuenta ni piden esos datos', async () => {
    mockUser('comite_lectura')
    vi.spyOn(propertiesApi, 'listPropertyResidents').mockResolvedValue([resident])

    renderPage()

    await screen.findByText(/Ana Pérez/)
    expect(screen.queryByText('Estado de cuenta')).not.toBeInTheDocument()
    expect(paymentsApi.getAccountStatement).not.toHaveBeenCalled()
  })

  it('si el estado de cuenta no carga, los residentes se siguen mostrando', async () => {
    mockUser('tesorero')
    vi.spyOn(propertiesApi, 'listPropertyResidents').mockResolvedValue([resident])
    vi.spyOn(paymentsApi, 'getAccountStatement').mockRejectedValue(new Error('caída'))

    renderPage()

    expect(await screen.findByText(/Ana Pérez/)).toBeInTheDocument()
    expect(screen.queryByText('Estado de cuenta')).not.toBeInTheDocument()
  })
})
