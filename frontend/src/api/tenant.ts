import { apiFetch, apiUpload, ApiError, getToken } from './client'

export interface TenantConfig {
  id: string
  nombre: string
  tiene_logo: boolean
}

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export function getTenantConfig(): Promise<TenantConfig> {
  return apiFetch<TenantConfig>('/tenant')
}

export function updateTenantName(nombre: string): Promise<TenantConfig> {
  return apiFetch<TenantConfig>('/tenant', { method: 'PATCH', body: { nombre } })
}

export function uploadLogo(file: File): Promise<TenantConfig> {
  const formData = new FormData()
  formData.append('file', file)
  return apiUpload<TenantConfig>('/tenant/logo', formData)
}

export async function deleteLogo(): Promise<void> {
  const token = getToken()
  const response = await fetch(`${API_URL}/tenant/logo`, {
    method: 'DELETE',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!response.ok) throw new ApiError(response.status, 'No se pudo quitar el logo.')
}

// El logo se sirve por su propia ruta autenticada (no por enlace firmado de vida corta, como el resto de los
// archivos): el encabezado lo necesita disponible toda la sesión. Se trae como blob y se expone como object URL
// para un <img src>; null si el condominio no tiene logo o si algo falla (el encabezado sigue viéndose bien sin él).
export async function fetchLogoObjectUrl(): Promise<string | null> {
  const token = getToken()
  try {
    const response = await fetch(`${API_URL}/tenant/logo`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!response.ok) return null
    const blob = await response.blob()
    return URL.createObjectURL(blob)
  } catch {
    return null
  }
}
