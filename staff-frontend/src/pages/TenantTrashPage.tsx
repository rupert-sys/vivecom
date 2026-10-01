import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { borrarPermanentemente, listarPapelera, restaurarDePapelera, type TenantListItem } from '../api/tenants'
import { ApiError } from '../api/client'

export function TenantTrashPage() {
  const [tenants, setTenants] = useState<TenantListItem[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  // Un solo diálogo de confirmación abierto a la vez, identificado por el tenant que le pidió el borrado.
  const [confirmandoId, setConfirmandoId] = useState<string | null>(null)
  const [password, setPassword] = useState('')
  const [errorConfirmacion, setErrorConfirmacion] = useState<string | null>(null)
  const [procesando, setProcesando] = useState<string | null>(null)

  function cargar() {
    listarPapelera()
      .then(setTenants)
      .catch((err) => setError(err instanceof ApiError ? err.message : 'No se pudo cargar la papelera.'))
  }

  useEffect(cargar, [])

  async function handleRestaurar(tenantId: string) {
    setProcesando(tenantId)
    setError(null)
    try {
      await restaurarDePapelera(tenantId)
      cargar()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo restaurar.')
    } finally {
      setProcesando(null)
    }
  }

  function abrirConfirmacion(tenantId: string) {
    setConfirmandoId(tenantId)
    setPassword('')
    setErrorConfirmacion(null)
  }

  async function handleBorrarPermanentemente(tenantId: string) {
    if (!password) return
    setProcesando(tenantId)
    setErrorConfirmacion(null)
    try {
      await borrarPermanentemente(tenantId, password)
      setConfirmandoId(null)
      cargar()
    } catch (err) {
      setErrorConfirmacion(err instanceof ApiError ? err.message : 'No se pudo borrar.')
    } finally {
      setProcesando(null)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
      <div>
        <Link to="/">&larr; Condominios</Link>
        <h2 style={{ marginTop: 'var(--space-2)' }}>Papelera</h2>
        <p style={{ margin: 0, color: 'var(--ink-soft)' }}>
          {tenants ? `${tenants.length} condominio(s) en la papelera` : 'Cargando…'}
        </p>
      </div>

      {error && <p style={{ color: 'var(--brick)' }}>{error}</p>}

      {tenants && tenants.length === 0 && <p style={{ color: 'var(--ink-faint)' }}>La papelera está vacía.</p>}

      {tenants && tenants.length > 0 && (
        <table className="card" style={{ width: '100%' }}>
          <thead>
            <tr>
              <th>Nombre</th>
              <th>Viviendas</th>
              <th>Enviado a la papelera</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {tenants.map((t) => (
              <tr key={t.tenant_id}>
                <td>{t.nombre}</td>
                <td className="mono">{t.viviendas}</td>
                <td className="mono">{t.papelera_en ? new Date(t.papelera_en).toLocaleString('es-MX') : '—'}</td>
                <td>
                  {confirmandoId === t.tenant_id ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)', alignItems: 'flex-start' }}>
                      <label style={{ margin: 0 }}>
                        Tu contraseña (confirma que eres tú)
                        <input
                          type="password"
                          autoFocus
                          value={password}
                          onChange={(e) => setPassword(e.target.value)}
                          style={{ display: 'block', marginTop: 4 }}
                        />
                      </label>
                      {errorConfirmacion && <p style={{ color: 'var(--brick)', margin: 0 }}>{errorConfirmacion}</p>}
                      <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
                        <button
                          disabled={!password || procesando === t.tenant_id}
                          onClick={() => handleBorrarPermanentemente(t.tenant_id)}
                          style={{ color: 'var(--brick)' }}
                        >
                          {procesando === t.tenant_id ? 'Borrando…' : 'Confirmar borrado definitivo'}
                        </button>
                        <button onClick={() => setConfirmandoId(null)}>Cancelar</button>
                      </div>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
                      <button disabled={procesando === t.tenant_id} onClick={() => handleRestaurar(t.tenant_id)}>
                        Restaurar
                      </button>
                      <button
                        disabled={procesando === t.tenant_id}
                        onClick={() => abrirConfirmacion(t.tenant_id)}
                        style={{ color: 'var(--brick)' }}
                      >
                        Eliminar permanentemente
                      </button>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
