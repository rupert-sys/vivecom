import { render, screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { PackagesPage } from './PackagesPage'
import * as packagesApi from '../api/packages'
import * as propertiesApi from '../api/properties'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import type { Package, Property } from '../types'

vi.mock('../auth/AuthContext', () => ({ useAuth: vi.fn() }))

const casa1: Property = { id: 'p1', identificador: 'Casa 1', referencia_pago: '0000001', saldo_a_favor: 0, residente_principal: null, residente_principal_rol: null, total_residentes: 0 }
const casa2: Property = { id: 'p2', identificador: 'Casa 2', referencia_pago: '0000002', saldo_a_favor: 0, residente_principal: null, residente_principal_rol: null, total_residentes: 0 }

// "Ahora" fijo para que días_esperando() sea determinista en las pruebas.
const AHORA = new Date('2026-10-10T12:00:00Z')

function paquete(extra: Partial<Package> = {}): Package {
  return { id: 'pk1', property_id: 'p1', fecha_llegada: '2026-10-10T08:00:00', fecha_recogido: null, ...extra }
}

function mockUser(rol: string) {
  vi.mocked(useAuth).mockReturnValue({
    user: { sub: 'u1', tenant_id: 't1', schema: 's1', rol, property_id: null, exp: 0 },
    login: vi.fn(),
    logout: vi.fn(),
  })
}

function mockApis(paquetes: Package[], viviendas: Property[] = [casa1, casa2]) {
  vi.spyOn(packagesApi, 'listPackages').mockResolvedValue(paquetes)
  vi.spyOn(propertiesApi, 'listProperties').mockResolvedValue(viviendas)
}

describe('PackagesPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    // Solo Date.now(): con vi.useFakeTimers() a secas, Testing Library deja de poder esperar
    // (findBy/waitFor dependen de timers reales para su propio polling).
    vi.spyOn(Date, 'now').mockReturnValue(AHORA.getTime())
  })

  it('muestra los conteos de pendientes, con 3+ días y recogidos', async () => {
    mockUser('admin')
    mockApis([
      paquete({ id: 'pk1', property_id: 'p1', fecha_llegada: '2026-10-10T08:00:00' }), // hoy, 0 días
      paquete({ id: 'pk2', property_id: 'p2', fecha_llegada: '2026-10-05T08:00:00' }), // 5 días
      paquete({ id: 'pk3', property_id: 'p1', fecha_recogido: '2026-10-09T08:00:00' }),
    ])

    render(<PackagesPage />)

    expect(await screen.findByText('Pendientes de recoger')).toBeInTheDocument()
    expect(screen.getByText('Pendientes de recoger').parentElement).toHaveTextContent('2')
    expect(screen.getByText('Con 3+ días esperando').parentElement).toHaveTextContent('1')
    expect(screen.getByText('Recogidos').parentElement).toHaveTextContent('1')
  })

  it('lista solo los pendientes, con su vivienda y días esperando, del más viejo al más nuevo', async () => {
    mockUser('admin')
    mockApis([
      paquete({ id: 'pk1', property_id: 'p1', fecha_llegada: '2026-10-08T08:00:00' }), // 2 días
      paquete({ id: 'pk2', property_id: 'p2', fecha_llegada: '2026-10-05T08:00:00' }), // 5 días
      paquete({ id: 'pk3', property_id: 'p1', fecha_recogido: '2026-10-09T08:00:00' }), // recogido, no aparece
    ])

    render(<PackagesPage />)

    const filas = await screen.findAllByRole('row')
    expect(filas).toHaveLength(3) // encabezado + 2 pendientes
    // El más viejo (Casa 2, 5 días) va primero.
    expect(within(filas[1]).getByText('Casa 2')).toBeInTheDocument()
    expect(within(filas[1]).getByText('5')).toBeInTheDocument()
    expect(within(filas[2]).getByText('Casa 1')).toBeInTheDocument()
    expect(within(filas[2]).getByText('2')).toBeInTheDocument()
  })

  it('sin paquetes pendientes lo dice', async () => {
    mockUser('admin')
    mockApis([paquete({ fecha_recogido: '2026-10-09T08:00:00' })])

    render(<PackagesPage />)

    expect(await screen.findByText(/no hay paquetes pendientes de recoger/i)).toBeInTheDocument()
  })

  it('un rol sin acceso no ve la paquetería ni la pide', async () => {
    mockUser('tesorero')
    mockApis([paquete()])

    render(<PackagesPage />)

    expect(screen.getByText(/no tienes acceso a esta vista/i)).toBeInTheDocument()
    expect(packagesApi.listPackages).not.toHaveBeenCalled()
  })

  it('muestra el error del backend si falla la carga', async () => {
    mockUser('admin')
    vi.spyOn(packagesApi, 'listPackages').mockRejectedValue(new ApiError(500, 'Error del servidor'))
    vi.spyOn(propertiesApi, 'listProperties').mockResolvedValue([])

    render(<PackagesPage />)

    expect(await screen.findByText('Error del servidor')).toBeInTheDocument()
  })
})
