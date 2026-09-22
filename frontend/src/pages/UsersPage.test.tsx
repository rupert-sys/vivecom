import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { UsersPage } from './UsersPage'
import * as propertiesApi from '../api/properties'
import * as usersApi from '../api/users'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import type { Property, UserAccount } from '../types'

vi.mock('../auth/AuthContext', () => ({ useAuth: vi.fn() }))

const casa1: Property = { id: 'p1', identificador: 'Casa 1', referencia_pago: '1111111', saldo_a_favor: 0, residente_principal: null, residente_principal_rol: null, total_residentes: 0 }
const casa2: Property = { id: 'p2', identificador: 'Casa 2', referencia_pago: '2222222', saldo_a_favor: 0, residente_principal: null, residente_principal_rol: null, total_residentes: 0 }
const admin: UserAccount = { id: 'u1', email: 'admin@condo.mx', rol: 'admin', property_id: null }
const vecina: UserAccount = { id: 'u2', email: 'vecina@condo.mx', rol: 'residente', property_id: 'p1' }

function mockUser(rol: string) {
  vi.mocked(useAuth).mockReturnValue({
    user: { sub: 'u1', tenant_id: 't1', schema: 's1', rol, property_id: null, exp: 0 },
    login: vi.fn(),
    logout: vi.fn(),
  })
}

function conCuentas(cuentas: UserAccount[] = [admin, vecina]) {
  vi.spyOn(usersApi, 'listUsers').mockResolvedValue(cuentas)
  vi.spyOn(propertiesApi, 'listProperties').mockResolvedValue([casa1, casa2])
}

