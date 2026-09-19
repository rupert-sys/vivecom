import { apiFetch } from './client'
import type { Amenity } from '../types'

// Reglas de uso de una amenidad según el reglamento del condominio.
export interface AmenityRulesInput {
  dias_anticipacion_minimos: number
  hora_inicio_permitida: string | null
  hora_fin_maxima: string | null
  dias_semana_permitidos: number[] | null
  capacidad: number
  cuota: number
  max_duracion_horas: number | null
  notas_reglamento: string | null
}

export function listAmenities(): Promise<Amenity[]> {
  return apiFetch<Amenity[]>('/amenities')
}

export function createAmenity(
  nombre: string,
  periodoLimiteHoras: number,
  reglas?: Partial<AmenityRulesInput>,
): Promise<Amenity> {
  return apiFetch<Amenity>('/amenities', {
    method: 'POST',
    body: { nombre, periodo_limite_horas: periodoLimiteHoras, ...reglas },
  })
}

export function updateAmenity(
  id: string,
  cambios: Partial<AmenityRulesInput> & { nombre?: string; periodo_limite_horas?: number },
): Promise<Amenity> {
  return apiFetch<Amenity>(`/amenities/${id}`, { method: 'PATCH', body: cambios })
}

export function listAmenityApprovers(amenityId: string): Promise<string[]> {
  return apiFetch<string[]>(`/amenities/${amenityId}/approvers`)
}

export function addAmenityApprover(amenityId: string, userId: string): Promise<void> {
  return apiFetch<void>(`/amenities/${amenityId}/approvers`, { method: 'POST', body: { user_id: userId } })
}
