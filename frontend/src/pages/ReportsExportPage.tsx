import { useEffect, useState } from 'react'
import { exportAccountStatements, exportBudgetReport, exportExpenses } from '../api/reportsExport'
import { listProperties } from '../api/properties'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import type { Property } from '../types'
import { rolesDe } from '../permisos'

const ROLES_CON_ACCESO = new Set<string>(rolesDe('/reports/export'))

export function ReportsExportPage() {
  const { user } = useAuth()
  const tieneAcceso = user !== null && ROLES_CON_ACCESO.has(user.rol)

  const [properties, setProperties] = useState<Property[]>([])
  const [error, setError] = useState<string | null>(null)

  const [propertyId, setPropertyId] = useState('')
  const [descargandoEstados, setDescargandoEstados] = useState(false)

  const [desde, setDesde] = useState('')
  const [hasta, setHasta] = useState('')
  const [descargandoGastos, setDescargandoGastos] = useState(false)

  const [mes, setMes] = useState('')
  const [descargandoPresupuesto, setDescargandoPresupuesto] = useState(false)

  useEffect(() => {
    if (tieneAcceso) {
      listProperties()
        .then(setProperties)
        .catch(() => {
          /* el selector de vivienda es opcional; si falla, se exporta "todas" sin filtro */
        })
    }
  }, [tieneAcceso])

  async function handleExportAccountStatements() {
    setDescargandoEstados(true)
    setError(null)
    try {
      await exportAccountStatements(propertyId || undefined)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo exportar el reporte.')
    } finally {
      setDescargandoEstados(false)
    }
  }

  async function handleExportExpenses() {
    setDescargandoGastos(true)
    setError(null)
    try {
      await exportExpenses(desde || undefined, hasta || undefined)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo exportar el reporte.')
    } finally {
      setDescargandoGastos(false)
    }
  }

  async function handleExportBudget() {
    setDescargandoPresupuesto(true)
    setError(null)
    try {
      await exportBudgetReport(mes ? `${mes}-01` : undefined)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo exportar el reporte.')
    } finally {
      setDescargandoPresupuesto(false)
    }
  }

  if (!tieneAcceso) {
    return (
      <div>
        <h2>Exportar reportes</h2>
        <p>No tienes acceso a esta vista — solo administradores y tesorero.</p>
      </div>
    )
  }

  return (
    <div>
      <h2>Exportar reportes</h2>
      {error && <p style={{ color: 'var(--brick)' }}>{error}</p>}

      <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: 'var(--space-3)', marginBottom: 'var(--space-3)' }}>
        <h3>Estados de cuenta</h3>
        <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
          <select value={propertyId} onChange={(e) => setPropertyId(e.target.value)}>
            <option value="">Todas las viviendas</option>
            {properties.map((p) => (
              <option key={p.id} value={p.id}>
                {p.identificador}
              </option>
            ))}
          </select>
          <button onClick={handleExportAccountStatements} disabled={descargandoEstados}>
            {descargandoEstados ? 'Generando…' : 'Exportar a Excel'}
          </button>
        </div>
      </div>

      <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: 'var(--space-3)', marginBottom: 'var(--space-3)' }}>
        <h3>Gastos</h3>
        <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
          <input type="date" aria-label="Desde" value={desde} onChange={(e) => setDesde(e.target.value)} />
          <input type="date" aria-label="Hasta" value={hasta} onChange={(e) => setHasta(e.target.value)} />
          <button onClick={handleExportExpenses} disabled={descargandoGastos}>
            {descargandoGastos ? 'Generando…' : 'Exportar a Excel'}
          </button>
        </div>
      </div>

      <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: 'var(--space-3)' }}>
        <h3>Presupuesto vs. real</h3>
        <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
          <input type="month" aria-label="Periodo" value={mes} onChange={(e) => setMes(e.target.value)} />
          <button onClick={handleExportBudget} disabled={descargandoPresupuesto}>
            {descargandoPresupuesto ? 'Generando…' : 'Exportar a Excel'}
          </button>
        </div>
      </div>
    </div>
  )
}
