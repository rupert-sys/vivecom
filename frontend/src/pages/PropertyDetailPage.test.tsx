import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { PropertyDetailPage } from './PropertyDetailPage'
import * as propertiesApi from '../api/properties'
import * as residentsApi from '../api/residents'
import { useAuth } from '../auth/AuthContext'
import type { Resident } from '../types'

vi.mock('../auth/AuthContext', () => ({ useAuth: vi.fn() }))

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
})
