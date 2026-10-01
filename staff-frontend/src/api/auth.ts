import { apiFetch } from './client'

interface TokenResponse {
  access_token: string
}

export interface StaffJwtPayload {
  sub: string
  staff: true
  exp: number
}

export async function login(email: string, password: string): Promise<string> {
  const { access_token } = await apiFetch<TokenResponse>('/staff/login', {
    method: 'POST',
    body: { email, password },
    auth: false,
  })
  return access_token
}

export function decodeToken(token: string): StaffJwtPayload | null {
  try {
    const payloadBase64 = token.split('.')[1]
    const json = atob(payloadBase64.replace(/-/g, '+').replace(/_/g, '/'))
    return JSON.parse(json) as StaffJwtPayload
  } catch {
    return null
  }
}
