import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { OrganizationPage } from './OrganizationPage'
import * as tenantApi from '../api/tenant'
import { ApiError } from '../api/client'

describe('OrganizationPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    // jsdom no implementa URL.createObjectURL: la previsualización instantánea del logo elegido lo necesita.
    vi.stubGlobal('URL', { createObjectURL: vi.fn(() => 'blob:logo-elegido'), revokeObjectURL: vi.fn() })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  function conConfig(config = { id: 't1', nombre: 'Residencial Las Torres', tiene_logo: false }) {
    vi.spyOn(tenantApi, 'getTenantConfig').mockResolvedValue(config)
    vi.spyOn(tenantApi, 'fetchLogoObjectUrl').mockResolvedValue(config.tiene_logo ? 'blob:logo-actual' : null)
    return config
  }

  it('carga y muestra el nombre actual del condominio', async () => {
    conConfig()
    render(<OrganizationPage />)

    expect(await screen.findByDisplayValue('Residencial Las Torres')).toBeInTheDocument()
  })

  it('Guardar está deshabilitado hasta que el nombre cambie', async () => {
    conConfig()
    const user = userEvent.setup({ delay: null })
    render(<OrganizationPage />)
    const input = await screen.findByDisplayValue('Residencial Las Torres')

    expect(screen.getByRole('button', { name: /guardar/i })).toBeDisabled()

    await user.clear(input)
    await user.type(input, 'Residencial Los Encinos')
    expect(screen.getByRole('button', { name: /guardar/i })).toBeEnabled()
  })

  it('guarda el nombre nuevo', async () => {
    conConfig()
    const actualizar = vi.spyOn(tenantApi, 'updateTenantName').mockResolvedValue({
      id: 't1', nombre: 'Residencial Los Encinos', tiene_logo: false,
    })
    const user = userEvent.setup({ delay: null })
    render(<OrganizationPage />)
    const input = await screen.findByDisplayValue('Residencial Las Torres')

    await user.clear(input)
    await user.type(input, 'Residencial Los Encinos')
    await user.click(screen.getByRole('button', { name: /guardar/i }))

    await waitFor(() => expect(actualizar).toHaveBeenCalledWith('Residencial Los Encinos'))
    expect(await screen.findByText('Nombre actualizado.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /guardar/i })).toBeDisabled()
  })

  it('muestra el motivo del backend si falla guardar el nombre', async () => {
    conConfig()
    vi.spyOn(tenantApi, 'updateTenantName').mockRejectedValue(new ApiError(422, 'El nombre no puede quedar vacío'))
    const user = userEvent.setup({ delay: null })
    render(<OrganizationPage />)
    const input = await screen.findByDisplayValue('Residencial Las Torres')

    await user.clear(input)
    await user.type(input, 'x')
    await user.click(screen.getByRole('button', { name: /guardar/i }))

    expect(await screen.findByText('El nombre no puede quedar vacío')).toBeInTheDocument()
  })

  it('sin logo, muestra "Sin logo" y no ofrece quitarlo', async () => {
    conConfig()
    render(<OrganizationPage />)

    await screen.findByDisplayValue('Residencial Las Torres')
    expect(screen.getByText('Sin logo')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /quitar logo/i })).not.toBeInTheDocument()
  })

  it('con logo, lo muestra y ofrece quitarlo', async () => {
    conConfig({ id: 't1', nombre: 'Residencial Las Torres', tiene_logo: true })
    render(<OrganizationPage />)

    const imagen = await screen.findByAltText('Logo del condominio')
    expect(imagen).toHaveAttribute('src', 'blob:logo-actual')
    expect(screen.getByRole('button', { name: /quitar logo/i })).toBeInTheDocument()
  })

  it('sube un logo nuevo', async () => {
    conConfig()
    const subir = vi.spyOn(tenantApi, 'uploadLogo').mockResolvedValue({ id: 't1', nombre: 'Residencial Las Torres', tiene_logo: true })
    const user = userEvent.setup({ delay: null })
    render(<OrganizationPage />)
    await screen.findByDisplayValue('Residencial Las Torres')

    const archivo = new File(['contenido'], 'logo.png', { type: 'image/png' })
    await user.upload(screen.getByLabelText(/logo del condominio/i), archivo)

    await waitFor(() => expect(subir).toHaveBeenCalledWith(archivo))
    expect(await screen.findByText('Logo actualizado.')).toBeInTheDocument()
    expect(await screen.findByAltText('Logo del condominio')).toBeInTheDocument()
  })

  it('muestra el motivo del backend si falla subir el logo (p. ej. tamaño)', async () => {
    conConfig()
    vi.spyOn(tenantApi, 'uploadLogo').mockRejectedValue(new ApiError(413, 'El logo pesa más de 3 MB.'))
    const user = userEvent.setup({ delay: null })
    render(<OrganizationPage />)
    await screen.findByDisplayValue('Residencial Las Torres')

    await user.upload(screen.getByLabelText(/logo del condominio/i), new File(['x'], 'grande.png', { type: 'image/png' }))

    expect(await screen.findByText('El logo pesa más de 3 MB.')).toBeInTheDocument()
  })

  it('quitar el logo pide confirmación y solo lo quita si se acepta', async () => {
    conConfig({ id: 't1', nombre: 'Residencial Las Torres', tiene_logo: true })
    const quitar = vi.spyOn(tenantApi, 'deleteLogo').mockResolvedValue()
    const confirmar = vi.spyOn(window, 'confirm').mockReturnValueOnce(false).mockReturnValueOnce(true)
    const user = userEvent.setup({ delay: null })
    render(<OrganizationPage />)
    await screen.findByAltText('Logo del condominio')

    await user.click(screen.getByRole('button', { name: /quitar logo/i }))
    expect(quitar).not.toHaveBeenCalled()

    await user.click(screen.getByRole('button', { name: /quitar logo/i }))
    await waitFor(() => expect(quitar).toHaveBeenCalled())
    expect(confirmar).toHaveBeenCalledTimes(2)
    expect(await screen.findByText('Sin logo')).toBeInTheDocument()
  })

  it('si no carga la configuración, muestra el error', async () => {
    vi.spyOn(tenantApi, 'getTenantConfig').mockRejectedValue(new ApiError(500, 'Error interno'))
    render(<OrganizationPage />)

    expect(await screen.findByText('Error interno')).toBeInTheDocument()
  })
})
