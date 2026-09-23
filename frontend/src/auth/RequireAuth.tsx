import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from './AuthContext'

const RUTA_CAMBIAR_PASSWORD = '/cambiar-password'

export function RequireAuth({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  const { pathname } = useLocation()
  if (user === null) return <Navigate to="/login" replace />
  // Alta por /signup: contraseña temporal = nombre del condominio — nada más se ve hasta que la cambie.
  if (user.debe_cambiar_password && pathname !== RUTA_CAMBIAR_PASSWORD) {
    return <Navigate to={RUTA_CAMBIAR_PASSWORD} replace />
  }
  return children
}
