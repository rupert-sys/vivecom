import { apiFetch } from './client'
import type { Budget, BudgetComparison, PeriodicidadPresupuesto } from '../types'

export interface BudgetInput {
  categoria: string
  periodicidad: PeriodicidadPresupuesto
  periodo: string
  monto_planeado: number
}

export function listBudgets(): Promise<Budget[]> {
  return apiFetch<Budget[]>('/budgets')
}

export function createBudget(payload: BudgetInput): Promise<Budget> {
  return apiFetch<Budget>('/budgets', { method: 'POST', body: payload })
}

export function getBudgetReport(periodo?: string): Promise<BudgetComparison[]> {
  return apiFetch<BudgetComparison[]>(`/budgets/report${periodo ? `?periodo=${periodo}` : ''}`)
}
