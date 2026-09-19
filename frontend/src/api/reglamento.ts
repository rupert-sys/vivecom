import { apiFetch } from './client'
import type { Reglamento } from '../types'

export function getReglamento(): Promise<Reglamento> {
  return apiFetch<Reglamento>('/tenant/reglamento')
}

// PATCH parcial: solo se cambia lo que se manda. gasto_umbral_asamblea: null quita el umbral.
export type ReglamentoUpdate = Partial<Omit<Reglamento, 'dia_recargo'>>

export function updateReglamento(payload: ReglamentoUpdate): Promise<Reglamento> {
  return apiFetch<Reglamento>('/tenant/reglamento', { method: 'PATCH', body: payload })
}
