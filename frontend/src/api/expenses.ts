import { apiFetch } from './client'
import type { Expense, FinancialSummary, RecurrenciaGasto, TipoComprobante, TipoGasto } from '../types'

export interface ExpenseInput {
  categoria: string
  monto: number
  // Uno de los dos es obligatorio: el archivo subido (foto o PDF) o un enlace.
  comprobante_url?: string
  comprobante_archivo_id?: string
  fecha: string
  tipo?: TipoGasto
  aprobado_en_asamblea?: boolean
  acta_referencia?: string
  cotizaciones?: { proveedor: string; monto: number; archivo_id?: string }[]
  tipo_comprobante?: TipoComprobante
  recurrencia?: RecurrenciaGasto
}

export function listExpenses(): Promise<Expense[]> {
  return apiFetch<Expense[]>('/expenses')
}

export function createExpense(payload: ExpenseInput): Promise<Expense> {
  return apiFetch<Expense>('/expenses', { method: 'POST', body: payload })
}

export function getFinancialSummary(desde?: string, hasta?: string): Promise<FinancialSummary> {
  const params = new URLSearchParams()
  if (desde) params.set('desde', desde)
  if (hasta) params.set('hasta', hasta)
  const query = params.toString()
  return apiFetch<FinancialSummary>(`/expenses/summary${query ? `?${query}` : ''}`)
}
