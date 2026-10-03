import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { TenantTrashPage } from './TenantTrashPage'
import * as tenantsApi from '../api/tenants'
import { ApiError } from '../api/client'

const TENANT_EN_PAPELERA: tenantsApi.TenantListItem = {
  tenant_id: 't1', nombre: 'Residencial Las Fuentes', activo: false, fecha_creacion: '2026-01-01T00:00:00Z',
  precio_por_vivienda: 25, viviendas: 40, en_papelera: true, papelera_en: '2026-09-29T00:00:00Z',
}

describe('TenantTrashPage', () => {
  it('lista los condominios en la papelera', async () => {
    vi.spyOn(tenantsApi, 'listarPapelera').mockResolvedValue([TENANT_EN_PAPELERA])

    render(
      <MemoryRouter>
        <TenantTrashPage />
      </MemoryRouter>,
    )

    await waitFor(() => expect(screen.getByText('Residencial Las Fuentes')).toBeInTheDocument())
    expect(screen.getByText('1 condominio(s) en la papelera')).toBeInTheDocument()
  })

  it('la papelera vacía muestra un mensaje claro', async () => {
    vi.spyOn(tenantsApi, 'listarPapelera').mockResolvedValue([])

    render(
      <MemoryRouter>
        <TenantTrashPage />
      </MemoryRouter>,
    )

    await waitFor(() => expect(screen.getByText('La papelera está vacía.')).toBeInTheDocument())
  })

  it('restaurar llama a la API y recarga la lista', async () => {
    vi.spyOn(tenantsApi, 'listarPapelera')
      .mockResolvedValueOnce([TENANT_EN_PAPELERA])
      .mockResolvedValueOnce([])
    const restaurar = vi.spyOn(tenantsApi, 'restaurarDePapelera').mockResolvedValue({
      ...TENANT_EN_PAPELERA, en_papelera: false, papelera_en: null, activo: true,
      email_admin: null, nombre_admin: null, telefono_admin: null,
      ocupacion: { total: 40, propietario: 0, inquilino: 0, sin_residente: 40 },
    })

    render(
      <MemoryRouter>
        <TenantTrashPage />
      </MemoryRouter>,
    )

    await waitFor(() => expect(screen.getByText('Residencial Las Fuentes')).toBeInTheDocument())
    fireEvent.click(screen.getByText('Restaurar'))

    await waitFor(() => expect(restaurar).toHaveBeenCalledWith('t1'))
    await waitFor(() => expect(screen.getByText('La papelera está vacía.')).toBeInTheDocument())
  })

  it('borrar permanentemente pide la contraseña antes de llamar a la API', async () => {
    vi.spyOn(tenantsApi, 'listarPapelera').mockResolvedValue([TENANT_EN_PAPELERA])
    const borrar = vi.spyOn(tenantsApi, 'borrarPermanentemente').mockResolvedValue(undefined)

    render(
      <MemoryRouter>
        <TenantTrashPage />
      </MemoryRouter>,
    )

    await waitFor(() => expect(screen.getByText('Residencial Las Fuentes')).toBeInTheDocument())
    fireEvent.click(screen.getByText('Eliminar permanentemente'))

    // Sin contraseña, el botón de confirmar debe estar deshabilitado — no debe poder llamar a la API sin ella.
    const confirmar = screen.getByText('Confirmar borrado definitivo')
    expect(confirmar).toBeDisabled()
    expect(borrar).not.toHaveBeenCalled()

    const campoPassword = screen.getByLabelText('Tu contraseña (confirma que eres tú)')
    fireEvent.change(campoPassword, { target: { value: 'mi-clave' } })
    fireEvent.click(screen.getByText('Confirmar borrado definitivo'))

    await waitFor(() => expect(borrar).toHaveBeenCalledWith('t1', 'mi-clave'))
  })

  it('una contraseña incorrecta muestra el error sin cerrar el diálogo', async () => {
    vi.spyOn(tenantsApi, 'listarPapelera').mockResolvedValue([TENANT_EN_PAPELERA])
    vi.spyOn(tenantsApi, 'borrarPermanentemente').mockRejectedValue(new ApiError(403, 'Contraseña incorrecta'))

    render(
      <MemoryRouter>
        <TenantTrashPage />
      </MemoryRouter>,
    )

    await waitFor(() => expect(screen.getByText('Residencial Las Fuentes')).toBeInTheDocument())
    fireEvent.click(screen.getByText('Eliminar permanentemente'))
    fireEvent.change(screen.getByLabelText('Tu contraseña (confirma que eres tú)'), { target: { value: 'mala' } })
    fireEvent.click(screen.getByText('Confirmar borrado definitivo'))

    await waitFor(() => expect(screen.getByText('Contraseña incorrecta')).toBeInTheDocument())
    // El diálogo sigue abierto — sí se puede reintentar sin recargar la página.
    expect(screen.getByLabelText('Tu contraseña (confirma que eres tú)')).toBeInTheDocument()
  })
})
