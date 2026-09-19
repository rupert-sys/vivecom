import { apiFetch } from './client'
import type { AccountStatement } from '../types'

export type MetodoPagoManual = 'efectivo' | 'transferencia'

// Pago capturado a mano por el tesorero (efectivo, o una transferencia que el SPEI no detectó).
// El backend responde 409 si el condominio no acepta efectivo.
export function createManualPayment(propertyId: string, monto: number, metodo: MetodoPagoManual): Promise<unknown> {
  return apiFetch('/payments/manual', { method: 'POST', body: { property_id: propertyId, monto, metodo } })
}

export function getAccountStatement(propertyId: string): Promise<AccountStatement> {
  return apiFetch<AccountStatement>(`/properties/${propertyId}/statement`)
}