describe('UsersPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    mockUser('admin')
  })

  it('lista las cuentas con su rol en español y la vivienda del residente', async () => {
    conCuentas()
    render(<UsersPage />)

    const fila = (await screen.findByText('vecina@condo.mx')).closest('tr')!
    expect(within(fila).getByText('Residente')).toBeInTheDocument()
    expect(within(fila).getByText('Casa 1')).toBeInTheDocument()
    expect(within(screen.getByText('admin@condo.mx').closest('tr')!).getByText('Administrador')).toBeInTheDocument()
  })

  it('un rol que no es admin solo ve el aviso y no consulta nada', async () => {
    mockUser('tesorero')
    const listar = vi.spyOn(usersApi, 'listUsers')

    render(<UsersPage />)

    expect(screen.getByText(/solo el administrador/i)).toBeInTheDocument()
    expect(listar).not.toHaveBeenCalled()
  })

  it('crea una cuenta de residente con su vivienda', async () => {
    conCuentas()
    const crear = vi.spyOn(usersApi, 'createUser').mockResolvedValue({ ...vecina, id: 'u3' })
    const user = userEvent.setup({ delay: null })
    render(<UsersPage />)
    await screen.findByText('vecina@condo.mx')

    const form = screen.getByRole('form', { name: 'Nueva cuenta' })
    await user.type(within(form).getByPlaceholderText('Correo'), 'nuevo@condo.mx')
    await user.type(within(form).getByPlaceholderText(/contraseña temporal/i), 'clave-temporal-1')
    await user.selectOptions(within(form).getByLabelText('Vivienda'), 'p2')
    await user.click(within(form).getByRole('button', { name: /agregar cuenta/i }))

    await waitFor(() =>
      expect(crear).toHaveBeenCalledWith({
        email: 'nuevo@condo.mx',
        password: 'clave-temporal-1',
        rol: 'residente',
        property_id: 'p2',
      }),
    )
    expect(await screen.findByText(/cuenta creada/i)).toBeInTheDocument()
  })

  it('el selector de vivienda solo aparece para el rol residente', async () => {
    conCuentas()
    const crear = vi.spyOn(usersApi, 'createUser').mockResolvedValue(admin)
    const user = userEvent.setup({ delay: null })
    render(<UsersPage />)
    await screen.findByText('vecina@condo.mx')
    const form = screen.getByRole('form', { name: 'Nueva cuenta' })

    await user.selectOptions(within(form).getByLabelText('Rol'), 'tesorero')
    expect(within(form).queryByLabelText('Vivienda')).not.toBeInTheDocument()

    await user.type(within(form).getByPlaceholderText('Correo'), 'tes@condo.mx')
    await user.type(within(form).getByPlaceholderText(/contraseña temporal/i), 'clave-temporal-1')
    await user.click(within(form).getByRole('button', { name: /agregar cuenta/i }))

    await waitFor(() =>
      expect(crear).toHaveBeenCalledWith({ email: 'tes@condo.mx', password: 'clave-temporal-1', rol: 'tesorero', property_id: null }),
    )
  })

  it('editar manda solo lo que cambió (la contraseña vacía no se manda)', async () => {
    conCuentas()
    const actualizar = vi.spyOn(usersApi, 'updateUser').mockResolvedValue(vecina)
    const user = userEvent.setup({ delay: null })
    render(<UsersPage />)
    await screen.findByText('vecina@condo.mx')

    await user.click(screen.getByRole('button', { name: 'Editar vecina@condo.mx' }))
    const form = screen.getByRole('form', { name: 'Editar vecina@condo.mx' })
    const correo = within(form).getByLabelText('Correo')
    await user.clear(correo)
    await user.type(correo, 'otra@condo.mx')
    await user.click(within(form).getByRole('button', { name: /guardar/i }))

    await waitFor(() => expect(actualizar).toHaveBeenCalledWith('u2', { email: 'otra@condo.mx' }))
    expect(await screen.findByText(/cuenta actualizada/i)).toBeInTheDocument()
    expect(screen.queryByRole('form', { name: 'Editar vecina@condo.mx' })).not.toBeInTheDocument()
  })

  it('cambiar la contraseña, el rol y la vivienda los manda; quitar la vivienda manda null', async () => {
    conCuentas()
    const actualizar = vi.spyOn(usersApi, 'updateUser').mockResolvedValue(vecina)
    const user = userEvent.setup({ delay: null })
    render(<UsersPage />)
    await screen.findByText('vecina@condo.mx')

    await user.click(screen.getByRole('button', { name: 'Editar vecina@condo.mx' }))
    let form = screen.getByRole('form', { name: 'Editar vecina@condo.mx' })
    await user.type(within(form).getByLabelText('Contraseña nueva'), 'clave-nueva-987')
    await user.selectOptions(within(form).getByLabelText('Vivienda'), 'p2')
    await user.click(within(form).getByRole('button', { name: /guardar/i }))
    await waitFor(() => expect(actualizar).toHaveBeenCalledWith('u2', { password: 'clave-nueva-987', property_id: 'p2' }))
    expect(await screen.findByText(/contraseña nueva rige/i)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Editar vecina@condo.mx' }))
    form = screen.getByRole('form', { name: 'Editar vecina@condo.mx' })
    await user.selectOptions(within(form).getByLabelText('Rol'), 'guardia')
    await user.selectOptions(within(form).getByLabelText('Vivienda'), '')
    await user.click(within(form).getByRole('button', { name: /guardar/i }))
    await waitFor(() => expect(actualizar).toHaveBeenLastCalledWith('u2', { rol: 'guardia', property_id: null }))
  })

  it('guardar sin cambios no llama a la API y cierra el formulario', async () => {
    conCuentas()
    const actualizar = vi.spyOn(usersApi, 'updateUser')
    const user = userEvent.setup({ delay: null })
    render(<UsersPage />)
    await screen.findByText('vecina@condo.mx')

    await user.click(screen.getByRole('button', { name: 'Editar vecina@condo.mx' }))
    await user.click(within(screen.getByRole('form', { name: 'Editar vecina@condo.mx' })).getByRole('button', { name: /guardar/i }))

    expect(actualizar).not.toHaveBeenCalled()
    expect(screen.queryByRole('form', { name: 'Editar vecina@condo.mx' })).not.toBeInTheDocument()
  })

  it('muestra el motivo del backend y deja el formulario abierto (correo repetido, único admin…)', async () => {
    conCuentas()
    vi.spyOn(usersApi, 'updateUser').mockRejectedValue(new ApiError(409, 'Ya existe una cuenta con ese email'))
    const user = userEvent.setup({ delay: null })
    render(<UsersPage />)
    await screen.findByText('vecina@condo.mx')

    await user.click(screen.getByRole('button', { name: 'Editar vecina@condo.mx' }))
    const form = screen.getByRole('form', { name: 'Editar vecina@condo.mx' })
    const correo = within(form).getByLabelText('Correo')
    await user.clear(correo)
    await user.type(correo, 'admin@condo.mx')
    await user.click(within(form).getByRole('button', { name: /guardar/i }))

    expect(await screen.findByText('Ya existe una cuenta con ese email')).toBeInTheDocument()
    expect(screen.getByRole('form', { name: 'Editar vecina@condo.mx' })).toBeInTheDocument()
  })

  it('cancelar cierra la edición sin guardar', async () => {
    conCuentas()
    const actualizar = vi.spyOn(usersApi, 'updateUser')
    const user = userEvent.setup({ delay: null })
    render(<UsersPage />)
    await screen.findByText('vecina@condo.mx')

    await user.click(screen.getByRole('button', { name: 'Editar vecina@condo.mx' }))
    await user.click(screen.getByRole('button', { name: /cancelar/i }))

    expect(screen.queryByRole('form', { name: 'Editar vecina@condo.mx' })).not.toBeInTheDocument()
    expect(actualizar).not.toHaveBeenCalled()
  })

  it('eliminar pide confirmación y solo elimina si se acepta', async () => {
    conCuentas()
    const eliminar = vi.spyOn(usersApi, 'deleteUser').mockResolvedValue()
    const confirmar = vi.spyOn(window, 'confirm').mockReturnValueOnce(false).mockReturnValueOnce(true)
    const user = userEvent.setup({ delay: null })
    render(<UsersPage />)
    await screen.findByText('vecina@condo.mx')

    await user.click(screen.getByRole('button', { name: 'Eliminar vecina@condo.mx' }))
    expect(eliminar).not.toHaveBeenCalled()

    await user.click(screen.getByRole('button', { name: 'Eliminar vecina@condo.mx' }))
    await waitFor(() => expect(eliminar).toHaveBeenCalledWith('u2'))
    expect(confirmar).toHaveBeenCalledTimes(2)
    expect(await screen.findByText(/cuenta eliminada/i)).toBeInTheDocument()
  })

  it('si no cargan las cuentas, muestra el error', async () => {
    vi.spyOn(usersApi, 'listUsers').mockRejectedValue(new ApiError(500, 'Error interno'))
    vi.spyOn(propertiesApi, 'listProperties').mockResolvedValue([])
    render(<UsersPage />)

    expect(await screen.findByText('Error interno')).toBeInTheDocument()
  })
})
