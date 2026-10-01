import { apiFetch } from './client'

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

export interface TenantDetail extends TenantListItem {
  email_admin: string | null
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
