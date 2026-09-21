import { Navigate } from 'react-router-dom'
import { inicioDe } from '../permisos'
import { useAuth } from './AuthContext'

/** «/»: sin sesión va al inicio de sesión; con sesión, a la primera pantalla de su rol. */
export function Inicio() {
  const { user } = useAuth()
  if (user === null) return <Navigate to="/login" replace />
  return <Navigate to={inicioDe(user.rol) ?? '/sin-secciones'} replace />
}
