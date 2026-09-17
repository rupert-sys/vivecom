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

export type Rol = 'admin' | 'tesorero' | 'comite_lectura' | 'comite_aprobador' | 'vocero' | 'residente' | 'guardia'

export interface UserAccount {
  id: string
  email: string
  rol: Rol
}

export interface Amenity {
  id: string
  nombre: string
  periodo_limite_horas: number
}

export interface Poll {
  id: string
  pregunta: string
  fecha_cierre: string
  resultados_en_vivo: boolean
  quorum_alcanzado: boolean
  reactivada: boolean
  opciones: { id: string; texto: string }[]
}

export type EstadoIncidencia = 'abierta' | 'en_proceso' | 'resuelta'

export interface Incident {
  id: string
  reportado_por: string
  estado: EstadoIncidencia
  descripcion: string
  created_at: string
  resolved_at: string | null
}

export type TipoAcceso = 'residente' | 'visitante' | 'proveedor'

export interface AccessLogEntry {
  id: string
  property_id: string | null
  tipo: TipoAcceso
  hora_entrada: string
  hora_salida: string | null
  placas: string[]
}

export interface Announcement {
  id: string
  titulo: string
  contenido: string
  fecha_publicacion: string
}

export interface ReadStatusEntry {
  property_id: string
  identificador: string
  leido: boolean
  leido_at: string | null
}
