import { apiFetch } from './client'
import type { Poll } from '../types'

export interface PollInput {
  pregunta: string
  opciones: string[]
  fecha_cierre: string
  resultados_en_vivo: boolean
}

export function listPolls(): Promise<Poll[]> {
  return apiFetch<Poll[]>('/polls')
}

export function createPoll(payload: PollInput): Promise<Poll> {
  return apiFetch<Poll>('/polls', { method: 'POST', body: payload })
}
