import { apiFetch } from './client'
import type { Amenity } from '../types'

export function listAmenities(): Promise<Amenity[]> {
  return apiFetch<Amenity[]>('/amenities')
}

export function createAmenity(nombre: string, periodoLimiteHoras: number): Promise<Amenity> {
  return apiFetch<Amenity>('/amenities', {
    method: 'POST',
    body: { nombre, periodo_limite_horas: periodoLimiteHoras },
  })
}

export function listAmenityApprovers(amenityId: string): Promise<string[]> {
  return apiFetch<string[]>(`/amenities/${amenityId}/approvers`)
}

export function addAmenityApprover(amenityId: string, userId: string): Promise<void> {
  return apiFetch<void>(`/amenities/${amenityId}/approvers`, { method: 'POST', body: { user_id: userId } })
}
