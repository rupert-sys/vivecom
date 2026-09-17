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
