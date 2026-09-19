import { useEffect, useState, type FormEvent } from 'react'
import { createFee, listFees, updateFee } from '../api/fees'
import { getReglamento } from '../api/reglamento'
import { Link } from 'react-router-dom'
import { formatoPorcentaje } from '../utils/reglamento'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import type { Fee, Periodicidad, Reglamento } from '../types'

export function FeesPage() {
  const { user } = useAuth()
  const isAdmin = user?.rol === 'admin'

  const [fees, setFees] = useState<Fee[]>([])
  const [reglamento, setReglamento] = useState<Reglamento | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [monto, setMonto] = useState('')
  const [periodicidad, setPeriodicidad] = useState<Periodicidad>('mensual')
  const [activaDesde, setActivaDesde] = useState('')
  const [creating, setCreating] = useState(false)

  const [editingId, setEditingId] = useState<string | null>(null)
  const [editMonto, setEditMonto] = useState('')
  const [editPeriodicidad, setEditPeriodicidad] = useState<Periodicidad>('mensual')
  const [editActivaDesde, setEditActivaDesde] = useState('')

  async function reload() {
    setLoading(true)
    try {
      const [feesResult, rulesResult] = await Promise.all([listFees(), getReglamento()])
      setFees(feesResult)
      setReglamento(rulesResult)
      setError(null)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo cargar la configuración de cuotas.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    reload()
  }, [])

  async function handleCreate(event: FormEvent) {
    event.preventDefault()
    setCreating(true)
    try {
      await createFee({ monto: Number(monto), periodicidad, activa_desde: activaDesde })
      setMonto('')
      setActivaDesde('')
      await reload()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo crear la cuota.')
    } finally {
      setCreating(false)
    }
  }

  function startEdit(fee: Fee) {
    setEditingId(fee.id)
    setEditMonto(String(fee.monto))
    setEditPeriodicidad(fee.periodicidad)
    setEditActivaDesde(fee.activa_desde)
  }

  async function handleSaveEdit(event: FormEvent, feeId: string) {
    event.preventDefault()
    try {
      await updateFee(feeId, {
        monto: Number(editMonto),
        periodicidad: editPeriodicidad,
        activa_desde: editActivaDesde,
      })
      setEditingId(null)
      await reload()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo actualizar la cuota.')
    }
  }

  return (
    <div>
      <h2>Configuración de cuotas</h2>
      {error && <p style={{ color: 'var(--brick)' }}>{error}</p>}

      {reglamento && (
        <p style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: 'var(--space-3)' }}>
          {/* recargo_porcentaje llega como fracción (0.05), no como porcentaje entero */}
          Recargo por mora: <span className="mono">{formatoPorcentaje(reglamento.recargo_porcentaje)}</span>{' '}
          ({reglamento.recargo_modalidad === 'mensual_sobre_saldo' ? 'mensual sobre el saldo vencido' : 'por única vez'}) a
          partir del día <span className="mono">{reglamento.dia_recargo}</span> de cada mes — según el reglamento de tu
          condominio{isAdmin ? <> (<Link to="/reglamento">cambiar en Reglamento</Link>)</> : ''}.
        </p>
      )}

      {isAdmin && (
        <form onSubmit={handleCreate} style={{ display: 'flex', gap: 'var(--space-2)', margin: 'var(--space-3) 0', flexWrap: 'wrap' }}>
          <input
            type="number"
            step="0.01"
            placeholder="Monto"
            value={monto}
            onChange={(e) => setMonto(e.target.value)}
            required
          />
          <select value={periodicidad} onChange={(e) => setPeriodicidad(e.target.value as Periodicidad)}>
            <option value="mensual">Mensual</option>
            <option value="bimestral">Bimestral</option>
          </select>
          <input
            type="date"
            aria-label="Activa desde"
            value={activaDesde}
            onChange={(e) => setActivaDesde(e.target.value)}
            required
          />
          <button type="submit" disabled={creating}>
            {creating ? 'Creando…' : 'Agregar cuota'}
          </button>
        </form>
      )}

      {loading ? (
        <p>Cargando…</p>
      ) : fees.length === 0 ? (
        <p>Todavía no hay ninguna cuota configurada.</p>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
              <th>Monto</th>
              <th>Periodicidad</th>
              <th>Activa desde</th>
              {isAdmin && <th />}
            </tr>
          </thead>
          <tbody>
            {fees.map((fee) =>
              editingId === fee.id ? (
                <tr key={fee.id} style={{ borderBottom: '1px solid var(--border)' }}>
                  <td colSpan={4}>
                    <form
                      onSubmit={(e) => handleSaveEdit(e, fee.id)}
                      style={{ display: 'flex', gap: 'var(--space-2)', alignItems: 'center', flexWrap: 'wrap' }}
                    >
                      <input
                        type="number"
                        step="0.01"
                        value={editMonto}
                        onChange={(e) => setEditMonto(e.target.value)}
                        required
                      />
                      <select value={editPeriodicidad} onChange={(e) => setEditPeriodicidad(e.target.value as Periodicidad)}>
                        <option value="mensual">Mensual</option>
                        <option value="bimestral">Bimestral</option>
                      </select>
                      <input
                        type="date"
                        aria-label="Activa desde"
                        value={editActivaDesde}
                        onChange={(e) => setEditActivaDesde(e.target.value)}
                        required
                      />
                      <button type="submit">Guardar</button>
                      <button type="button" onClick={() => setEditingId(null)}>
                        Cancelar
                      </button>
                    </form>
                  </td>
                </tr>
              ) : (
                <tr key={fee.id} style={{ borderBottom: '1px solid var(--border)' }}>
                  <td className="mono">${fee.monto.toFixed(2)}</td>
                  <td>{fee.periodicidad === 'mensual' ? 'Mensual' : 'Bimestral'}</td>
                  <td className="mono">{fee.activa_desde}</td>
                  {isAdmin && (
                    <td>
                      <button onClick={() => startEdit(fee)}>Editar</button>
                    </td>
                  )}
                </tr>
              ),
            )}
          </tbody>
        </table>
      )}
    </div>
  )
}
