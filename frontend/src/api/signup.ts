import { apiFetch } from './client'

export interface SignupInput {
  nombre_condominio: string
  clabe_destino: string
  admin_email: string
  admin_password: string
}

export interface SignupResponse {
  tenant_id: string
  nombre: string
  admin_email: string
}

export function signup(payload: SignupInput): Promise<SignupResponse> {
  return apiFetch<SignupResponse>('/signup', { method: 'POST', body: payload, auth: false })
}
