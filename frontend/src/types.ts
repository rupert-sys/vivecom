export interface Property {
  id: string
  identificador: string
  referencia_pago: string
  saldo_a_favor: number
}

export type RolOcupacion = 'propietario' | 'inquilino'

export interface Resident {
  id: string
  nombre: string
  telefono: string
  email: string | null
}

export type Periodicidad = 'mensual' | 'bimestral'

export interface Fee {
  id: string
  monto: number
  periodicidad: Periodicidad
  activa_desde: string
}

export interface GlobalRules {
  recargo_porcentaje: number
  recargo_dia_del_mes: number
}

export interface TenantClabe {
  id: string
  nombre: string
  clabe_destino: string
}

export interface ClabeChangeLogEntry {
  id: string
  clabe_anterior: string
  clabe_nueva: string
  cambiado_por: string
  fecha: string
}

export interface PropertyCollectionsSummary {
  property_id: string
  identificador: string
  cobrado: number
  pendiente: number
}

export interface CollectionsSummary {
  periodo: string | null
  cobrado_total: number
  pendiente_total: number
  por_vivienda: PropertyCollectionsSummary[]
}

export interface Expense {
  id: string
  categoria: string
  monto: number
  comprobante_url: string
  fecha: string
}

export type PeriodicidadPresupuesto = 'mensual' | 'anual'

export interface Budget {
  id: string
  categoria: string
  periodicidad: PeriodicidadPresupuesto
  periodo: string
  monto_planeado: number
}

export interface BudgetComparison {
  categoria: string
  periodicidad: PeriodicidadPresupuesto
  monto_planeado: number
  monto_real: number
}
