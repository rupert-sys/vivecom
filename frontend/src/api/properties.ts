import { apiFetch } from './client'
import type { Property, Resident, RolOcupacion } from '../types'

export function listProperties(): Promise<Property[]> {
  return apiFetch<Property[]>('/properties')
}

export function createProperty(identificador: string): Promise<Property> {
  return apiFetch<Property>('/properties', { method: 'POST', body: { identificador } })
}

export function updateProperty(id: string, identificador: string): Promise<Property> {
  return apiFetch<Property>(`/properties/${id}`, { method: 'PATCH', body: { identificador } })
}

export function listPropertyResidents(propertyId: string): Promise<Resident[]> {
  return apiFetch<Resident[]>(`/properties/${propertyId}/residents`)
}

export function linkResidentToProperty(
  propertyId: string,
  residentId: string,
  rol: RolOcupacion,
): Promise<void> {
  return apiFetch<void>(`/properties/${propertyId}/residents`, {
    method: 'POST',
    body: { resident_id: residentId, rol },
  })
}

export function unlinkResidentFromProperty(propertyId: string, residentId: string): Promise<void> {
  return apiFetch<void>(`/properties/${propertyId}/residents/${residentId}`, { method: 'DELETE' })
}
