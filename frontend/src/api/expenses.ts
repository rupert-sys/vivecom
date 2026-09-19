import { apiFetch } from './client'
import type { Cotizacion, Expense, FinancialSummary, TipoComprobante, TipoGasto } from '../types'

export interface ExpenseInput {
  categoria: string
  monto: number
  comprobante_url: string
  fecha: string
  tipo?: TipoGasto
  aprobado_en_asamblea?: boolean
  acta_referencia?: string
  cotizaciones?: Cotizacion[]
  tipo_comprobante?: TipoComprobante
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
