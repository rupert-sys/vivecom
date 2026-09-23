import { apiFetch } from './client'

interface TokenResponse {
  access_token: string
}

export interface JwtPayload {
  sub: string
  tenant_id: string
  schema: string
  rol: string
  property_id: string | null
  // Alta por /signup: contraseña inicial = nombre del condominio, temporal — el panel fuerza cambiarla
  // antes de dejar hacer cualquier otra cosa (ver RequiereCambiarPassword). Opcional (no obligatorio en
  // decodeToken/las pruebas existentes): un token viejo, de antes de este campo, simplemente no lo trae.
  debe_cambiar_password?: boolean
  exp: number
}

export async function login(email: string, password: string): Promise<string> {
  const { access_token } = await apiFetch<TokenResponse>('/auth/login', {
    method: 'POST',
    body: { email, password },
    auth: false,
  })
  return access_token
}

// El JWT solo se decodifica en el cliente para mostrar/ocultar UI (ej. botón
// de borrar solo si rol=admin) — el backend es quien realmente valida el
// rol en cada endpoint (require_roles), esto nunca es una barrera de seguridad.
export function decodeToken(token: string): JwtPayload | null {
  try {
    const payloadBase64 = token.split('.')[1]
    const json = atob(payloadBase64.replace(/-/g, '+').replace(/_/g, '/'))
    return JSON.parse(json) as JwtPayload
  } catch {
    return null
  }
}
