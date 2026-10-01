import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { actualizarTenant, enviarAPapelera, obtenerTenant, type TenantDetail } from '../api/tenants'
import { ApiError } from '../api/client'

export function TenantDetailPage() {
  const { tenantId } = useParams<{ tenantId: string }>()
  const navigate = useNavigate()
  const [tenant, setTenant] = useState<TenantDetail | null>(null)
  const [nombre, setNombre] = useState('')
  const [precio, setPrecio] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [guardando, setGuardando] = useState(false)

  useEffect(() => {
    if (!tenantId) return
    obtenerTenant(tenantId)
      .then((t) => {
        setTenant(t)
        setNombre(t.nombre)
        setPrecio(String(t.precio_por_vivienda))
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : 'No se pudo cargar el condominio.'))
  }, [tenantId])

  if (error && !tenant) {
    return (
      <div>
        <p style={{ color: 'var(--brick)' }}>{error}</p>
        <Link to="/">&larr; Volver al listado</Link>
      </div>
    )
  }

  if (!tenant || !tenantId) return <p>Cargando…</p>
  const id = tenantId // useParams() lo tipa como string | undefined; ya se validó arriba que sí lo es.

  async function guardarCambios(cambios: Parameters<typeof actualizarTenant>[1]) {
    setGuardando(true)
    setError(null)
    try {
      const actualizado = await actualizarTenant(id, cambios)
      setTenant(actualizado)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo guardar el cambio.')
    } finally {
      setGuardando(false)
    }
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const precioNumerico = Number(precio)
    await guardarCambios({ nombre: nombre.trim(), precio_por_vivienda: precioNumerico })
  }

  async function handleEnviarAPapelera() {
    setGuardando(true)
    setError(null)
    try {
      await enviarAPapelera(id)
      navigate('/papelera')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo enviar a la papelera.')
      setGuardando(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)', maxWidth: 520 }}>
      <div>
        <Link to="/">&larr; Condominios</Link>
        <h2 style={{ marginTop: 'var(--space-2)' }}>{tenant.nombre}</h2>
        <span className={tenant.activo ? 'chip chip-teal' : 'chip chip-brick'}>
          {tenant.activo ? 'Activo' : 'Suspendido'}
        </span>
      </div>

      {error && <p style={{ color: 'var(--brick)' }}>{error}</p>}

      <div className="card" style={{ padding: 'var(--space-4)', display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
        <p style={{ margin: 0 }}>
          <strong>Viviendas:</strong> <span className="mono">{tenant.viviendas}</span>
        </p>
        <p style={{ margin: 0 }}>
          <strong>Admin del condominio:</strong> {tenant.email_admin ?? 'sin cuenta admin todavía'}
        </p>
        <p style={{ margin: 0 }}>
          <strong>Alta:</strong> <span className="mono">{new Date(tenant.fecha_creacion).toLocaleDateString('es-MX')}</span>
        </p>
      </div>

      <form onSubmit={handleSubmit} className="card" style={{ padding: 'var(--space-4)', display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
        <h3 style={{ margin: 0 }}>Editar</h3>
        <label>
          Nombre
          <input value={nombre} onChange={(e) => setNombre(e.target.value)} required style={{ display: 'block', width: '100%', marginTop: 4 }} />
        </label>
        <label>
          Cuota por vivienda
          <input
            type="number"
            min="0.01"
            step="0.01"
            value={precio}
            onChange={(e) => setPrecio(e.target.value)}
            required
            style={{ display: 'block', width: '100%', marginTop: 4 }}
          />
        </label>
        <button type="submit" disabled={guardando}>
          {guardando ? 'Guardando…' : 'Guardar cambios'}
        </button>
      </form>

      {tenant.en_papelera ? (
        <div className="card" style={{ padding: 'var(--space-4)' }}>
          <h3 style={{ margin: 0, marginBottom: 'var(--space-2)' }}>Este condominio está en la papelera</h3>
          <p style={{ color: 'var(--ink-soft)' }}>
            Restaurarlo o borrarlo en definitiva se hace desde la propia papelera, no aquí.
          </p>
          <Link to="/papelera">Ir a la papelera &rarr;</Link>
        </div>
      ) : (
        <>
          <div className="card" style={{ padding: 'var(--space-4)' }}>
            <h3 style={{ margin: 0, marginBottom: 'var(--space-2)' }}>
              {tenant.activo ? 'Suspender condominio' : 'Reactivar condominio'}
            </h3>
            <p style={{ color: 'var(--ink-soft)' }}>
              {tenant.activo
                ? 'Ningún usuario de este condominio podrá iniciar sesión mientras esté suspendido.'
                : 'El condominio volverá a permitir el inicio de sesión de sus usuarios.'}
            </p>
            <button
              disabled={guardando}
              onClick={() => guardarCambios({ activo: !tenant.activo })}
              style={tenant.activo ? { color: 'var(--brick)' } : {}}
            >
              {tenant.activo ? 'Suspender' : 'Reactivar'}
            </button>
          </div>

          <div className="card" style={{ padding: 'var(--space-4)', borderColor: 'var(--brick-tint)' }}>
            <h3 style={{ margin: 0, marginBottom: 'var(--space-2)' }}>Papelera</h3>
            <p style={{ color: 'var(--ink-soft)' }}>
              Lo desactiva y lo mueve a la papelera — desde ahí se puede restaurar, o borrar en definitiva
              (eso sí es irreversible: borra todas sus viviendas, residentes y pagos).
            </p>
            <button disabled={guardando} onClick={handleEnviarAPapelera} style={{ color: 'var(--brick)' }}>
              Enviar a la papelera
            </button>
          </div>
        </>
      )}
    </div>
  )
}
