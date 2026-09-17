import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { PropertiesPage } from './PropertiesPage'
import * as propertiesApi from '../api/properties'
import { useAuth } from '../auth/AuthContext'
import type { Property } from '../types'

vi.mock('../auth/AuthContext', () => ({ useAuth: vi.fn() }))

const property: Property = {
  id: 'prop-1',
  identificador: 'Casa 1',
  referencia_pago: '1234567',
  saldo_a_favor: 0,
}

function mockUser(rol: string) {
  vi.mocked(useAuth).mockReturnValue({
    user: { sub: 'u1', tenant_id: 't1', schema: 's1', rol, property_id: null, exp: 0 },
    login: vi.fn(),
    logout: vi.fn(),
  })
}

function renderPage() {
  return render(
    <MemoryRouter>
      <PropertiesPage />
    </MemoryRouter>,
  )
}

describe('PropertiesPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('lista las viviendas que regresa la API', async () => {
    mockUser('tesorero')
    vi.spyOn(propertiesApi, 'listProperties').mockResolvedValue([property])

    renderPage()

    expect(await screen.findByText('Casa 1')).toBeInTheDocument()
    expect(screen.getByText('1234567')).toBeInTheDocument()
  })

  it('no muestra el formulario de alta ni el botón de eliminar si el rol no es admin', async () => {
    mockUser('tesorero')
    vi.spyOn(propertiesApi, 'listProperties').mockResolvedValue([property])

    renderPage()

    await screen.findByText('Casa 1')
    expect(screen.queryByPlaceholderText(/identificador/i)).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /eliminar/i })).not.toBeInTheDocument()
  })

  it('un admin puede crear una vivienda nueva', async () => {
    mockUser('admin')
    vi.spyOn(propertiesApi, 'listProperties').mockResolvedValue([])
    const createSpy = vi.spyOn(propertiesApi, 'createProperty').mockResolvedValue(property)
    const user = userEvent.setup()

    renderPage()
    await screen.findByText(/todavía no hay viviendas/i)

    await user.type(screen.getByPlaceholderText(/identificador/i), 'Casa 1')
    await user.click(screen.getByRole('button', { name: /agregar vivienda/i }))

    await waitFor(() => expect(createSpy).toHaveBeenCalledWith('Casa 1'))
  })

  it('muestra el error del backend si falla la carga', async () => {
    mockUser('admin')
    vi.spyOn(propertiesApi, 'listProperties').mockRejectedValue(new Error('caída'))

    renderPage()

    expect(await screen.findByText(/no se pudieron cargar las viviendas/i)).toBeInTheDocument()
  })
})
