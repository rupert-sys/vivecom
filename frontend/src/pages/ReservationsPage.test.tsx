import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ReservationsPage } from './ReservationsPage'
import * as amenitiesApi from '../api/amenities'
import * as propertiesApi from '../api/properties'
import * as reservationsApi from '../api/reservations'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import type { Amenity, Property, Reservation } from '../types'

vi.mock('../auth/AuthContext', () => ({ useAuth: vi.fn() }))

const area: Amenity = {
  id: 'am1',
  nombre: 'Área adoquinada',
  periodo_limite_horas: 48,
  dias_anticipacion_minimos: 8,
  hora_inicio_permitida: null,
  hora_fin_maxima: '01:00:00',
  dias_semana_permitidos: null,
  capacidad: 1,
  cuota: 1000,
  max_duracion_horas: null,
  notas_reglamento: null,
  reglas: [],
}
const casa: Property = { id: 'p1', identificador: 'Casa 4', referencia_pago: '0000004', saldo_a_favor: 0, residente_principal: null, residente_principal_rol: null, total_residentes: 0 }

function reserva(extra: Partial<Reservation> = {}): Reservation {
  return {
    id: 'r1',
    amenity_id: 'am1',
    property_id: 'p1',
    fecha_inicio: '2026-10-10T20:00:00',
    fecha_fin: '2026-10-11T07:00:00',
    estado: 'aprobada',
    cuota: 1000,
    cuota_pagada: false,
    ...extra,
  }
}

function mockUser(rol: string) {
  vi.mocked(useAuth).mockReturnValue({
    user: { sub: 'u1', tenant_id: 't1', schema: 's1', rol, property_id: null, exp: 0 },
    login: vi.fn(),
    logout: vi.fn(),
  })
}

function mockApis(reservaciones: Reservation[]) {
  vi.spyOn(reservationsApi, 'listReservations').mockResolvedValue(reservaciones)
  vi.spyOn(amenitiesApi, 'listAmenities').mockResolvedValue([area])
  vi.spyOn(propertiesApi, 'listProperties').mockResolvedValue([casa])
}

describe('ReservationsPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('lista las reservaciones con la amenidad, la vivienda y la cuota', async () => {
    mockUser('tesorero')
    mockApis([reserva()])

    render(<ReservationsPage />)

    const fila = (await screen.findByText('Área adoquinada')).closest('tr')!
    expect(within(fila).getByText('Casa 4')).toBeInTheDocument()
    expect(within(fila).getByText('Aprobada')).toBeInTheDocument()
    expect(within(fila).getByText('$1000.00')).toBeInTheDocument()
  })

  it('suma lo que falta por recibir y lo ya recibido, sin contar reservaciones descartadas', async () => {
    mockUser('tesorero')
    mockApis([
      reserva({ id: 'r1', cuota: 1000 }),
      reserva({ id: 'r2', cuota: 500, cuota_pagada: true }),
      reserva({ id: 'r3', cuota: 700, estado: 'rechazada' }), // rechazada: nadie debe entregar esa cuota
    ])

    render(<ReservationsPage />)

    await screen.findAllByText('Área adoquinada')
    const porRecibir = screen.getByText('Cuotas por recibir').parentElement!
    const recibidas = screen.getByText('Cuotas recibidas').parentElement!
    expect(within(porRecibir).getByText('$1000.00')).toBeInTheDocument()
    expect(within(recibidas).getByText('$500.00')).toBeInTheDocument()
  })

  it('el tesorero marca una cuota como recibida y la fila se actualiza', async () => {
    mockUser('tesorero')
    mockApis([reserva()])
    const spy = vi.spyOn(reservationsApi, 'markReservationFeePaid').mockResolvedValue(reserva({ cuota_pagada: true }))
    const user = userEvent.setup()

    render(<ReservationsPage />)
    await user.click(await screen.findByRole('button', { name: /marcar cuota recibida/i }))

    await waitFor(() => expect(spy).toHaveBeenCalledWith('r1'))
    expect(await screen.findByText('Recibida')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /marcar cuota recibida/i })).not.toBeInTheDocument()
  })

  it('el comité aprobador ve la cuota pendiente pero no puede marcarla', async () => {
    mockUser('comite_aprobador')
    mockApis([reserva()])

    render(<ReservationsPage />)

    expect(await screen.findByText('Pendiente', { selector: 'span' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /marcar cuota recibida/i })).not.toBeInTheDocument()
  })

  it('una reservación sin cuota no ofrece nada que recibir', async () => {
    mockUser('admin')
    mockApis([reserva({ cuota: 0 })])

    render(<ReservationsPage />)

    await screen.findByText('Área adoquinada')
    expect(screen.queryByRole('button', { name: /marcar cuota recibida/i })).not.toBeInTheDocument()
  })

  it('el filtro deja solo las que tienen cuota pendiente', async () => {
    mockUser('admin')
    mockApis([
      reserva({ id: 'r1', property_id: 'p1' }),
      reserva({ id: 'r2', cuota_pagada: true }),
      reserva({ id: 'r3', cuota: 0 }),
    ])
    const user = userEvent.setup()

    render(<ReservationsPage />)
    await screen.findAllByText('Área adoquinada')
    expect(screen.getAllByRole('row')).toHaveLength(4)
    await user.click(screen.getByLabelText(/solo con cuota pendiente/i))

    expect(screen.getAllByRole('row')).toHaveLength(2) // encabezado + la única pendiente
  })

  it('sin cuotas pendientes el filtro lo dice', async () => {
    mockUser('admin')
    mockApis([reserva({ cuota_pagada: true })])
    const user = userEvent.setup()

    render(<ReservationsPage />)
    await screen.findByText('Área adoquinada')
    await user.click(screen.getByLabelText(/solo con cuota pendiente/i))

    expect(screen.getByText(/no hay cuotas pendientes de recibir/i)).toBeInTheDocument()
  })

  it('muestra el error del backend si no se puede marcar la cuota', async () => {
    mockUser('tesorero')
    mockApis([reserva()])
    vi.spyOn(reservationsApi, 'markReservationFeePaid').mockRejectedValue(new ApiError(404, 'Reservación no encontrada'))
    const user = userEvent.setup()

    render(<ReservationsPage />)
    await user.click(await screen.findByRole('button', { name: /marcar cuota recibida/i }))

    expect(await screen.findByText('Reservación no encontrada')).toBeInTheDocument()
  })

  it('un rol sin acceso no ve las reservaciones ni las pide', async () => {
    mockUser('guardia')
    mockApis([reserva()])

    render(<ReservationsPage />)

    expect(screen.getByText(/no tienes acceso a esta vista/i)).toBeInTheDocument()
    expect(reservationsApi.listReservations).not.toHaveBeenCalled()
  })

  it('sin reservaciones lo dice', async () => {
    mockUser('admin')
    mockApis([])

    render(<ReservationsPage />)

    expect(await screen.findByText('Todavía no hay reservaciones.')).toBeInTheDocument()
  })
})
