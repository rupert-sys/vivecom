import { apiFetch } from './client'
import type { AccessLogEntry } from '../types'

export function listAccessLogs(): Promise<AccessLogEntry[]> {
  return apiFetch<AccessLogEntry[]>('/access-log')
}
