import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { CollectionStatusPage } from './CollectionStatusPage'
import * as reportsApi from '../api/reports'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import type { CollectionStatus } from '../types'

vi.mock('../auth/AuthContext', () => ({ useAuth: vi.fn() }))

const estado: CollectionStatus = {
  periodo: '2026-09-01',
  total_viviendas: 3,
  al_corriente: 1,
  pendientes: 1,
  morosas: 1,
  adeudo_total: 1500,
  viviendas: [
    { property_id: 'p1', identificador: 'Casa 1', estatus: 'moroso', adeudo_total: 1500, cargos_vencidos: 2, periodo_pagado: false },
    { property_id: 'p2', identificador: 'Casa 2', estatus: 'pendiente', adeudo_total: 750, cargos_vencidos: 0, periodo_pagado: false },
    { property_id: 'p3', identificador: 'Casa 3', estatus: 'al_corriente', adeudo_total: 0, cargos_vencidos: 0, periodo_pagado: true },
  ],
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
      <CollectionStatusPage />
    </MemoryRouter>,
  )
}

describe('CollectionStatusPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('resume cuántas viviendas están al corriente, pendientes y morosas', async () => {
    mockUser('tesorero')
    vi.spyOn(reportsApi, 'getCollectionStatus').mockResolvedValue(estado)

    renderPage()

    await screen.findByText('Casa 1')
    expect(screen.getAllByText('$1500.00')).toHaveLength(2) // la tarjeta de adeudo total y la fila del moroso
    const filas = screen.getAllByRole('row')
    expect(filas).toHaveLength(4) // encabezado + 3 viviendas
    expect(within(filas[1]).getByText('Casa 1')).toBeInTheDocument() // el moroso primero, como lo ordena el backend
    expect(within(filas[1]).getByText('Moroso')).toBeInTheDocument()
    expect(within(filas[3]).getByText('Al corriente')).toBeInTheDocument()
  })

  it('cada vivienda enlaza a su detalle', async () => {
    mockUser('admin')
    vi.spyOn(reportsApi, 'getCollectionStatus').mockResolvedValue(estado)

    renderPage()

    expect(await screen.findByRole('link', { name: 'Casa 1' })).toHaveAttribute('href', '/properties/p1')
  })

  it('el filtro deja solo a los morosos', async () => {
    mockUser('tesorero')
    vi.spyOn(reportsApi, 'getCollectionStatus').mockResolvedValue(estado)
    const user = userEvent.setup()

    renderPage()
    await screen.findByText('Casa 3')
    await user.click(screen.getByRole('button', { name: 'Moroso' }))

    expect(screen.getByText('Casa 1')).toBeInTheDocument()
    expect(screen.queryByText('Casa 2')).not.toBeInTheDocument()
    expect(screen.queryByText('Casa 3')).not.toBeInTheDocument()
  })

  it('un filtro sin resultados lo dice', async () => {
    mockUser('tesorero')
    vi.spyOn(reportsApi, 'getCollectionStatus').mockResolvedValue({ ...estado, viviendas: [estado.viviendas[0]] })
    const user = userEvent.setup()

    renderPage()
    await screen.findByText('Casa 1')
    await user.click(screen.getByRole('button', { name: 'Al corriente' }))

    expect(screen.getByText(/no hay viviendas con este estatus/i)).toBeInTheDocument()
  })

  it('cambiar el mes pide el estatus de ese periodo', async () => {
    mockUser('tesorero')
    const spy = vi.spyOn(reportsApi, 'getCollectionStatus').mockResolvedValue(estado)
    const user = userEvent.setup()

    renderPage()
    await screen.findByText('Casa 1')
    await user.type(screen.getByLabelText('Periodo'), '2026-08')

    await waitFor(() => expect(spy).toHaveBeenLastCalledWith('2026-08-01'))
  })

  it('solo las viviendas al corriente ofrecen la constancia de no adeudo', async () => {
    mockUser('tesorero')
    vi.spyOn(reportsApi, 'getCollectionStatus').mockResolvedValue(estado)
    const descarga = vi.spyOn(reportsApi, 'downloadNoDebtCertificate').mockResolvedValue()
    const user = userEvent.setup()

    renderPage()
    await screen.findByText('Casa 3')
    const botones = screen.getAllByRole('button', { name: /constancia de no adeudo/i })
    expect(botones).toHaveLength(1)
    await user.click(botones[0])

    expect(descarga).toHaveBeenCalledWith('p3', 'Casa 3')
  })

  it('muestra el error si la constancia no se puede generar', async () => {
    mockUser('tesorero')
    vi.spyOn(reportsApi, 'getCollectionStatus').mockResolvedValue(estado)
    vi.spyOn(reportsApi, 'downloadNoDebtCertificate').mockRejectedValue(
      new ApiError(409, 'La vivienda tiene adeudos: no se puede emitir la constancia'),
    )
    const user = userEvent.setup()

    renderPage()
    await user.click(await screen.findByRole('button', { name: /constancia de no adeudo/i }))

    expect(await screen.findByText(/la vivienda tiene adeudos/i)).toBeInTheDocument()
  })

  it('un rol sin acceso no ve la cobranza ni la pide', async () => {
    mockUser('residente')
    const spy = vi.spyOn(reportsApi, 'getCollectionStatus').mockResolvedValue(estado)

    renderPage()

    expect(screen.getByText(/no tienes acceso a esta vista/i)).toBeInTheDocument()
    expect(spy).not.toHaveBeenCalled()
  })

  it('muestra el error del backend si no carga', async () => {
    mockUser('admin')
    vi.spyOn(reportsApi, 'getCollectionStatus').mockRejectedValue(new ApiError(500, 'Error de servidor'))

    renderPage()

    expect(await screen.findByText('Error de servidor')).toBeInTheDocument()
  })
})
