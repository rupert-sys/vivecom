import { downloadFile } from './downloadFile'

export function exportAccountStatements(propertyId?: string): Promise<void> {
  const params = propertyId ? `?property_id=${propertyId}` : ''
  return downloadFile(`/reports/account-statements/export${params}`, 'estados_de_cuenta.xlsx')
}

export function exportExpenses(desde?: string, hasta?: string): Promise<void> {
  const params = new URLSearchParams()
  if (desde) params.set('desde', desde)
  if (hasta) params.set('hasta', hasta)
  const query = params.toString()
  return downloadFile(`/reports/expenses/export${query ? `?${query}` : ''}`, 'gastos.xlsx')
}

export function exportBudgetReport(periodo?: string): Promise<void> {
  const params = periodo ? `?periodo=${periodo}` : ''
  return downloadFile(`/reports/budget/export${params}`, 'presupuesto_vs_real.xlsx')
}
