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
