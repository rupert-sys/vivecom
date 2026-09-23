import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { updateUser } from '../api/users'
import { ApiError } from '../api/client'

// Alta por /signup: la contraseña inicial del admin es el nombre del condominio, temporal por diseño — esta
// pantalla se muestra ANTES que cualquier otra (ver RequireAuth) mientras el JWT traiga debe_cambiar_password.
export function CambiarPasswordObligatorioPage() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const [password, setPassword] = useState('')
  const [confirmacion, setConfirmacion] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    if (password !== confirmacion) {
      setError('Las dos contraseñas no coinciden.')
      return
    }
    if (!user) return
    setSubmitting(true)
    try {
      await updateUser(user.sub, { password })
      // debe_cambiar_password vive en el JWT (sin estado): el token actual sigue trayendo el valor viejo
      // hasta que se vuelva a iniciar sesión — más simple y robusto que reconstruir el token en el cliente.
      logout()
      navigate('/login', { state: { mensaje: 'Contraseña actualizada: inicia sesión de nuevo con tu contraseña nueva.' } })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo cambiar la contraseña.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <form
        onSubmit={handleSubmit}
        style={{
          background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)',
          padding: 'var(--space-5)', width: 360, display: 'flex', flexDirection: 'column', gap: 'var(--space-3)',
        }}
      >
        <h2>Cambia tu contraseña</h2>
        <p style={{ color: 'var(--ink-soft)', margin: 0 }}>
          Tu contraseña actual es temporal (el nombre del condominio). Elige una nueva antes de continuar.
        </p>
        <label>
          Contraseña nueva (mínimo 8 caracteres)
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={8}
            required
            style={{ display: 'block', width: '100%', marginTop: 4 }}
          />
        </label>
        <label>
          Confírmala
          <input
            type="password"
            value={confirmacion}
            onChange={(e) => setConfirmacion(e.target.value)}
            minLength={8}
            required
            style={{ display: 'block', width: '100%', marginTop: 4 }}
          />
        </label>
        {error && <p style={{ color: 'var(--brick)', margin: 0 }}>{error}</p>}
        <button
          type="submit"
          disabled={submitting}
          style={{ background: 'var(--teal)', color: 'white', border: 'none', padding: 8, borderRadius: 'var(--radius)' }}
        >
          {submitting ? 'Guardando…' : 'Cambiar contraseña'}
        </button>
      </form>
    </div>
  )
}
