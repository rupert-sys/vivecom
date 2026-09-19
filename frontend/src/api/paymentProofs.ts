import { apiFetch } from './client'
import type { PaymentProof, EstadoComprobante } from '../types'

export function listPaymentProofs(estado?: EstadoComprobante): Promise<PaymentProof[]> {
  return apiFetch<PaymentProof[]>(`/payment-proofs${estado ? `?estado=${estado}` : ''}`)
}

// `monto`: lo que de verdad llegó, si difiere de lo que declaró el residente.
// `forzar`: confirma que NO es el mismo pago que el SPEI ya detectó (el backend responde 409 si parece serlo).
export function acceptPaymentProof(id: string, opciones: { monto?: number; forzar?: boolean } = {}): Promise<PaymentProof> {
  return apiFetch<PaymentProof>(`/payment-proofs/${id}/accept`, { method: 'POST', body: opciones })
}

export function rejectPaymentProof(id: string, motivo: string): Promise<PaymentProof> {
  return apiFetch<PaymentProof>(`/payment-proofs/${id}/reject`, { method: 'POST', body: { motivo } })
}
