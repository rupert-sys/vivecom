import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { SignupPage } from './SignupPage'
import { AuthProvider } from '../auth/AuthContext'
import * as signupApi from '../api/signup'
import * as authApi from '../api/auth'
import { ApiError } from '../api/client'

function renderSignup() {
  return render(
    <MemoryRouter>
      <AuthProvider>
        <SignupPage />
      </AuthProvider>
    </MemoryRouter>,
  )
}

describe('SignupPage', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
  })

  it('registra el condominio y hace login automático', async () => {
    const signupSpy = vi.spyOn(signupApi, 'signup').mockResolvedValue({
      tenant_id: 't1',
      nombre: 'Residencial Las Fuentes',
      admin_email: 'admin@condo.mx',
    })
    const loginSpy = vi.spyOn(authApi, 'login').mockResolvedValue('un-token')
    const user = userEvent.setup()

    renderSignup()

    await user.type(screen.getByLabelText(/nombre del condominio/i), 'Residencial Las Fuentes')
    await user.type(screen.getByLabelText(/clabe de destino/i), '012180001547896321')
    await user.type(screen.getByLabelText(/tu email/i), 'admin@condo.mx')
    await user.type(screen.getByLabelText(/contraseña/i), 'clave-temporal-123')
    await user.click(screen.getByRole('button', { name: /crear condominio/i }))

    await waitFor(() =>
      expect(signupSpy).toHaveBeenCalledWith({
        nombre_condominio: 'Residencial Las Fuentes',
        clabe_destino: '012180001547896321',
        admin_email: 'admin@condo.mx',
        admin_password: 'clave-temporal-123',
      }),
    )
    await waitFor(() => expect(loginSpy).toHaveBeenCalledWith('admin@condo.mx', 'clave-temporal-123'))
  })

  it('muestra el mensaje de error exacto si el email ya existe', async () => {
    vi.spyOn(signupApi, 'signup').mockRejectedValue(new ApiError(409, 'Ya existe una cuenta con ese email'))
    const user = userEvent.setup()

    renderSignup()

    await user.type(screen.getByLabelText(/nombre del condominio/i), 'Residencial Las Fuentes')
    await user.type(screen.getByLabelText(/clabe de destino/i), '012180001547896321')
    await user.type(screen.getByLabelText(/tu email/i), 'admin@condo.mx')
    await user.type(screen.getByLabelText(/contraseña/i), 'clave-temporal-123')
    await user.click(screen.getByRole('button', { name: /crear condominio/i }))

    expect(await screen.findByText('Ya existe una cuenta con ese email')).toBeInTheDocument()
  })

  it('tiene un enlace para ir a iniciar sesión', () => {
    renderSignup()
    expect(screen.getByRole('link', { name: /inicia sesión/i })).toHaveAttribute('href', '/login')
  })
})
