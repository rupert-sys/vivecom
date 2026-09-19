import { apiFetch } from './client'
import type { Fee, Periodicidad } from '../types'

export interface FeeInput {
  monto: number
  periodicidad: Periodicidad
  activa_desde: string
}

export function listFees(): Promise<Fee[]> {
  return apiFetch<Fee[]>('/fees')
}

export function createFee(payload: FeeInput): Promise<Fee> {
  return apiFetch<Fee>('/fees', { method: 'POST', body: payload })
}

export function updateFee(id: string, payload: Partial<FeeInput>): Promise<Fee> {
  return apiFetch<Fee>(`/fees/${id}`, { method: 'PATCH', body: payload })
}
