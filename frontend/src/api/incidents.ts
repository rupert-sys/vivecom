import { apiFetch } from './client'
import type { Incident } from '../types'

export function listIncidents(): Promise<Incident[]> {
  return apiFetch<Incident[]>('/incidents')
}
