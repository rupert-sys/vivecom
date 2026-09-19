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

export type RecargoModalidad = 'unico' | 'mensual_sobre_saldo'

// Reglas del reglamento interior de ESTE condominio (GET /tenant/reglamento).
// recargo_porcentaje llega como fracción (0.05 = 5%), no como entero.
export interface Reglamento {
  dia_limite_pago: number
  dia_recargo: number
  recargo_porcentaje: number
  recargo_modalidad: RecargoModalidad
  acepta_pago_efectivo: boolean
  morosos_sin_voto: boolean
  morosos_sin_areas_comunes: boolean
  gasto_umbral_asamblea: number | null
  cotizaciones_minimas: number
  cajones_visitas: number
  horas_max_estacionamiento_visitas: number
  dudas_en_avisos_por_defecto: boolean
}

export type EstatusCobranza = 'al_corriente' | 'pendiente' | 'moroso'

export interface EstatusVivienda {
  property_id: string
  identificador: string
  estatus: EstatusCobranza
  adeudo_total: number
  cargos_vencidos: number
  periodo_pagado: boolean | null
}

export interface CollectionStatus {
  periodo: string
  total_viviendas: number
  al_corriente: number
  pendientes: number
  morosas: number
  adeudo_total: number
  viviendas: EstatusVivienda[]
}

export interface AccountStatement {
  property_id: string
  identificador: string
  saldo_a_favor: number
  deuda_total: number
  en_mora: boolean
  restricciones_por_mora: string[]
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

export type EstadoComprobante = 'pendiente' | 'aceptado' | 'rechazado'

// Comprobante de pago que el residente adjunta desde su app; tesorería lo acepta o rechaza.
export interface PaymentProof {
  id: string
  property_id: string
  monto: number
  fecha_pago: string | null
  nota: string | null
  estado: EstadoComprobante
  created_at: string
  revisado_en: string | null
  motivo_rechazo: string | null
  payment_id: string | null
  archivo_url: string // enlace firmado de vida corta al archivo
}

export type TipoGasto = 'operativo' | 'programado' | 'extraordinario'
export type TipoComprobante = 'remision' | 'factura'

export interface Cotizacion {
  proveedor: string
  monto: number
  url?: string | null
}

export interface Expense {
  id: string
  categoria: string
  monto: number
  comprobante_url: string
  fecha: string
  tipo: TipoGasto
  aprobado_en_asamblea: boolean
  acta_referencia: string | null
  cotizaciones: Cotizacion[] | null
  tipo_comprobante: TipoComprobante | null
}

export interface TotalPorConcepto {
  concepto: string
  total: number
  cantidad: number
}

// Estado financiero del condominio: saldo > 0 es a favor, < 0 en contra.
export interface FinancialSummary {
  desde: string | null
  hasta: string | null
  ingresos: number
  gastos: number
  saldo: number
  por_cobrar: number
  gastos_por_tipo: TotalPorConcepto[]
  gastos_por_categoria: TotalPorConcepto[]
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
  // Reglas propias del condominio (reglamento). dias_semana: 0=lunes … 6=domingo.
  dias_anticipacion_minimos: number
  hora_inicio_permitida: string | null
  hora_fin_maxima: string | null
  dias_semana_permitidos: number[] | null
  capacidad: number
  cuota: number
  max_duracion_horas: number | null
  notas_reglamento: string | null
  reglas: string[]
}

export type EstadoReserva = 'pendiente' | 'aprobada' | 'rechazada' | 'expirada'

export interface Reservation {
  id: string
  amenity_id: string
  property_id: string
  fecha_inicio: string
  fecha_fin: string
  estado: EstadoReserva
  cuota: number
  cuota_pagada: boolean
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

export type TipoIncidencia = 'seguridad' | 'mantenimiento' | 'otro'

export interface Incident {
  id: string
  reportado_por: string
  estado: EstadoIncidencia
  descripcion: string
  created_at: string
  resolved_at: string | null
  // Foto de la incidencia: un enlace firmado de vida corta si se subió como archivo desde la caseta.
  foto_url: string | null
  tipo: TipoIncidencia
  property_id: string | null
  persona_involucrada: string | null
}

export type TipoAcceso = 'residente' | 'visitante' | 'proveedor'

export interface AccessLogEntry {
  id: string
  property_id: string | null
  tipo: TipoAcceso
  hora_entrada: string
  hora_salida: string | null
  placas: string[]
  nombre_visitante: string | null
  acompanantes: number
  identificacion: string | null
  autorizado_por: 'residente_previo' | 'telefono' | 'otro' | null
}

// Cajones de visitas libres ahora mismo (reglamento Art. 2 IX-XI).
export interface VisitorParking {
  total_cajones: number
  ocupados: number
  libres: number
  horas_maximas: number
  excedidos: string[]
}

export interface Announcement {
  id: string
  titulo: string
  contenido: string
  fecha_publicacion: string
  // Dudas de los residentes: las activa el administrador al publicar (o el condominio por defecto).
  permite_dudas: boolean
  dudas_hasta: string | null // última fecha para mandar dudas; null = sin límite
  dudas_abiertas: boolean // ¿se pueden mandar HOY? (activadas y dentro del plazo)
}

// Duda de un residente sobre un aviso. Va solo a la administración y al comité; si se publica como
// aclaración la ven todos, sin vivienda.
export interface AnnouncementQuestion {
  id: string
  announcement_id: string
  aviso_titulo: string | null
  texto: string
  estado: 'abierta' | 'respondida'
  respuesta: string | null
  respondido_en: string | null
  publica: boolean
  created_at: string
  vivienda: string | null
}

export interface ReadStatusEntry {
  property_id: string
  identificador: string
  leido: boolean
  leido_at: string | null
}
