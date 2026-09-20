import { apiFetch } from './client'
import type { EstadoAcuerdo, PaymentAgreement } from '../types'

export function listPaymentAgreements(estado?: EstadoAcuerdo): Promise<PaymentAgreement[]> {
  return apiFetch<PaymentAgreement[]>(`/payment-agreements${estado ? `?estado=${estado}` : ''}`)
}

export interface AgreementRequestInput {
  property_id: string // el administrador captura la solicitud que un vecino entregó en papel
  causa: string
  numero_de_pagos: number
  primer_pago: string
  archivo_id?: string
}

export function requestPaymentAgreement(payload: AgreementRequestInput): Promise<PaymentAgreement> {
  return apiFetch<PaymentAgreement>('/payment-agreements', { method: 'POST', body: payload })
}

// `pagos`: otro calendario que el propuesto (debe sumar la deuda cubierta). `congela_recargo`: el comité decide.
export function approvePaymentAgreement(
  id: string,
  opciones: { congela_recargo: boolean; pagos?: { fecha: string; monto: number }[] },
): Promise<PaymentAgreement> {
  return apiFetch<PaymentAgreement>(`/payment-agreements/${id}/approve`, { method: 'POST', body: opciones })
}

export function rejectPaymentAgreement(id: string, motivo: string): Promise<PaymentAgreement> {
  return apiFetch<PaymentAgreement>(`/payment-agreements/${id}/reject`, { method: 'POST', body: { motivo } })
}

export function cancelPaymentAgreement(id: string): Promise<PaymentAgreement> {
  return apiFetch<PaymentAgreement>(`/payment-agreements/${id}/cancel`, { method: 'POST' })
}
