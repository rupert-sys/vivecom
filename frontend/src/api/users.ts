import { apiFetch } from './client'
import type { Rol, UserAccount } from '../types'

export interface UserAccountInput {
  email: string
  password: string
  rol: Rol
}

export function listUsers(rol?: Rol): Promise<UserAccount[]> {
  return apiFetch<UserAccount[]>(`/users${rol ? `?rol=${rol}` : ''}`)
}

export function createUser(payload: UserAccountInput): Promise<UserAccount> {
  return apiFetch<UserAccount>('/users', { method: 'POST', body: payload })
}
