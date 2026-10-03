import { apiDownload, apiFetch, apiUpload } from './client'

export interface TenantListItem {
  tenant_id: string
  nombre: string
  activo: boolean
  fecha_creacion: string
  precio_por_vivienda: number
  viviendas: number
  en_papelera: boolean
  papelera_en: string | null
}

export interface OcupacionResumen {
  total: number
  propietario: number
  inquilino: number
  sin_residente: number
}

export interface TenantDetail extends TenantListItem {
  email_admin: string | null
  nombre_admin: string | null
  telefono_admin: string | null
  ocupacion: OcupacionResumen
}

export type TipoPagoTenant = 'efectivo' | 'transferencia'

export interface TenantPayment {
  id: string
  tenant_id: string
  fecha: string
  monto: number
  tipo_pago: TipoPagoTenant
  notas: string | null
  tiene_recibo: boolean
  registrado_en: string
}

export interface TenantPaymentInput {
  fecha: string
  monto: number
  tipo_pago: TipoPagoTenant
  notas?: string
  recibo?: File
}

export interface TenantUpdate {
  activo?: boolean
  nombre?: string
  precio_por_vivienda?: number
}

export interface TenantCreateRequest {
  nombre_condominio: string
  cantidad_casas: number
  nombre_admin: string
  telefono_admin: string
}

export interface TenantCreateResponse {
  tenant_id: string
  nombre: string
  email_admin: string
  emails_viviendas: string[]
}

export function listarTenants(): Promise<TenantListItem[]> {
  return apiFetch<TenantListItem[]>('/staff/tenants')
}

export function obtenerTenant(tenantId: string): Promise<TenantDetail> {
  return apiFetch<TenantDetail>(`/staff/tenants/${tenantId}`)
}

export function actualizarTenant(tenantId: string, cambios: TenantUpdate): Promise<TenantDetail> {
  return apiFetch<TenantDetail>(`/staff/tenants/${tenantId}`, { method: 'PATCH', body: cambios })
}

export function crearTenant(datos: TenantCreateRequest): Promise<TenantCreateResponse> {
  return apiFetch<TenantCreateResponse>('/staff/tenants', { method: 'POST', body: datos })
}

export function listarPapelera(): Promise<TenantListItem[]> {
  return apiFetch<TenantListItem[]>('/staff/tenants/papelera')
}

export function enviarAPapelera(tenantId: string): Promise<TenantDetail> {
  return apiFetch<TenantDetail>(`/staff/tenants/${tenantId}/papelera`, { method: 'POST' })
}

export function restaurarDePapelera(tenantId: string): Promise<TenantDetail> {
  return apiFetch<TenantDetail>(`/staff/tenants/${tenantId}/restaurar`, { method: 'POST' })
}

export function borrarPermanentemente(tenantId: string, password: string): Promise<void> {
  return apiFetch<void>(`/staff/tenants/${tenantId}`, { method: 'DELETE', body: { password } })
}

export function cambiarPasswordDelAdmin(tenantId: string, password: string): Promise<void> {
  return apiFetch<void>(`/staff/tenants/${tenantId}/admin/password`, { method: 'POST', body: { password } })
}

export function listarPagos(tenantId: string): Promise<TenantPayment[]> {
  return apiFetch<TenantPayment[]>(`/staff/tenants/${tenantId}/payments`)
}

export function registrarPago(tenantId: string, datos: TenantPaymentInput): Promise<TenantPayment> {
  const formData = new FormData()
  formData.append('fecha', datos.fecha)
  formData.append('monto', String(datos.monto))
  formData.append('tipo_pago', datos.tipo_pago)
  if (datos.notas) formData.append('notas', datos.notas)
  if (datos.recibo) formData.append('recibo', datos.recibo)
  return apiUpload<TenantPayment>(`/staff/tenants/${tenantId}/payments`, formData)
}

export function descargarRecibo(tenantId: string, paymentId: string): Promise<Blob> {
  return apiDownload(`/staff/tenants/${tenantId}/payments/${paymentId}/recibo`)
}
