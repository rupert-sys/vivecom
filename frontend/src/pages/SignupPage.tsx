import { useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { signup } from '../api/signup'
import { ApiError } from '../api/client'

export function SignupPage() {
  const { user, login } = useAuth()
  const navigate = useNavigate()

  const [nombreCondominio, setNombreCondominio] = useState('')
  const [clabeDestino, setClabeDestino] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  if (user !== null) return <Navigate to="/properties" replace />

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await signup({
        nombre_condominio: nombreCondominio,
        clabe_destino: clabeDestino,
        admin_email: email,
        admin_password: password,
      })
      // Auto-login tras el registro — el admin ya tiene cuenta y contraseña
      // válidas, no tiene sentido pedirle que las vuelva a escribir en /login.
      await login(email, password)
      navigate('/properties')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo crear el condominio.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <form
        onSubmit={handleSubmit}
        style={{
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius)',
          padding: 'var(--space-5)',
          width: 360,
          display: 'flex',
          flexDirection: 'column',
          gap: 'var(--space-3)',
        }}
      >
        <h2>Registra tu condominio</h2>
        <p style={{ color: 'var(--ink-soft)', margin: 0 }}>
          Se crea tu condominio y tu cuenta de administrador al instante.
        </p>
        <label>
          Nombre del condominio
          <input
            value={nombreCondominio}
            onChange={(e) => setNombreCondominio(e.target.value)}
            required
            style={{ display: 'block', width: '100%', marginTop: 4 }}
          />
        </label>
        <label>
          CLABE de destino (18 dígitos)
          <input
            value={clabeDestino}
            onChange={(e) => setClabeDestino(e.target.value)}
            maxLength={18}
            pattern="[0-9]{18}"
            required
            style={{ display: 'block', width: '100%', marginTop: 4 }}
          />
        </label>
        <label>
          Tu email (será tu usuario)
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            style={{ display: 'block', width: '100%', marginTop: 4 }}
          />
        </label>
        <label>
          Contraseña (mínimo 8 caracteres)
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
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
          {submitting ? 'Creando…' : 'Crear condominio'}
        </button>
        <p style={{ margin: 0, fontSize: '0.9rem' }}>
          ¿Ya tienes cuenta? <Link to="/login">Inicia sesión</Link>
        </p>
      </form>
    </div>
  )
}
