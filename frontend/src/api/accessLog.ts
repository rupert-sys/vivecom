import { apiFetch } from './client'
import type { AccessLogEntry, VisitorParking } from '../types'

export function listAccessLogs(): Promise<AccessLogEntry[]> {
  return apiFetch<AccessLogEntry[]>('/access-log')
}

export function getVisitorParking(): Promise<VisitorParking> {
  return apiFetch<VisitorParking>('/access-log/estacionamiento-visitas')
}
