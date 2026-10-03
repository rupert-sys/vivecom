import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { TenantDetailPage } from './TenantDetailPage'
import * as tenantsApi from '../api/tenants'
import { ApiError } from '../api/client'
import type { TenantDetail, TenantPayment } from '../api/tenants'

const TENANT: TenantDetail = {
  tenant_id: 't1',
  nombre: 'Residencial Las Fuentes',
  activo: true,
  fecha_creacion: '2026-01-01T00:00:00Z',
  precio_por_vivienda: 25,
  viviendas: 40,
  en_papelera: false,
  papelera_en: null,
  email_admin: 'administracion@lasfuentes.mx',
  nombre_admin: 'Ruperto Villalobos',
  telefono_admin: '5555555555',
  ocupacion: { total: 40, propietario: 25, inquilino: 10, sin_residente: 5 },
}

const PAGO: TenantPayment = {
  id: 'p1',
  tenant_id: 't1',
  fecha: '2026-09-01',
  monto: 1000,
  tipo_pago: 'transferencia',
  notas: 'Septiembre',
  tiene_recibo: true,
  registrado_en: '2026-09-01T10:00:00Z',
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/t1']}>
      <Routes>
        <Route path="/:tenantId" element={<TenantDetailPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('TenantDetailPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(tenantsApi, 'listarPagos').mockResolvedValue([])
  })

  it('muestra la cuota total del condominio, el admin y la ocupación de las viviendas', async () => {
    vi.spyOn(tenantsApi, 'obtenerTenant').mockResolvedValue(TENANT)

    renderPage()

    await waitFor(() => expect(screen.getByText('Residencial Las Fuentes')).toBeInTheDocument())
    // 40 viviendas × $25 = $1000.00 — la cuota total, no la de una sola vivienda.
    expect(screen.getByText('$1000.00')).toBeInTheDocument()
    expect(screen.getByText('($25.00 por vivienda)')).toBeInTheDocument()
    // Aparece dos veces a propósito: en el resumen y en el formulario de cambiar contraseña.
    expect(screen.getAllByText('administracion@lasfuentes.mx').length).toBe(2)
    expect(screen.getByText('Ruperto Villalobos')).toBeInTheDocument()
    expect(screen.getByText('5555555555')).toBeInTheDocument()
    expect(screen.getByText('25')).toBeInTheDocument() // de propietario
    expect(screen.getByText('10')).toBeInTheDocument() // rentadas
    expect(screen.getByText('5')).toBeInTheDocument() // sin residente
  })

  it('cambia la contraseña del administrador', async () => {
    vi.spyOn(tenantsApi, 'obtenerTenant').mockResolvedValue(TENANT)
    const cambiar = vi.spyOn(tenantsApi, 'cambiarPasswordDelAdmin').mockResolvedValue(undefined)

    renderPage()
    await waitFor(() => expect(screen.getByText('Residencial Las Fuentes')).toBeInTheDocument())

    fireEvent.change(screen.getByLabelText('Contraseña nueva'), { target: { value: 'una-clave-nueva' } })
    fireEvent.click(screen.getByText('Cambiar contraseña'))

    await waitFor(() => expect(cambiar).toHaveBeenCalledWith('t1', 'una-clave-nueva'))
    expect(await screen.findByText('Contraseña actualizada.')).toBeInTheDocument()
  })

  it('muestra el error del backend si no se puede cambiar la contraseña', async () => {
    vi.spyOn(tenantsApi, 'obtenerTenant').mockResolvedValue(TENANT)
    vi.spyOn(tenantsApi, 'cambiarPasswordDelAdmin').mockRejectedValue(new ApiError(404, 'Sin cuenta admin'))

    renderPage()
    await waitFor(() => expect(screen.getByText('Residencial Las Fuentes')).toBeInTheDocument())

    fireEvent.change(screen.getByLabelText('Contraseña nueva'), { target: { value: 'una-clave-nueva' } })
    fireEvent.click(screen.getByText('Cambiar contraseña'))

    expect(await screen.findByText('Sin cuenta admin')).toBeInTheDocument()
  })

  it('lista el historial de pagos a Vivecom y registra uno nuevo', async () => {
    vi.spyOn(tenantsApi, 'obtenerTenant').mockResolvedValue(TENANT)
    vi.spyOn(tenantsApi, 'listarPagos').mockResolvedValue([PAGO])
    const registrar = vi.spyOn(tenantsApi, 'registrarPago').mockResolvedValue({
      ...PAGO, id: 'p2', fecha: '2026-10-01', monto: 500, tipo_pago: 'efectivo', notas: null, tiene_recibo: false,
    })

    renderPage()
    await waitFor(() => expect(screen.getByText('Residencial Las Fuentes')).toBeInTheDocument())
    expect(await screen.findByText('Septiembre')).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('Fecha'), { target: { value: '2026-10-01' } })
    fireEvent.change(screen.getByLabelText('Monto'), { target: { value: '500' } })
    fireEvent.change(screen.getByLabelText('Tipo de pago'), { target: { value: 'efectivo' } })
    fireEvent.click(screen.getByText('Registrar pago'))

    await waitFor(() =>
      expect(registrar).toHaveBeenCalledWith('t1', {
        fecha: '2026-10-01', monto: 500, tipo_pago: 'efectivo', notas: undefined, recibo: undefined,
      }),
    )
  })

  it('abre el recibo de un pago en una pestaña nueva', async () => {
    vi.spyOn(tenantsApi, 'obtenerTenant').mockResolvedValue(TENANT)
    vi.spyOn(tenantsApi, 'listarPagos').mockResolvedValue([PAGO])
    const blob = new Blob(['x'], { type: 'image/png' })
    vi.spyOn(tenantsApi, 'descargarRecibo').mockResolvedValue(blob)
    vi.stubGlobal('URL', { createObjectURL: vi.fn(() => 'blob:recibo'), revokeObjectURL: vi.fn() })
    const abrir = vi.spyOn(window, 'open').mockImplementation(() => null)

    renderPage()
    await waitFor(() => expect(screen.getByText('Residencial Las Fuentes')).toBeInTheDocument())

    fireEvent.click(await screen.findByText('Ver recibo'))

    await waitFor(() => expect(tenantsApi.descargarRecibo).toHaveBeenCalledWith('t1', 'p1'))
    expect(abrir).toHaveBeenCalledWith('blob:recibo', '_blank')
  })

  it('un condominio sin cuenta admin no ofrece cambiar contraseña', async () => {
    vi.spyOn(tenantsApi, 'obtenerTenant').mockResolvedValue({ ...TENANT, email_admin: null, nombre_admin: null, telefono_admin: null })

    renderPage()
    await waitFor(() => expect(screen.getByText('Residencial Las Fuentes')).toBeInTheDocument())

    expect(screen.queryByText('Cambiar la contraseña del administrador')).not.toBeInTheDocument()
    expect(screen.getByText('sin cuenta admin todavía')).toBeInTheDocument()
  })
})
