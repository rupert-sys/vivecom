import { apiFetch } from './client'
import type { Reservation } from '../types'

export function listReservations(): Promise<Reservation[]> {
  return apiFetch<Reservation[]>('/reservations')
}

// La cuota de uso se entrega a tesorería al solicitar la reservación (reglamento Art. 2 VI).
export function markReservationFeePaid(reservationId: string): Promise<Reservation> {
  return apiFetch<Reservation>(`/reservations/${reservationId}/cuota-pagada`, { method: 'POST' })
}
