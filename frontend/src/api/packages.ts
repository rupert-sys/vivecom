import { apiFetch } from './client'
import type { Package } from '../types'

export function listPackages(): Promise<Package[]> {
  return apiFetch<Package[]>('/packages')
}
