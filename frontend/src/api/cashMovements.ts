import { apiFetch } from './client'
import type { CashBalance, CashMovement, TipoCaja, TipoMovimientoCaja } from '../types'

export interface CashMovementInput {
  caja: TipoCaja
  tipo: TipoMovimientoCaja
  monto: number
  motivo: string
  fecha: string
}

export function listCashMovements(caja?: TipoCaja): Promise<CashMovement[]> {
  return apiFetch<CashMovement[]>(`/cash-movements${caja ? `?caja=${caja}` : ''}`)
}

export function createCashMovement(payload: CashMovementInput): Promise<CashMovement> {
  return apiFetch<CashMovement>('/cash-movements', { method: 'POST', body: payload })
}

export function getCashBalance(): Promise<CashBalance> {
  return apiFetch<CashBalance>('/cash-movements/balance')
}
