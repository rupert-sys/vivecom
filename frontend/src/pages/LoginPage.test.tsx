import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { LoginPage } from './LoginPage'
import { AuthProvider } from '../auth/AuthContext'
import * as authApi from '../api/auth'
import { ApiError } from '../api/client'

function renderLogin() {
  return render(
    <MemoryRouter>
      <AuthProvider>
        <LoginPage />
      </AuthProvider>
    </MemoryRouter>,
  )
}

describe('LoginPage', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('muestra el mensaje de error exacto que regresa el backend', async () => {
    vi.spyOn(authApi, 'login').mockRejectedValue(new ApiError(401, 'Credenciales inválidas'))
    const user = userEvent.setup()
    renderLogin()

    await user.type(screen.getByLabelText('Email'), 'admin@condo.mx')
    await user.type(screen.getByLabelText('Contraseña'), 'mal-password')
    await user.click(screen.getByRole('button', { name: /entrar/i }))

    expect(await screen.findByText('Credenciales inválidas')).toBeInTheDocument()
  })

  it('muestra un mensaje genérico si el error no viene del API (ej. red caída)', async () => {
    vi.spyOn(authApi, 'login').mockRejectedValue(new Error('network down'))
    const user = userEvent.setup()
    renderLogin()

    await user.type(screen.getByLabelText('Email'), 'admin@condo.mx')
    await user.type(screen.getByLabelText('Contraseña'), 'algo')
    await user.click(screen.getByRole('button', { name: /entrar/i }))

    expect(await screen.findByText(/no se pudo iniciar sesión/i)).toBeInTheDocument()
  })

  it('llama a login con el email y password capturados', async () => {
    const loginSpy = vi.spyOn(authApi, 'login').mockResolvedValue('un-token')
    const user = userEvent.setup()
    renderLogin()

    await user.type(screen.getByLabelText('Email'), 'admin@condo.mx')
    await user.type(screen.getByLabelText('Contraseña'), 'secreta123')
    await user.click(screen.getByRole('button', { name: /entrar/i }))

    await waitFor(() => expect(loginSpy).toHaveBeenCalledWith('admin@condo.mx', 'secreta123'))
  })
})
