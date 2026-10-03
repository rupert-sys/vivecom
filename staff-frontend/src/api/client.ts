const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
// Distinto de 'vivecom_token' (el del panel de condominio, frontend/): un token de staff no da acceso a
// ningún tenant y viceversa — si algún día se abren ambos paneles en el mismo navegador, no deben pisarse.
const TOKEN_STORAGE_KEY = 'vivecom_staff_token'

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_STORAGE_KEY)
}

export function setToken(token: string | null): void {
  if (token === null) {
    localStorage.removeItem(TOKEN_STORAGE_KEY)
  } else {
    localStorage.setItem(TOKEN_STORAGE_KEY, token)
  }
}

interface ApiFetchOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE'
  body?: unknown
  auth?: boolean
}

function extraerMensajeDeError(detail: unknown): string {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length > 0 && typeof detail[0]?.msg === 'string') {
    return detail[0].msg.replace(/^Value error, /, '')
  }
  return 'Ocurrió un error inesperado.'
}

// Subida de un archivo (multipart/form-data). No se fija Content-Type a mano: el navegador lo arma
// con el boundary correcto. Mismo patrón que frontend/src/api/client.ts.
export async function apiUpload<T>(path: string, formData: FormData): Promise<T> {
  const headers: Record<string, string> = {}
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`

  const response = await fetch(`${API_URL}${path}`, { method: 'POST', headers, body: formData })
  const isJson = response.headers.get('content-type')?.includes('application/json')
  const data = isJson ? await response.json() : undefined
  if (!response.ok) {
    throw new ApiError(response.status, extraerMensajeDeError(data?.detail))
  }
  return data as T
}

// Descarga binaria con el token de staff como credencial (el recibo no es un enlace firmado anónimo —
// ver api/staff_tenants.py). Mismo patrón que frontend/src/api/downloadFile.ts.
export async function apiDownload(path: string): Promise<Blob> {
  const token = getToken()
  const response = await fetch(`${API_URL}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!response.ok) {
    let message = 'No se pudo descargar el archivo.'
    if (response.headers.get('content-type')?.includes('application/json')) {
      const data = await response.json()
      if (typeof data?.detail === 'string') message = data.detail
    }
    throw new ApiError(response.status, message)
  }
  return response.blob()
}

export async function apiFetch<T>(path: string, options: ApiFetchOptions = {}): Promise<T> {
  const { method = 'GET', body, auth = true } = options

  const headers: Record<string, string> = {}
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (auth) {
    const token = getToken()
    if (token) headers.Authorization = `Bearer ${token}`
  }

  const response = await fetch(`${API_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })

  if (response.status === 204) {
    return undefined as T
  }

  const isJson = response.headers.get('content-type')?.includes('application/json')
  const data = isJson ? await response.json() : undefined

  if (!response.ok) {
    throw new ApiError(response.status, extraerMensajeDeError(data?.detail))
  }

  return data as T
}
