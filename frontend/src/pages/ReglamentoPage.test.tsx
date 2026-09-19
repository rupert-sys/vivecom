import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ReglamentoPage } from './ReglamentoPage'
import * as reglamentoApi from '../api/reglamento'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import type { Reglamento } from '../types'

vi.mock('../auth/AuthContext', () => ({ useAuth: vi.fn() }))

const arequipa: Reglamento = {
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
}

function mockUser(rol: string) {
  vi.mocked(useAuth).mockReturnValue({
    user: { sub: 'u1', tenant_id: 't1', schema: 's1', rol, property_id: null, exp: 0 },
    login: vi.fn(),
    logout: vi.fn(),
  })
}

describe('ReglamentoPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('carga las reglas del condominio en el formulario', async () => {
    mockUser('admin')
    vi.spyOn(reglamentoApi, 'getReglamento').mockResolvedValue(arequipa)

    render(<ReglamentoPage />)

    expect(await screen.findByLabelText(/día límite de pago/i)).toHaveValue(5)
    expect(screen.getByLabelText(/recargo \(%\)/i)).toHaveValue(5) // la fracción 0.05 se muestra como 5
    expect(screen.getByLabelText(/modalidad del recargo/i)).toHaveValue('mensual_sobre_saldo')
    expect(screen.getByLabelText(/pago en efectivo/i)).toBeChecked()
    expect(screen.getByLabelText(/no pueden reservar áreas comunes/i)).toBeChecked()
    expect(screen.getByLabelText(/monto desde el cual/i)).toHaveValue(10000)
    expect(screen.getByLabelText(/cajones de visitas/i)).toHaveValue(7)
  })

  it('no muestra 7.000000000000001 por el error de coma flotante', async () => {
    mockUser('admin')
    vi.spyOn(reglamentoApi, 'getReglamento').mockResolvedValue({ ...arequipa, recargo_porcentaje: 0.07 })

    render(<ReglamentoPage />)

    expect(await screen.findByLabelText(/recargo \(%\)/i)).toHaveValue(7)
  })

  it('el admin guarda: el porcentaje vuelve a fracción y el umbral vacío se manda como null', async () => {
    mockUser('admin')
    vi.spyOn(reglamentoApi, 'getReglamento').mockResolvedValue(arequipa)
    const updateSpy = vi.spyOn(reglamentoApi, 'updateReglamento').mockResolvedValue(arequipa)
    const user = userEvent.setup()

    render(<ReglamentoPage />)
    const recargo = await screen.findByLabelText(/recargo \(%\)/i)
    await user.clear(recargo)
    await user.type(recargo, '2.5')
    await user.clear(screen.getByLabelText(/monto desde el cual/i))
    await user.click(screen.getByRole('button', { name: /guardar reglamento/i }))

    await waitFor(() => expect(updateSpy).toHaveBeenCalledTimes(1))
    expect(updateSpy).toHaveBeenCalledWith({
      dia_limite_pago: 5,
      recargo_porcentaje: 0.025,
      recargo_modalidad: 'mensual_sobre_saldo',
      acepta_pago_efectivo: true,
      morosos_sin_voto: true,
      morosos_sin_areas_comunes: true,
      gasto_umbral_asamblea: null,
      cotizaciones_minimas: 3,
      cajones_visitas: 7,
      horas_max_estacionamiento_visitas: 24,
    })
    expect(await screen.findByText(/reglamento guardado/i)).toBeInTheDocument()
  })

  it('cambiar las casillas y la modalidad se manda al guardar', async () => {
    mockUser('admin')
    vi.spyOn(reglamentoApi, 'getReglamento').mockResolvedValue(arequipa)
    const updateSpy = vi.spyOn(reglamentoApi, 'updateReglamento').mockResolvedValue(arequipa)
    const user = userEvent.setup()

    render(<ReglamentoPage />)
    await user.selectOptions(await screen.findByLabelText(/modalidad del recargo/i), 'unico')
    await user.click(screen.getByLabelText(/pago en efectivo/i))
    await user.click(screen.getByLabelText(/conservan voz pero no voto/i))
    await user.click(screen.getByRole('button', { name: /guardar reglamento/i }))

    await waitFor(() => expect(updateSpy).toHaveBeenCalled())
    expect(updateSpy.mock.calls[0][0]).toMatchObject({
      recargo_modalidad: 'unico',
      acepta_pago_efectivo: false,
      morosos_sin_voto: false,
    })
  })

  it('muestra el error del backend si no se puede guardar', async () => {
    mockUser('admin')
    vi.spyOn(reglamentoApi, 'getReglamento').mockResolvedValue(arequipa)
    vi.spyOn(reglamentoApi, 'updateReglamento').mockRejectedValue(new ApiError(422, 'El día límite debe estar entre 1 y 27'))
    const user = userEvent.setup()

    render(<ReglamentoPage />)
    await user.click(await screen.findByRole('button', { name: /guardar reglamento/i }))

    expect(await screen.findByText('El día límite debe estar entre 1 y 27')).toBeInTheDocument()
    expect(screen.queryByText(/reglamento guardado/i)).not.toBeInTheDocument()
  })

  it('quien no es admin lo consulta sin poder cambiarlo', async () => {
    mockUser('tesorero')
    vi.spyOn(reglamentoApi, 'getReglamento').mockResolvedValue(arequipa)

    render(<ReglamentoPage />)

    expect(await screen.findByLabelText(/día límite de pago/i)).toBeDisabled()
    expect(screen.queryByRole('button', { name: /guardar reglamento/i })).not.toBeInTheDocument()
    expect(screen.getByText(/solo el administrador puede cambiarlas/i)).toBeInTheDocument()
  })

  it('muestra el error si no carga el reglamento', async () => {
    mockUser('admin')
    vi.spyOn(reglamentoApi, 'getReglamento').mockRejectedValue(new ApiError(500, 'Error de servidor'))

    render(<ReglamentoPage />)

    expect(await screen.findByText('Error de servidor')).toBeInTheDocument()
  })
})
