import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { TenantsListPage } from './TenantsListPage'
import * as tenantsApi from '../api/tenants'

describe('TenantsListPage', () => {
  it('lista los condominios con sus viviendas y estado', async () => {
    vi.spyOn(tenantsApi, 'listarTenants').mockResolvedValue([
      {
        tenant_id: 't1', nombre: 'Residencial Las Fuentes', activo: true, fecha_creacion: '2026-01-01T00:00:00Z',
        precio_por_vivienda: 25, viviendas: 40, en_papelera: false, papelera_en: null,
      },
      {
        tenant_id: 't2', nombre: 'Condominio Arequipa (muestra)', activo: false, fecha_creacion: '2026-02-01T00:00:00Z',
        precio_por_vivienda: 30, viviendas: 12, en_papelera: false, papelera_en: null,
      },
    ])

    render(
      <MemoryRouter>
        <TenantsListPage />
      </MemoryRouter>,
    )

    await waitFor(() => expect(screen.getByText('Residencial Las Fuentes')).toBeInTheDocument())
    expect(screen.getByText('Condominio Arequipa (muestra)')).toBeInTheDocument()
    expect(screen.getByText('Suspendido')).toBeInTheDocument()
    expect(screen.getByText('Activo')).toBeInTheDocument()
    expect(screen.getByText('2 condominio(s) · 52 vivienda(s)')).toBeInTheDocument()
  })

  it('filtra por nombre', async () => {
    vi.spyOn(tenantsApi, 'listarTenants').mockResolvedValue([
      {
        tenant_id: 't1', nombre: 'Residencial Las Fuentes', activo: true, fecha_creacion: '2026-01-01T00:00:00Z',
        precio_por_vivienda: 25, viviendas: 40, en_papelera: false, papelera_en: null,
      },
      {
        tenant_id: 't2', nombre: 'Condominio Arequipa', activo: true, fecha_creacion: '2026-02-01T00:00:00Z',
        precio_por_vivienda: 30, viviendas: 12, en_papelera: false, papelera_en: null,
      },
    ])

    render(
      <MemoryRouter>
        <TenantsListPage />
      </MemoryRouter>,
    )

    await waitFor(() => expect(screen.getByText('Residencial Las Fuentes')).toBeInTheDocument())
    const buscador = screen.getByPlaceholderText('Buscar condominio…')
    fireEvent.change(buscador, { target: { value: 'arequipa' } })

    await waitFor(() => expect(screen.queryByText('Residencial Las Fuentes')).not.toBeInTheDocument())
    expect(screen.getByText('Condominio Arequipa')).toBeInTheDocument()
  })
})
