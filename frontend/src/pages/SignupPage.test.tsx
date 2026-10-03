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

async function llenarPaso1(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText(/nombre del condominio/i), 'Residencial Las Fuentes')
  await user.type(screen.getByLabelText(/cantidad de viviendas/i), '20')
  await user.click(screen.getByRole('button', { name: /continuar/i }))
}

const respuesta = {
  tenant_id: 't1',
  nombre: 'Residencial Las Fuentes',
  admin_email: 'administracion@lasfuentes.com.mx',
  email_tesorero: 'tesoreria@lasfuentes.com.mx',
  email_guardia: 'vigilancia@lasfuentes.com.mx',
  email_vocero: 'vocero@lasfuentes.com.mx',
  emails_viviendas: ['casa1@lasfuentes.com.mx', 'casa2@lasfuentes.com.mx'],
}

describe('SignupPage', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
  })

  it('paso 1: pide el condominio y cuántas viviendas, y avisa que se crean de una vez', async () => {
    const user = userEvent.setup()
    renderSignup()

    await user.type(screen.getByLabelText(/nombre del condominio/i), 'Residencial Las Fuentes')
    await user.type(screen.getByLabelText(/cantidad de viviendas/i), '20')

    expect(screen.getByText(/"Casa 1" a "Casa 20"/)).toBeInTheDocument()
  })

  it('registra el condominio con nombre+teléfono del admin y hace login automático con la contraseña temporal', async () => {
    const signupSpy = vi.spyOn(signupApi, 'signup').mockResolvedValue(respuesta)
    const loginSpy = vi.spyOn(authApi, 'login').mockResolvedValue('un-token')
    const user = userEvent.setup()

    renderSignup()
    await llenarPaso1(user)

    await user.type(screen.getByLabelText(/tu nombre/i), 'Ruperto Villalobos')
    await user.type(screen.getByLabelText(/tu teléfono/i), '5555555555')
    await user.click(screen.getByRole('button', { name: /crear condominio/i }))

    await waitFor(() =>
      expect(signupSpy).toHaveBeenCalledWith({
        nombre_condominio: 'Residencial Las Fuentes',
        cantidad_casas: 20,
        nombre_admin: 'Ruperto Villalobos',
        telefono_admin: '5555555555',
      }),
    )
    expect(await screen.findByText('administracion@lasfuentes.com.mx')).toBeInTheDocument()
    expect(screen.getByText('tesoreria@lasfuentes.com.mx')).toBeInTheDocument()
    expect(screen.getByText('vigilancia@lasfuentes.com.mx')).toBeInTheDocument()
    expect(screen.getByText('vocero@lasfuentes.com.mx')).toBeInTheDocument()
    expect(screen.getByText('casa1@lasfuentes.com.mx')).toBeInTheDocument()
    expect(screen.getByText('casa2@lasfuentes.com.mx')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /entrar al panel/i }))

    // La contraseña con la que se hace login automático es el nombre del condominio (temporal, ver alcance).
    await waitFor(() =>
      expect(loginSpy).toHaveBeenCalledWith('administracion@lasfuentes.com.mx', 'Residencial Las Fuentes'),
    )
  })

  it('el botón "Atrás" del paso 2 regresa al paso 1 sin perder lo escrito', async () => {
    const user = userEvent.setup()
    renderSignup()
    await llenarPaso1(user)

    await user.click(screen.getByRole('button', { name: /atrás/i }))

    expect(screen.getByLabelText(/nombre del condominio/i)).toHaveValue('Residencial Las Fuentes')
  })

  it('muestra el mensaje de error exacto si algo falla al crear el condominio', async () => {
    vi.spyOn(signupApi, 'signup').mockRejectedValue(new ApiError(409, 'Ya existe un condominio con ese nombre'))
    const user = userEvent.setup()

    renderSignup()
    await llenarPaso1(user)
    await user.type(screen.getByLabelText(/tu nombre/i), 'Ruperto Villalobos')
    await user.type(screen.getByLabelText(/tu teléfono/i), '5555555555')
    await user.click(screen.getByRole('button', { name: /crear condominio/i }))

    expect(await screen.findByText('Ya existe un condominio con ese nombre')).toBeInTheDocument()
  })

  it('tiene un enlace para ir a iniciar sesión desde el paso 1', () => {
    renderSignup()
    expect(screen.getByRole('link', { name: /inicia sesión/i })).toHaveAttribute('href', '/login')
  })
})
