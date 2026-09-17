import { apiFetch } from './client'
import type { ClabeChangeLogEntry, TenantClabe } from '../types'

export function getClabe(): Promise<TenantClabe> {
  return apiFetch<TenantClabe>('/tenant/clabe')
}

export function changeClabe(clabeNueva: string): Promise<TenantClabe> {
  return apiFetch<TenantClabe>('/tenant/clabe', {
    method: 'PATCH',
    body: { clabe_nueva: clabeNueva, confirmo_cambio: true },
  })
}

export function getClabeHistory(): Promise<ClabeChangeLogEntry[]> {
  return apiFetch<ClabeChangeLogEntry[]>('/tenant/clabe/historial')
}
