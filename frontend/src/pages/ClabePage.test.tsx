import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ClabePage } from './ClabePage'
import * as tenantConfigApi from '../api/tenantConfig'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import type { ClabeChangeLogEntry, TenantClabe } from '../types'

vi.mock('../auth/AuthContext', () => ({ useAuth: vi.fn() }))

const clabe: TenantClabe = { id: 't1', nombre: 'Residencial Demo', clabe_destino: '012180001547896321' }
const historial: ClabeChangeLogEntry[] = [
  {
    id: 'log-1',
    clabe_anterior: '012180001547896300',
    clabe_nueva: '012180001547896321',
    cambiado_por: 'u1',
    fecha: '2026-09-01T10:00:00Z',
  },
]

function mockUser(rol: string) {
  vi.mocked(useAuth).mockReturnValue({
    user: { sub: 'u1', tenant_id: 't1', schema: 's1', rol, property_id: null, exp: 0 },
    login: vi.fn(),
    logout: vi.fn(),
  })
}

describe('ClabePage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('muestra la CLABE vigente a cualquier rol autenticado', async () => {
    mockUser('tesorero')
    vi.spyOn(tenantConfigApi, 'getClabe').mockResolvedValue(clabe)

    render(<ClabePage />)

    expect(await screen.findByText('012180001547896321')).toBeInTheDocument()
  })

  it('un no-admin no ve el formulario de cambio ni el historial', async () => {
    mockUser('tesorero')
    const getClabeHistorySpy = vi.spyOn(tenantConfigApi, 'getClabeHistory')
    vi.spyOn(tenantConfigApi, 'getClabe').mockResolvedValue(clabe)

    render(<ClabePage />)

    await screen.findByText('012180001547896321')
    expect(screen.queryByPlaceholderText(/nueva clabe/i)).not.toBeInTheDocument()
    expect(getClabeHistorySpy).not.toHaveBeenCalled()
  })

  it('un admin ve el historial de cambios', async () => {
    mockUser('admin')
    vi.spyOn(tenantConfigApi, 'getClabe').mockResolvedValue(clabe)
    vi.spyOn(tenantConfigApi, 'getClabeHistory').mockResolvedValue(historial)

    render(<ClabePage />)

    expect(await screen.findByText('012180001547896300')).toBeInTheDocument()
  })

  it('el botón de cambiar sigue deshabilitado hasta marcar la casilla de confirmación', async () => {
    mockUser('admin')
    vi.spyOn(tenantConfigApi, 'getClabe').mockResolvedValue(clabe)
    vi.spyOn(tenantConfigApi, 'getClabeHistory').mockResolvedValue([])
    const user = userEvent.setup()

    render(<ClabePage />)
    await screen.findByText('012180001547896321')

    const boton = screen.getByRole('button', { name: /cambiar clabe/i })
    expect(boton).toBeDisabled()

    await user.type(screen.getByPlaceholderText(/nueva clabe/i), '012180009999999999')
    expect(boton).toBeDisabled()

    await user.click(screen.getByRole('checkbox'))
    expect(boton).not.toBeDisabled()
  })

  it('un admin puede cambiar la CLABE tras confirmar, y el formulario se limpia', async () => {
    mockUser('admin')
    vi.spyOn(tenantConfigApi, 'getClabe').mockResolvedValue(clabe)
    vi.spyOn(tenantConfigApi, 'getClabeHistory').mockResolvedValue([])
    const changeSpy = vi.spyOn(tenantConfigApi, 'changeClabe').mockResolvedValue({
      ...clabe,
      clabe_destino: '012180009999999999',
    })
    const user = userEvent.setup()

    render(<ClabePage />)
    await screen.findByText('012180001547896321')

    await user.type(screen.getByPlaceholderText(/nueva clabe/i), '012180009999999999')
    await user.click(screen.getByRole('checkbox'))
    await user.click(screen.getByRole('button', { name: /cambiar clabe/i }))

    await waitFor(() => expect(changeSpy).toHaveBeenCalledWith('012180009999999999'))
    expect(await screen.findByText(/se actualizó correctamente/i)).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/nueva clabe/i)).toHaveValue('')
    expect(screen.getByRole('checkbox')).not.toBeChecked()
  })

  it('muestra el mensaje de error real que regresa el backend al fallar el cambio', async () => {
    // Nota: el input tiene pattern="[0-9]{18}", así que un valor que NO son 18
    // dígitos nunca llega a disparar el submit (bloqueado por el navegador
    // antes de handleSubmit) — para probar el mensaje de error hay que usar un
    // valor que SÍ pase la validación del navegador y simular el rechazo del
    // backend (ej. un 409 o 500), no la validación de formato de la CLABE.
    mockUser('admin')
    vi.spyOn(tenantConfigApi, 'getClabe').mockResolvedValue(clabe)
    vi.spyOn(tenantConfigApi, 'getClabeHistory').mockResolvedValue([])
    vi.spyOn(tenantConfigApi, 'changeClabe').mockRejectedValue(new ApiError(500, 'Ocurrió un error inesperado.'))
    const user = userEvent.setup()

    render(<ClabePage />)
    await screen.findByText('012180001547896321')

    await user.type(screen.getByPlaceholderText(/nueva clabe/i), '012180009999999999')
    await user.click(screen.getByRole('checkbox'))
    await user.click(screen.getByRole('button', { name: /cambiar clabe/i }))

    expect(await screen.findByText('Ocurrió un error inesperado.')).toBeInTheDocument()
  })
})
