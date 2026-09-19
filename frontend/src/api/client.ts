const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
const TOKEN_STORAGE_KEY = 'vivecom_token'

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

// FastAPI regresa errores como {"detail": "mensaje"} (HTTPException) o
// {"detail": [{"msg": "...", "loc": [...]}, ...]} (422 de validación de
// Pydantic) — antes de esto solo se manejaba el primer caso, y cualquier
// error de validación (ej. la CLABE de F1-20) se veía como un mensaje
// genérico en vez del mensaje real del campo.
function extraerMensajeDeError(detail: unknown): string {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length > 0 && typeof detail[0]?.msg === 'string') {
    return detail[0].msg.replace(/^Value error, /, '')
  }
  return 'Ocurrió un error inesperado.'
}

// Subida de un archivo (multipart/form-data). No se fija Content-Type a mano: el navegador lo arma
// con el boundary correcto.
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
