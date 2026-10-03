import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  actualizarTenant,
  cambiarPasswordDelAdmin,
  descargarRecibo,
  enviarAPapelera,
  listarPagos,
  obtenerTenant,
  registrarPago,
  type TenantDetail,
  type TenantPayment,
  type TipoPagoTenant,
} from '../api/tenants'
import { ApiError } from '../api/client'

const ETIQUETA_TIPO_PAGO: Record<TipoPagoTenant, string> = {
  efectivo: 'Efectivo',
  transferencia: 'Transferencia',
}

const estiloMiniCard = {
  background: 'var(--surface)',
  border: '1px solid var(--border)',
  borderRadius: 'var(--radius)',
  padding: 'var(--space-2) var(--space-3)',
  flex: 1,
  minWidth: 100,
} as const

function MiniCard({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={estiloMiniCard}>
      <div style={{ color: 'var(--ink-soft)', fontSize: '0.85rem' }}>{label}</div>
      <div className="mono" style={{ fontSize: '1.25rem' }}>
        {children}
      </div>
    </div>
  )
}

export function TenantDetailPage() {
  const { tenantId } = useParams<{ tenantId: string }>()
  const navigate = useNavigate()
  const [tenant, setTenant] = useState<TenantDetail | null>(null)
  const [nombre, setNombre] = useState('')
  const [precio, setPrecio] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [guardando, setGuardando] = useState(false)

  const [passwordNueva, setPasswordNueva] = useState('')
  const [cambiandoPassword, setCambiandoPassword] = useState(false)
  const [passwordCambiada, setPasswordCambiada] = useState(false)

  const [pagos, setPagos] = useState<TenantPayment[] | null>(null)
  const [fechaPago, setFechaPago] = useState('')
  const [montoPago, setMontoPago] = useState('')
  const [tipoPago, setTipoPago] = useState<TipoPagoTenant>('transferencia')
  const [notasPago, setNotasPago] = useState('')
  const [reciboPago, setReciboPago] = useState<File | null>(null)
  const [registrandoPago, setRegistrandoPago] = useState(false)

  useEffect(() => {
    if (!tenantId) return
    obtenerTenant(tenantId)
      .then((t) => {
        setTenant(t)
        setNombre(t.nombre)
        setPrecio(String(t.precio_por_vivienda))
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : 'No se pudo cargar el condominio.'))
    listarPagos(tenantId)
      .then(setPagos)
      .catch((err) => setError(err instanceof ApiError ? err.message : 'No se pudieron cargar los pagos.'))
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

  async function handleCambiarPassword(event: FormEvent) {
    event.preventDefault()
    setCambiandoPassword(true)
    setPasswordCambiada(false)
    setError(null)
    try {
      await cambiarPasswordDelAdmin(id, passwordNueva)
      setPasswordNueva('')
      setPasswordCambiada(true)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo cambiar la contraseña.')
    } finally {
      setCambiandoPassword(false)
    }
  }

  async function handleRegistrarPago(event: FormEvent) {
    event.preventDefault()
    setRegistrandoPago(true)
    setError(null)
    try {
      const nuevo = await registrarPago(id, {
        fecha: fechaPago,
        monto: Number(montoPago),
        tipo_pago: tipoPago,
        notas: notasPago.trim() || undefined,
        recibo: reciboPago ?? undefined,
      })
      setPagos((actuales) => [nuevo, ...(actuales ?? [])])
      setFechaPago('')
      setMontoPago('')
      setNotasPago('')
      setReciboPago(null)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo registrar el pago.')
    } finally {
      setRegistrandoPago(false)
    }
  }

  async function handleVerRecibo(pago: TenantPayment) {
    setError(null)
    try {
      const blob = await descargarRecibo(id, pago.id)
      const url = URL.createObjectURL(blob)
      window.open(url, '_blank')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo abrir el recibo.')
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)', maxWidth: 620 }}>
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
          <strong>Cuota del condominio:</strong>{' '}
          <span className="mono">${(tenant.precio_por_vivienda * tenant.viviendas).toFixed(2)}</span>
          {' '}
          <span style={{ color: 'var(--ink-soft)' }}>(${tenant.precio_por_vivienda.toFixed(2)} por vivienda)</span>
        </p>
        <p style={{ margin: 0 }}>
          <strong>Admin del condominio:</strong> {tenant.email_admin ?? 'sin cuenta admin todavía'}
        </p>
        {tenant.nombre_admin && (
          <p style={{ margin: 0 }}>
            <strong>Nombre del admin:</strong> {tenant.nombre_admin}
          </p>
        )}
        {tenant.telefono_admin && (
          <p style={{ margin: 0 }}>
            <strong>Teléfono del admin:</strong> <span className="mono">{tenant.telefono_admin}</span>
          </p>
        )}
        <p style={{ margin: 0 }}>
          <strong>Alta:</strong> <span className="mono">{new Date(tenant.fecha_creacion).toLocaleDateString('es-MX')}</span>
        </p>
      </div>

      <div>
        <h3 style={{ marginBottom: 'var(--space-2)' }}>Ocupación de las viviendas</h3>
        <div style={{ display: 'flex', gap: 'var(--space-2)', flexWrap: 'wrap' }}>
          <MiniCard label="Total">{tenant.ocupacion.total}</MiniCard>
          <MiniCard label="De propietario">{tenant.ocupacion.propietario}</MiniCard>
          <MiniCard label="Rentadas">{tenant.ocupacion.inquilino}</MiniCard>
          <MiniCard label="Sin residente">{tenant.ocupacion.sin_residente}</MiniCard>
        </div>
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

      {tenant.email_admin && (
        <form onSubmit={handleCambiarPassword} className="card" style={{ padding: 'var(--space-4)', display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          <h3 style={{ margin: 0 }}>Cambiar la contraseña del administrador</h3>
          <p style={{ color: 'var(--ink-soft)', margin: 0 }}>
            Fija una contraseña nueva para <strong>{tenant.email_admin}</strong>. No se puede ver la actual.
          </p>
          <label>
            Contraseña nueva
            <input
              type="password"
              minLength={8}
              value={passwordNueva}
              onChange={(e) => setPasswordNueva(e.target.value)}
              required
              style={{ display: 'block', width: '100%', marginTop: 4 }}
            />
          </label>
          <button type="submit" disabled={cambiandoPassword}>
            {cambiandoPassword ? 'Cambiando…' : 'Cambiar contraseña'}
          </button>
          {passwordCambiada && <p style={{ color: 'var(--teal)', margin: 0 }}>Contraseña actualizada.</p>}
        </form>
      )}

      <div>
        <h3 style={{ marginBottom: 'var(--space-2)' }}>Pagos del condominio a Vivecom</h3>
        {pagos === null ? (
          <p>Cargando…</p>
        ) : (
          <table className="card" style={{ width: '100%', marginBottom: 'var(--space-3)' }}>
            <thead>
              <tr>
                <th>Fecha</th>
                <th>Monto</th>
                <th>Tipo</th>
                <th>Notas</th>
                <th>Recibo</th>
              </tr>
            </thead>
            <tbody>
              {pagos.map((p) => (
                <tr key={p.id}>
                  <td className="mono">{new Date(`${p.fecha}T00:00:00`).toLocaleDateString('es-MX')}</td>
                  <td className="mono">${p.monto.toFixed(2)}</td>
                  <td>{ETIQUETA_TIPO_PAGO[p.tipo_pago]}</td>
                  <td>{p.notas ?? '—'}</td>
                  <td>
                    {p.tiene_recibo ? (
                      <button type="button" onClick={() => handleVerRecibo(p)}>
                        Ver recibo
                      </button>
                    ) : (
                      '—'
                    )}
                  </td>
                </tr>
              ))}
              {pagos.length === 0 && (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', color: 'var(--ink-faint)' }}>
                    Todavía no hay pagos registrados.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}

        <form onSubmit={handleRegistrarPago} className="card" style={{ padding: 'var(--space-4)', display: 'flex', gap: 'var(--space-2)', flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <label>
            Fecha
            <input type="date" value={fechaPago} onChange={(e) => setFechaPago(e.target.value)} required style={{ display: 'block', marginTop: 4 }} />
          </label>
          <label>
            Monto
            <input
              type="number"
              min="0.01"
              step="0.01"
              value={montoPago}
              onChange={(e) => setMontoPago(e.target.value)}
              required
              style={{ display: 'block', marginTop: 4 }}
            />
          </label>
          <label>
            Tipo de pago
            <select value={tipoPago} onChange={(e) => setTipoPago(e.target.value as TipoPagoTenant)} style={{ display: 'block', marginTop: 4 }}>
              <option value="transferencia">Transferencia</option>
              <option value="efectivo">Efectivo</option>
            </select>
          </label>
          <label>
            Notas (opcional)
            <input value={notasPago} onChange={(e) => setNotasPago(e.target.value)} style={{ display: 'block', marginTop: 4 }} />
          </label>
          <label>
            Recibo (foto o PDF, opcional)
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp,image/heic,application/pdf"
              onChange={(e) => setReciboPago(e.target.files?.[0] ?? null)}
              style={{ display: 'block', marginTop: 4 }}
            />
          </label>
          <button type="submit" disabled={registrandoPago}>
            {registrandoPago ? 'Registrando…' : 'Registrar pago'}
          </button>
        </form>
      </div>

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
