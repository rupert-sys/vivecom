import { useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { signup, type SignupResponse } from '../api/signup'
import { ApiError } from '../api/client'

type Paso = 'condominio' | 'registro' | 'listo'

// Landing de bienvenida del panel: en dos pasos (condominio, luego quien se registra) da de alta el condominio
// completo — viviendas incluidas — sin pedir CLABE ni que el admin invente su propio email/contraseña (ver
// api/signup.py). El admin queda en administracion@<dominio>, con la contraseña temporal = el propio nombre
// del condominio; el panel se la pide cambiar de inmediato (ver RequireAuth/CambiarPasswordObligatorioPage).
export function SignupPage() {
  const { user, login } = useAuth()
  const navigate = useNavigate()

  const [paso, setPaso] = useState<Paso>('condominio')
  const [nombreCondominio, setNombreCondominio] = useState('')
  const [cantidadCasas, setCantidadCasas] = useState('')
  const [nombreAdmin, setNombreAdmin] = useState('')
  const [telefonoAdmin, setTelefonoAdmin] = useState('')
  const [resultado, setResultado] = useState<SignupResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  if (user !== null) return <Navigate to="/" replace />

  function handleContinuar(event: FormEvent) {
    event.preventDefault()
    setPaso('registro')
  }

  async function handleRegistrar(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      const creado = await signup({
        nombre_condominio: nombreCondominio,
        cantidad_casas: Number(cantidadCasas),
        nombre_admin: nombreAdmin,
        telefono_admin: telefonoAdmin,
      })
      setResultado(creado)
      setPaso('listo')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo crear el condominio.')
    } finally {
      setSubmitting(false)
    }
  }

  async function handleEntrar() {
    if (!resultado) return
    setSubmitting(true)
    try {
      // La contraseña inicial del admin es el propio nombre del condominio (ver arriba) — el panel lo forzará
      // a cambiarla en cuanto entre.
      await login(resultado.admin_email, nombreCondominio)
      navigate('/')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo iniciar sesión.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div
        style={{
          background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)',
          padding: 'var(--space-5)', width: 400, display: 'flex', flexDirection: 'column', gap: 'var(--space-3)',
        }}
      >
        <h2>Registra tu condominio</h2>

        {paso === 'condominio' && (
          <form onSubmit={handleContinuar} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
            <p style={{ color: 'var(--ink-soft)', margin: 0 }}>Paso 1 de 2 — datos del condominio.</p>
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
              Cantidad de viviendas
              <input
                type="number"
                min={1}
                value={cantidadCasas}
                onChange={(e) => setCantidadCasas(e.target.value)}
                required
                style={{ display: 'block', width: '100%', marginTop: 4 }}
              />
            </label>
            <p style={{ color: 'var(--ink-soft)', fontSize: '0.85rem', margin: 0 }}>
              Se crean de una vez: "Casa 1" a "Casa {cantidadCasas || 'N'}". Puedes renombrarlas después.
            </p>
            <button
              type="submit"
              style={{ background: 'var(--teal)', color: 'white', border: 'none', padding: 8, borderRadius: 'var(--radius)' }}
            >
              Continuar
            </button>
            <p style={{ margin: 0, fontSize: '0.9rem' }}>
              ¿Ya tienes cuenta? <Link to="/login">Inicia sesión</Link>
            </p>
          </form>
        )}

        {paso === 'registro' && (
          <form onSubmit={handleRegistrar} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
            <p style={{ color: 'var(--ink-soft)', margin: 0 }}>Paso 2 de 2 — regístrate como administrador.</p>
            <label>
              Tu nombre
              <input
                value={nombreAdmin}
                onChange={(e) => setNombreAdmin(e.target.value)}
                required
                style={{ display: 'block', width: '100%', marginTop: 4 }}
              />
            </label>
            <label>
              Tu teléfono
              <input
                value={telefonoAdmin}
                onChange={(e) => setTelefonoAdmin(e.target.value)}
                required
                style={{ display: 'block', width: '100%', marginTop: 4 }}
              />
            </label>
            {error && <p style={{ color: 'var(--brick)', margin: 0 }}>{error}</p>}
            <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
              <button type="button" onClick={() => setPaso('condominio')} style={{ flex: 1 }}>
                Atrás
              </button>
              <button
                type="submit"
                disabled={submitting}
                style={{ flex: 1, background: 'var(--teal)', color: 'white', border: 'none', padding: 8, borderRadius: 'var(--radius)' }}
              >
                {submitting ? 'Creando…' : 'Crear condominio'}
              </button>
            </div>
          </form>
        )}

        {paso === 'listo' && resultado && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
            <p style={{ margin: 0 }}>
              Tu cuenta de administrador: <strong className="mono">{resultado.admin_email}</strong>
              <br />
              Contraseña inicial: el nombre del condominio (te la pedirá cambiar al entrar).
            </p>
            <div>
              <p style={{ margin: '0 0 4px' }}>
                También se crearon cuentas listas para usarse (misma contraseña inicial que el admin):
              </p>
              <ul style={{ margin: 0, paddingLeft: '1.2em' }}>
                <li>
                  Tesorería: <span className="mono">{resultado.email_tesorero}</span>
                </li>
                <li>
                  Vigilancia: <span className="mono">{resultado.email_guardia}</span>
                </li>
                <li>
                  Vocero: <span className="mono">{resultado.email_vocero}</span>
                </li>
              </ul>
            </div>
            <div>
              <p style={{ margin: '0 0 4px' }}>Accesos para cada vivienda (compártelos con tus residentes):</p>
              <ul style={{ margin: 0, paddingLeft: '1.2em', maxHeight: 180, overflowY: 'auto' }}>
                {resultado.emails_viviendas.map((email) => (
                  <li key={email} className="mono">
                    {email}
                  </li>
                ))}
              </ul>
            </div>
            {error && <p style={{ color: 'var(--brick)', margin: 0 }}>{error}</p>}
            <button
              type="button"
              onClick={handleEntrar}
              disabled={submitting}
              style={{ background: 'var(--teal)', color: 'white', border: 'none', padding: 8, borderRadius: 'var(--radius)' }}
            >
              {submitting ? 'Entrando…' : 'Entrar al panel'}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
