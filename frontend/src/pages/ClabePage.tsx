import { useEffect, useState, type FormEvent } from 'react'
import { changeClabe, getClabe, getClabeHistory } from '../api/tenantConfig'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import type { ClabeChangeLogEntry, TenantClabe } from '../types'

export function ClabePage() {
  const { user } = useAuth()
  const isAdmin = user?.rol === 'admin'

  const [clabe, setClabe] = useState<TenantClabe | null>(null)
  const [historial, setHistorial] = useState<ClabeChangeLogEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const [clabeNueva, setClabeNueva] = useState('')
  const [confirmo, setConfirmo] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  async function reload() {
    setLoading(true)
    try {
      const [clabeResult, historialResult] = await Promise.all([
        getClabe(),
        isAdmin ? getClabeHistory() : Promise.resolve([]),
      ])
      setClabe(clabeResult)
      setHistorial(historialResult)
      setError(null)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo cargar la información de la cuenta CLABE.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    reload()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setSubmitting(true)
    setSuccess(null)
    try {
      await changeClabe(clabeNueva)
      setClabeNueva('')
      setConfirmo(false)
      setSuccess('La cuenta CLABE de destino se actualizó correctamente.')
      await reload()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo cambiar la cuenta CLABE.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div>
      <h2>Cuenta CLABE de destino</h2>
      {error && <p style={{ color: 'var(--brick)' }}>{error}</p>}
      {success && <p style={{ color: 'var(--teal)' }}>{success}</p>}

      {loading ? (
        <p>Cargando…</p>
      ) : (
        clabe && (
          <p>
            CLABE vigente: <span className="mono">{clabe.clabe_destino}</span>
          </p>
        )
      )}

      {isAdmin && (
        <>
          <h3>Cambiar cuenta CLABE</h3>
          <p style={{ color: 'var(--ink-soft)' }}>
            Este cambio afecta a dónde llegan todos los depósitos de las viviendas a partir de ahora. Requiere
            confirmación explícita y queda registrado en el historial de abajo.
          </p>
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)', maxWidth: 360 }}>
            <input
              placeholder="Nueva CLABE (18 dígitos)"
              value={clabeNueva}
              onChange={(e) => setClabeNueva(e.target.value)}
              maxLength={18}
              pattern="[0-9]{18}"
              required
            />
            <label style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
              <input type="checkbox" checked={confirmo} onChange={(e) => setConfirmo(e.target.checked)} />
              Confirmo que quiero cambiar la cuenta CLABE de destino.
            </label>
            <button type="submit" disabled={!confirmo || submitting} style={{ background: 'var(--teal)', color: 'white', border: 'none', padding: 8, borderRadius: 'var(--radius)' }}>
              {submitting ? 'Cambiando…' : 'Cambiar CLABE'}
            </button>
          </form>

          <h3>Historial de cambios</h3>
          {historial.length === 0 ? (
            <p>Todavía no se ha cambiado la cuenta CLABE.</p>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
                  <th>Fecha</th>
                  <th>CLABE anterior</th>
                  <th>CLABE nueva</th>
                </tr>
              </thead>
              <tbody>
                {historial.map((entry) => (
                  <tr key={entry.id} style={{ borderBottom: '1px solid var(--border)' }}>
                    <td className="mono">{new Date(entry.fecha).toLocaleString('es-MX')}</td>
                    <td className="mono">{entry.clabe_anterior}</td>
                    <td className="mono">{entry.clabe_nueva}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </div>
  )
}
