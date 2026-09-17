import { apiFetch } from './client'
import type { Expense } from '../types'

export interface ExpenseInput {
  categoria: string
  monto: number
  comprobante_url: string
  fecha: string
}

export function listExpenses(): Promise<Expense[]> {
  return apiFetch<Expense[]>('/expenses')
}

export function createExpense(payload: ExpenseInput): Promise<Expense> {
  return apiFetch<Expense>('/expenses', { method: 'POST', body: payload })
}
