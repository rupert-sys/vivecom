import { apiFetch } from './client'
import type { CollectionsSummary } from '../types'

export interface CollectionsSummaryFilters {
  periodo?: string
  propertyId?: string
}

export function getCollectionsSummary(filters: CollectionsSummaryFilters = {}): Promise<CollectionsSummary> {
  const params = new URLSearchParams()
  if (filters.periodo) params.set('periodo', filters.periodo)
  if (filters.propertyId) params.set('property_id', filters.propertyId)
  const query = params.toString()
  return apiFetch<CollectionsSummary>(`/reports/collections-summary${query ? `?${query}` : ''}`)
}
