import { apiFetch } from './client'
import type { Rol, UserAccount } from '../types'

export interface UserAccountInput {
  email: string
  password: string
  rol: Rol
  property_id?: string | null
}

// Todos opcionales: solo cambia lo que se manda. property_id: null la quita; password vacío no se manda.
export interface UserAccountChanges {
  email?: string
  password?: string
  rol?: Rol
  property_id?: string | null
}

export function listUsers(rol?: Rol): Promise<UserAccount[]> {
  return apiFetch<UserAccount[]>(`/users${rol ? `?rol=${rol}` : ''}`)
}

export function createUser(payload: UserAccountInput): Promise<UserAccount> {
  return apiFetch<UserAccount>('/users', { method: 'POST', body: payload })
}

export function updateUser(id: string, changes: UserAccountChanges): Promise<UserAccount> {
  return apiFetch<UserAccount>(`/users/${id}`, { method: 'PATCH', body: changes })
}

export function deleteUser(id: string): Promise<void> {
  return apiFetch<void>(`/users/${id}`, { method: 'DELETE' })
}
