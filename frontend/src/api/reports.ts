import { apiFetch } from './client'
import { downloadFile } from './downloadFile'
import type { CollectionStatus, CollectionsSummary } from '../types'

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

// Quién pagó, quién falta y quién es moroso, por vivienda.
export function getCollectionStatus(periodo?: string): Promise<CollectionStatus> {
  return apiFetch<CollectionStatus>(`/reports/collection-status${periodo ? `?periodo=${periodo}` : ''}`)
}

// Constancia de no adeudo (reglamento Art. 16): PDF; el backend responde 409 si la vivienda debe algo.
export function downloadNoDebtCertificate(propertyId: string, identificador: string): Promise<void> {
  return downloadFile(`/reports/no-debt-certificate/${propertyId}`, `constancia-no-adeudo-${identificador}.pdf`)
}
