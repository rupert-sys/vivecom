import { apiFetch } from './client'

export interface SignupInput {
  nombre_condominio: string
  cantidad_casas: number
  nombre_admin: string
  telefono_admin: string
}

export interface SignupResponse {
  tenant_id: string
  nombre: string
  admin_email: string
  // Una cuenta utilizable por puesto desde el día uno (F0-12) — misma contraseña inicial que el admin.
  email_tesorero: string
  email_guardia: string
  email_vocero: string
  // casa1@dominio, casa2@dominio... para que el admin recién registrado se las dé a sus residentes
  // (no hay canal de correo, ver alcance: solo WhatsApp+SMS).
  emails_viviendas: string[]
}

export function signup(payload: SignupInput): Promise<SignupResponse> {
  return apiFetch<SignupResponse>('/signup', { method: 'POST', body: payload, auth: false })
}
