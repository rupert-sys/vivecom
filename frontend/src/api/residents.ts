import { apiFetch } from './client'
import type { Resident } from '../types'

export interface ResidentInput {
  nombre: string
  telefono: string
  email?: string
}

export function listResidents(): Promise<Resident[]> {
  return apiFetch<Resident[]>('/residents')
}

export function createResident(payload: ResidentInput): Promise<Resident> {
  return apiFetch<Resident>('/residents', { method: 'POST', body: payload })
}

export function updateResident(id: string, payload: Partial<ResidentInput>): Promise<Resident> {
  return apiFetch<Resident>(`/residents/${id}`, { method: 'PATCH', body: payload })
}
