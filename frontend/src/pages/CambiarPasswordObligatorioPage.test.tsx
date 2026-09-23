import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { CambiarPasswordObligatorioPage } from './CambiarPasswordObligatorioPage'
import { useAuth } from '../auth/AuthContext'
import * as usersApi from '../api/users'
import { ApiError } from '../api/client'

vi.mock('../auth/AuthContext', () => ({ useAuth: vi.fn() }))

function mockUser(logout = vi.fn()) {
  vi.mocked(useAuth).mockReturnValue({
    user: { sub: 'admin-1', tenant_id: 't1', schema: 's1', rol: 'admin', property_id: null, debe_cambiar_password: true, exp: 0 },
    login: vi.fn(),
    logout,
  })
  return logout
}

describe('CambiarPasswordObligatorioPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('las dos contraseñas deben coincidir', async () => {
    mockUser()
    const updateSpy = vi.spyOn(usersApi, 'updateUser')
    const user = userEvent.setup()

    render(
      <MemoryRouter>
        <CambiarPasswordObligatorioPage />
      </MemoryRouter>,
    )

    await user.type(screen.getByLabelText(/contraseña nueva/i), 'clave-nueva-123')
    await user.type(screen.getByLabelText(/confírmala/i), 'otra-clave-distinta')
    await user.click(screen.getByRole('button', { name: /cambiar contraseña/i }))

    expect(await screen.findByText('Las dos contraseñas no coinciden.')).toBeInTheDocument()
    expect(updateSpy).not.toHaveBeenCalled()
  })

  it('cambia la contraseña de la propia cuenta y cierra la sesión para volver a entrar', async () => {
    const logoutSpy = mockUser()
    const updateSpy = vi.spyOn(usersApi, 'updateUser').mockResolvedValue({
      id: 'admin-1', email: 'administracion@arequipa.com.mx', rol: 'admin', property_id: null,
    })
    const user = userEvent.setup()

    render(
      <MemoryRouter>
        <CambiarPasswordObligatorioPage />
      </MemoryRouter>,
    )

    await user.type(screen.getByLabelText(/contraseña nueva/i), 'clave-nueva-123')
    await user.type(screen.getByLabelText(/confírmala/i), 'clave-nueva-123')
    await user.click(screen.getByRole('button', { name: /cambiar contraseña/i }))

    await waitFor(() => expect(updateSpy).toHaveBeenCalledWith('admin-1', { password: 'clave-nueva-123' }))
    await waitFor(() => expect(logoutSpy).toHaveBeenCalled())
  })

  it('muestra el error del backend si falla el cambio', async () => {
    mockUser()
    vi.spyOn(usersApi, 'updateUser').mockRejectedValue(new ApiError(422, 'La contraseña es muy corta'))
    const user = userEvent.setup()

    render(
      <MemoryRouter>
        <CambiarPasswordObligatorioPage />
      </MemoryRouter>,
    )

    await user.type(screen.getByLabelText(/contraseña nueva/i), 'clave-nueva-123')
    await user.type(screen.getByLabelText(/confírmala/i), 'clave-nueva-123')
    await user.click(screen.getByRole('button', { name: /cambiar contraseña/i }))

    expect(await screen.findByText('La contraseña es muy corta')).toBeInTheDocument()
  })
})
