import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { crearTenant, type TenantCreateResponse } from '../api/tenants'
import { ApiError } from '../api/client'

// panel.vivecom.com.mx y app.vivecom.com.mx son la MISMA app compartida para todos los condominios (el login
// decide a qué tenant entras) — no hay nada que desplegar por condominio nuevo, solo mostrar que ya están
// listos para este. Se derivan de VITE_API_URL (https://api.<dominio>) para no repetir el dominio a mano;
// en local (http://localhost:8000, sin "api.") no hay un equivalente limpio, así que se omiten.
function urlDePlataforma(prefijo: string): string | null {
  const apiUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
  if (!apiUrl.includes('api.')) return null
  return apiUrl.replace('api.', `${prefijo}.`)
}

export function TenantCreatePage() {
  const [nombreCondominio, setNombreCondominio] = useState('')
  const [cantidadCasas, setCantidadCasas] = useState('30')
  const [nombreAdmin, setNombreAdmin] = useState('')
  const [telefonoAdmin, setTelefonoAdmin] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [creando, setCreando] = useState(false)
  const [resultado, setResultado] = useState<TenantCreateResponse | null>(null)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setCreando(true)
    try {
      const respuesta = await crearTenant({
        nombre_condominio: nombreCondominio.trim(),
        cantidad_casas: Number(cantidadCasas),
        nombre_admin: nombreAdmin.trim(),
        telefono_admin: telefonoAdmin.trim(),
      })
      setResultado(respuesta)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo crear el condominio.')
    } finally {
      setCreando(false)
    }
  }

  if (resultado) {
    const urlPanel = urlDePlataforma('panel')
    const urlApp = urlDePlataforma('app')
    return (
      <div style={{ maxWidth: 520, display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
        <h2>{resultado.nombre} creado</h2>
        <p>
          Admin: <span className="mono">{resultado.email_admin}</span> — la contraseña inicial es el propio nombre
          del condominio, y se le pedirá cambiarla al entrar.
        </p>
        <div className="card" style={{ padding: 'var(--space-4)' }}>
          <h3 style={{ margin: 0, marginBottom: 'var(--space-2)' }}>Ya está listo para usarse</h3>
          <p style={{ margin: 0 }}>
            Panel del administrador:{' '}
            {urlPanel ? <a href={urlPanel} target="_blank" rel="noreferrer">{urlPanel}</a> : 'panel.vivecom.com.mx'}
          </p>
          <p style={{ margin: 0 }}>
            App de residentes:{' '}
            {urlApp ? <a href={urlApp} target="_blank" rel="noreferrer">{urlApp}</a> : 'app.vivecom.com.mx'}
          </p>
        </div>
        <details open>
          <summary>{resultado.emails_viviendas.length} cuenta(s) de vivienda generadas</summary>
          <p style={{ color: 'var(--ink-soft)' }}>
            Cada residente reclama la suya desde la app con sus propios datos. Cópialas para pasárselas al
            administrador (no hay canal de correo real: solo son identificadores de login).
          </p>
          <textarea readOnly value={resultado.emails_viviendas.join('\n')} rows={8} style={{ width: '100%' }} />
        </details>
        <Link to={`/${resultado.tenant_id}`}>Ver el condominio &rarr;</Link>
      </div>
    )
  }

  return (
    <div style={{ maxWidth: 480 }}>
      <Link to="/">&larr; Condominios</Link>
      <h2>Nuevo condominio</h2>
      <form onSubmit={handleSubmit} className="card" style={{ padding: 'var(--space-4)', display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
        <label>
          Nombre del condominio
          <input value={nombreCondominio} onChange={(e) => setNombreCondominio(e.target.value)} required style={{ display: 'block', width: '100%', marginTop: 4 }} />
        </label>
        <label>
          Cantidad de viviendas (30 a 80 es lo usual)
          <input
            type="number"
            min="1"
            value={cantidadCasas}
            onChange={(e) => setCantidadCasas(e.target.value)}
            required
            style={{ display: 'block', width: '100%', marginTop: 4 }}
          />
        </label>
        <label>
          Nombre de quien administrará el condominio
          <input value={nombreAdmin} onChange={(e) => setNombreAdmin(e.target.value)} required style={{ display: 'block', width: '100%', marginTop: 4 }} />
        </label>
        <label>
          Teléfono de contacto
          <input value={telefonoAdmin} onChange={(e) => setTelefonoAdmin(e.target.value)} required style={{ display: 'block', width: '100%', marginTop: 4 }} />
        </label>
        {error && <p style={{ color: 'var(--brick)', margin: 0 }}>{error}</p>}
        <button type="submit" disabled={creando}>
          {creando ? 'Creando…' : 'Crear condominio'}
        </button>
      </form>
    </div>
  )
}
