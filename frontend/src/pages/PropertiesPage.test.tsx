import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { PropertiesPage } from './PropertiesPage'
import * as propertiesApi from '../api/properties'
import * as residentImportApi from '../api/residentImport'
import { ApiError } from '../api/client'
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


describe('PropertiesPage: importar Excel de condóminos', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    mockUser('admin')
    vi.spyOn(propertiesApi, 'listProperties').mockResolvedValue([property])
  })

  function renderPage() {
    return render(
      <MemoryRouter>
        <PropertiesPage />
      </MemoryRouter>,
    )
  }

  async function abrirSeccion(user: ReturnType<typeof userEvent.setup>) {
    await screen.findByText('Casa 1')
    await user.click(screen.getByText('Importar Excel de condóminos'))
  }

  it('un rol que no es admin no ve la sección de importar', async () => {
    mockUser('tesorero')
    renderPage()
    await screen.findByText('Casa 1')
    expect(screen.queryByText('Importar Excel de condóminos')).not.toBeInTheDocument()
  })

  it('descarga la plantilla', async () => {
    const descargar = vi.spyOn(residentImportApi, 'downloadImportTemplate').mockResolvedValue()
    const user = userEvent.setup({ delay: null })
    renderPage()
    await abrirSeccion(user)

    await user.click(screen.getByRole('button', { name: /descargar plantilla/i }))

    expect(descargar).toHaveBeenCalled()
  })

  it('sin archivo elegido, Importar está deshabilitado', async () => {
    const user = userEvent.setup({ delay: null })
    renderPage()
    await abrirSeccion(user)

    expect(screen.getByRole('button', { name: /^importar$/i })).toBeDisabled()
  })

  it('importa el archivo elegido y muestra el resumen', async () => {
    const importar = vi.spyOn(residentImportApi, 'importResidents').mockResolvedValue({
      total_filas: 5,
      viviendas_creadas: 2,
      residentes_creados: 5,
      residentes_actualizados: 0,
      vinculos_creados: 5,
      vinculos_actualizados: 0,
      filas_con_error: [],
    })
    const user = userEvent.setup({ delay: null })
    renderPage()
    await abrirSeccion(user)

    const archivo = new File(['contenido'], 'condominos.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    })
    const input = screen.getByLabelText(/archivo de excel/i)
    await user.upload(input, archivo)
    await user.click(screen.getByRole('button', { name: /^importar$/i }))

    await waitFor(() => expect(importar).toHaveBeenCalledWith(archivo))
    expect(await screen.findByText(/5 filas de condóminos/)).toBeInTheDocument()
    expect(screen.getByText(/2 viviendas nuevas/)).toBeInTheDocument()
    expect(screen.getByText(/5 residentes nuevo/)).toBeInTheDocument()
    expect(screen.queryByText(/no se pudo importar/i)).not.toBeInTheDocument()
  })

  it('muestra las filas con error para que se corrijan', async () => {
    vi.spyOn(residentImportApi, 'importResidents').mockResolvedValue({
      total_filas: 3,
      viviendas_creadas: 1,
      residentes_creados: 1,
      residentes_actualizados: 0,
      vinculos_creados: 1,
      vinculos_actualizados: 0,
      filas_con_error: [
        { fila: 2, motivo: 'Falta el nombre.' },
        { fila: 3, motivo: '"vecino" no es "propietario" ni "inquilino".' },
      ],
    })
    const user = userEvent.setup({ delay: null })
    renderPage()
    await abrirSeccion(user)

    await user.upload(screen.getByLabelText(/archivo de excel/i), new File(['x'], 'c.xlsx'))
    await user.click(screen.getByRole('button', { name: /^importar$/i }))

    expect(await screen.findByText(/2 filas no se pudo importar/i)).toBeInTheDocument()
    expect(screen.getByText(/Fila 2: Falta el nombre\./)).toBeInTheDocument()
    expect(screen.getByText(/Fila 3: "vecino" no es "propietario" ni "inquilino"\./)).toBeInTheDocument()
  })

  it('muestra el motivo del backend si la importación falla', async () => {
    vi.spyOn(residentImportApi, 'importResidents').mockRejectedValue(
      new ApiError(422, 'El Excel no tiene estas columnas: correo, nombre, rol, telefono, vivienda'),
    )
    const user = userEvent.setup({ delay: null })
    renderPage()
    await abrirSeccion(user)

    await user.upload(screen.getByLabelText(/archivo de excel/i), new File(['x'], 'c.xlsx'))
    await user.click(screen.getByRole('button', { name: /^importar$/i }))

    expect(await screen.findByText(/el excel no tiene estas columnas/i)).toBeInTheDocument()
  })

  it('tras importar, la lista de viviendas se refresca', async () => {
    const nuevaCasa: Property = { id: 'prop-2', identificador: 'Casa 2', referencia_pago: '7654321', saldo_a_favor: 0 }
    const listar = vi.spyOn(propertiesApi, 'listProperties').mockResolvedValueOnce([property]).mockResolvedValueOnce([property, nuevaCasa])
    vi.spyOn(residentImportApi, 'importResidents').mockResolvedValue({
      total_filas: 1, viviendas_creadas: 1, residentes_creados: 1, residentes_actualizados: 0,
      vinculos_creados: 1, vinculos_actualizados: 0, filas_con_error: [],
    })
    const user = userEvent.setup({ delay: null })
    renderPage()
    await abrirSeccion(user)

    await user.upload(screen.getByLabelText(/archivo de excel/i), new File(['x'], 'c.xlsx'))
    await user.click(screen.getByRole('button', { name: /^importar$/i }))

    await waitFor(() => expect(listar).toHaveBeenCalledTimes(2))
    expect(await screen.findByText('Casa 2')).toBeInTheDocument()
  })
})
