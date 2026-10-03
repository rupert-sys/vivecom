import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { TenantCreatePage } from './TenantCreatePage'
import * as tenantsApi from '../api/tenants'
import type { TenantCreateResponse } from '../api/tenants'

const RESULTADO: TenantCreateResponse = {
  tenant_id: 't1',
  nombre: 'Residencial Las Fuentes',
  email_admin: 'administracion@lasfuentes.mx',
  email_tesorero: 'tesoreria@lasfuentes.mx',
  email_guardia: 'vigilancia@lasfuentes.mx',
  email_vocero: 'vocero@lasfuentes.mx',
  emails_viviendas: ['casa1@lasfuentes.mx', 'casa2@lasfuentes.mx'],
}

function renderPage() {
  return render(
    <MemoryRouter>
      <TenantCreatePage />
    </MemoryRouter>,
  )
}

describe('TenantCreatePage', () => {
  it('al crear el condominio, además del admin muestra las cuentas de tesorería, vigilancia y vocero ya listas para usarse', async () => {
    const crearSpy = vi.spyOn(tenantsApi, 'crearTenant').mockResolvedValue(RESULTADO)
    const user = userEvent.setup()

    renderPage()
    await user.type(screen.getByLabelText(/nombre del condominio/i), 'Residencial Las Fuentes')
    await user.clear(screen.getByLabelText(/cantidad de viviendas/i))
    await user.type(screen.getByLabelText(/cantidad de viviendas/i), '2')
    await user.type(screen.getByLabelText(/nombre de quien administrará/i), 'Ruperto Villalobos')
    await user.type(screen.getByLabelText(/teléfono de contacto/i), '5555555555')
    await user.click(screen.getByRole('button', { name: /crear condominio/i }))

    await waitFor(() =>
      expect(crearSpy).toHaveBeenCalledWith({
        nombre_condominio: 'Residencial Las Fuentes',
        cantidad_casas: 2,
        nombre_admin: 'Ruperto Villalobos',
        telefono_admin: '5555555555',
      }),
    )

    expect(await screen.findByText('administracion@lasfuentes.mx')).toBeInTheDocument()
    expect(screen.getByText('tesoreria@lasfuentes.mx')).toBeInTheDocument()
    expect(screen.getByText('vigilancia@lasfuentes.mx')).toBeInTheDocument()
    expect(screen.getByText('vocero@lasfuentes.mx')).toBeInTheDocument()
  })
})
