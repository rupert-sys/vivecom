import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { FeesPage } from './FeesPage'
import * as feesApi from '../api/fees'
import * as reglamentoApi from '../api/reglamento'
import { useAuth } from '../auth/AuthContext'
import type { Fee, Reglamento } from '../types'

vi.mock('../auth/AuthContext', () => ({ useAuth: vi.fn() }))

const fee: Fee = { id: 'fee-1', monto: 1500, periodicidad: 'mensual', activa_desde: '2026-09-01' }
// El backend regresa recargo_porcentaje como fracción (0.10 = 10%), no como entero.
const rules: Reglamento = {
  dia_limite_pago: 5,
  dia_recargo: 6,
  recargo_porcentaje: 0.1,
  recargo_modalidad: 'unico',
  acepta_pago_efectivo: false,
  morosos_sin_voto: false,
  morosos_sin_areas_comunes: false,
  gasto_umbral_asamblea: null,
  cotizaciones_minimas: 3,
  cajones_visitas: 0,
  horas_max_estacionamiento_visitas: 24,
  dudas_en_avisos_por_defecto: false,
  prorroga_max_meses: 3,
}

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
    vi.spyOn(reglamentoApi, 'getReglamento').mockResolvedValue(rules)

    render(
      <MemoryRouter>
        <FeesPage />
      </MemoryRouter>,
    )

    const fila = (await screen.findByText('$1500.00')).closest('tr')!
    expect(within(fila).getByText('Mensual')).toBeInTheDocument()
    expect(screen.getByText('10%')).toBeInTheDocument()
    expect(screen.getAllByText('6').length).toBeGreaterThan(0)
  })

  it('no muestra el formulario de alta ni el botón de editar si el rol no es tesorero', async () => {
    mockUser('admin')
    vi.spyOn(feesApi, 'listFees').mockResolvedValue([fee])
    vi.spyOn(reglamentoApi, 'getReglamento').mockResolvedValue(rules)

    render(
      <MemoryRouter>
        <FeesPage />
      </MemoryRouter>,
    )

    await screen.findByText('$1500.00')
    expect(screen.queryByPlaceholderText('Monto')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /editar/i })).not.toBeInTheDocument()
  })

  it('tesorería puede crear una cuota nueva', async () => {
    mockUser('tesorero')
    vi.spyOn(feesApi, 'listFees').mockResolvedValue([])
    vi.spyOn(reglamentoApi, 'getReglamento').mockResolvedValue(rules)
    const createSpy = vi.spyOn(feesApi, 'createFee').mockResolvedValue(fee)
    const user = userEvent.setup()

    render(
      <MemoryRouter>
        <FeesPage />
      </MemoryRouter>,
    )
    await screen.findByText(/todavía no hay ninguna cuota/i)

    await user.type(screen.getByPlaceholderText('Monto'), '1500')
    await user.type(screen.getByLabelText('Activa desde'), '2026-09-01')
    await user.click(screen.getByRole('button', { name: /agregar cuota/i }))

    await waitFor(() =>
      expect(createSpy).toHaveBeenCalledWith({ monto: 1500, periodicidad: 'mensual', activa_desde: '2026-09-01' }),
    )
  })

  it('tesorería puede editar una cuota existente', async () => {
    mockUser('tesorero')
    vi.spyOn(feesApi, 'listFees').mockResolvedValue([fee])
    vi.spyOn(reglamentoApi, 'getReglamento').mockResolvedValue(rules)
    const updateSpy = vi.spyOn(feesApi, 'updateFee').mockResolvedValue(fee)
    const user = userEvent.setup()

    render(
      <MemoryRouter>
        <FeesPage />
      </MemoryRouter>,
    )
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
    vi.spyOn(reglamentoApi, 'getReglamento').mockResolvedValue(rules)

    render(
      <MemoryRouter>
        <FeesPage />
      </MemoryRouter>,
    )

    expect(await screen.findByText(/no se pudo cargar la configuración de cuotas/i)).toBeInTheDocument()
  })

  it('muestra el recargo del reglamento del condominio, no un valor global', async () => {
    mockUser('admin')
    vi.spyOn(feesApi, 'listFees').mockResolvedValue([fee])
    vi.spyOn(reglamentoApi, 'getReglamento').mockResolvedValue({
      ...rules,
      recargo_porcentaje: 0.05,
      recargo_modalidad: 'mensual_sobre_saldo',
    })

    render(
      <MemoryRouter>
        <FeesPage />
      </MemoryRouter>,
    )

    expect(await screen.findByText('5%')).toBeInTheDocument()
    expect(screen.getByText(/mensual sobre el saldo vencido/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /cambiar en reglamento/i })).toBeInTheDocument()
  })

  it('a quien no es admin no se le ofrece cambiar el reglamento desde aquí', async () => {
    mockUser('tesorero')
    vi.spyOn(feesApi, 'listFees').mockResolvedValue([fee])
    vi.spyOn(reglamentoApi, 'getReglamento').mockResolvedValue(rules)

    render(
      <MemoryRouter>
        <FeesPage />
      </MemoryRouter>,
    )

    await screen.findByText('10%')
    expect(screen.queryByRole('link', { name: /cambiar en reglamento/i })).not.toBeInTheDocument()
  })

  it('tesorería puede eliminar una cuota, con confirmación', async () => {
    mockUser('tesorero')
    vi.spyOn(feesApi, 'listFees').mockResolvedValue([fee])
    vi.spyOn(reglamentoApi, 'getReglamento').mockResolvedValue(rules)
    const deleteSpy = vi.spyOn(feesApi, 'deleteFee').mockResolvedValue()
    const confirmar = vi.spyOn(window, 'confirm').mockReturnValueOnce(false).mockReturnValueOnce(true)
    const user = userEvent.setup()

    render(
      <MemoryRouter>
        <FeesPage />
      </MemoryRouter>,
    )
    await screen.findByText('$1500.00')

    await user.click(screen.getByRole('button', { name: /eliminar/i }))
    expect(deleteSpy).not.toHaveBeenCalled()

    await user.click(screen.getByRole('button', { name: /eliminar/i }))
    await waitFor(() => expect(deleteSpy).toHaveBeenCalledWith('fee-1'))
    expect(confirmar).toHaveBeenCalledTimes(2)
  })

  it('si la cuota ya generó cargos, muestra el motivo del backend en vez de eliminarla', async () => {
    mockUser('tesorero')
    vi.spyOn(feesApi, 'listFees').mockResolvedValue([fee])
    vi.spyOn(reglamentoApi, 'getReglamento').mockResolvedValue(rules)
    const { ApiError } = await import('../api/client')
    vi.spyOn(feesApi, 'deleteFee').mockRejectedValue(new ApiError(409, 'Esta cuota ya generó cargos: no se puede eliminar, solo editar.'))
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const user = userEvent.setup()

    render(
      <MemoryRouter>
        <FeesPage />
      </MemoryRouter>,
    )
    await screen.findByText('$1500.00')

    await user.click(screen.getByRole('button', { name: /eliminar/i }))

    expect(await screen.findByText(/ya generó cargos/i)).toBeInTheDocument()
    expect(screen.getByText('$1500.00')).toBeInTheDocument() // sigue en la lista
  })

  it('un pago único pide el periodo al que aplica, no una fecha de "activa desde"', async () => {
    mockUser('tesorero')
    vi.spyOn(feesApi, 'listFees').mockResolvedValue([])
    vi.spyOn(reglamentoApi, 'getReglamento').mockResolvedValue(rules)
    const createSpy = vi.spyOn(feesApi, 'createFee').mockResolvedValue({ ...fee, periodicidad: 'unica' })
    const user = userEvent.setup()

    render(
      <MemoryRouter>
        <FeesPage />
      </MemoryRouter>,
    )
    await screen.findByText(/todavía no hay ninguna cuota/i)

    await user.selectOptions(screen.getByDisplayValue('Mensual'), 'unica')
    expect(screen.getByText(/genera un cargo una sola vez/i)).toBeInTheDocument()

    await user.type(screen.getByPlaceholderText('Monto'), '5000')
    await user.type(screen.getByLabelText('Periodo'), '2026-12-01')
    await user.click(screen.getByRole('button', { name: /agregar cuota/i }))

    await waitFor(() =>
      expect(createSpy).toHaveBeenCalledWith({ monto: 5000, periodicidad: 'unica', activa_desde: '2026-12-01' }),
    )
  })

  it('la tabla muestra "Pago único" para una cuota con esa periodicidad', async () => {
    mockUser('tesorero')
    vi.spyOn(feesApi, 'listFees').mockResolvedValue([{ ...fee, periodicidad: 'unica' }])
    vi.spyOn(reglamentoApi, 'getReglamento').mockResolvedValue(rules)

    render(
      <MemoryRouter>
        <FeesPage />
      </MemoryRouter>,
    )

    expect(await screen.findByText('Pago único')).toBeInTheDocument()
  })

  it('se puede elegir y crear una cuota con periodicidad semanal', async () => {
    mockUser('tesorero')
    vi.spyOn(feesApi, 'listFees').mockResolvedValue([])
    vi.spyOn(reglamentoApi, 'getReglamento').mockResolvedValue(rules)
    const createSpy = vi.spyOn(feesApi, 'createFee').mockResolvedValue({ ...fee, periodicidad: 'semanal' })
    const user = userEvent.setup()

    render(
      <MemoryRouter>
        <FeesPage />
      </MemoryRouter>,
    )
    await screen.findByText(/todavía no hay ninguna cuota/i)

    await user.selectOptions(screen.getByDisplayValue('Mensual'), 'semanal')
    await user.type(screen.getByPlaceholderText('Monto'), '200')
    await user.type(screen.getByLabelText('Activa desde'), '2026-09-01')
    await user.click(screen.getByRole('button', { name: /agregar cuota/i }))

    await waitFor(() =>
      expect(createSpy).toHaveBeenCalledWith({ monto: 200, periodicidad: 'semanal', activa_desde: '2026-09-01' }),
    )
  })

  it('la tabla muestra "Semanal" para una cuota con esa periodicidad', async () => {
    mockUser('tesorero')
    vi.spyOn(feesApi, 'listFees').mockResolvedValue([{ ...fee, periodicidad: 'semanal' }])
    vi.spyOn(reglamentoApi, 'getReglamento').mockResolvedValue(rules)

    render(
      <MemoryRouter>
        <FeesPage />
      </MemoryRouter>,
    )

    expect(await screen.findByText('Semanal')).toBeInTheDocument()
  })
})
