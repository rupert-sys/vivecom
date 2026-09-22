import { useEffect, useState, type FormEvent } from 'react'
import { createExpense, getFinancialSummary, listExpenses } from '../api/expenses'
import { createBudget, getBudgetReport } from '../api/budgets'
import { getReglamento } from '../api/reglamento'
import { TIPOS_DE_ARCHIVO_ACEPTADOS, uploadFile } from '../api/files'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { StatCard } from '../components/StatCard'
import type {
  BudgetComparison,
  Expense,
  FinancialSummary,
  PeriodicidadPresupuesto,
  RecurrenciaGasto,
  Reglamento,
  TipoComprobante,
  TipoGasto,
} from '../types'

const ETIQUETA_TIPO: Record<TipoGasto, string> = {
  operativo: 'Operativo',
  programado: 'Programado',
  extraordinario: 'Extraordinario',
}

const ETIQUETA_RECURRENCIA: Record<RecurrenciaGasto, string> = {
  unica: 'Una vez',
  semanal: 'Semanal',
  mensual: 'Mensual',
}

// Categorías sugeridas (el gasto acepta cualquier texto vía "Otra…"): las más comunes en la administración de un
// condominio mexicano, para que la mayoría de los gastos no requieran capturar el nombre a mano cada vez.
const CATEGORIAS_SUGERIDAS = [
  'Mantenimiento',
  'Vigilancia',
  'Jardinería',
  'Recolección de basura',
  'Limpieza de áreas comunes',
  'Administración',
  'Agua, luz y gas (áreas comunes)',
  'Elevadores y equipos',
  'Seguros',
  'Proyectos y obra',
]
const OTRA_CATEGORIA = '__otra__'

interface CotizacionForm {
  proveedor: string
  monto: string
  archivo: File | null
}

function money(valor: number): string {
  return `$${valor.toFixed(2)}`
}

export function ExpensesBudgetPage() {
  const { user } = useAuth()
  const isAdmin = user?.rol === 'admin'

  const [expenses, setExpenses] = useState<Expense[]>([])
  const [reporte, setReporte] = useState<BudgetComparison[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [categoriaSeleccionada, setCategoriaSeleccionada] = useState<string>(CATEGORIAS_SUGERIDAS[0])
  const [categoriaOtra, setCategoriaOtra] = useState('')
  const categoria = categoriaSeleccionada === OTRA_CATEGORIA ? categoriaOtra.trim() : categoriaSeleccionada
  const [monto, setMonto] = useState('')
  const [fecha, setFecha] = useState('')
  const [comprobanteUrl, setComprobanteUrl] = useState('')
  const [comprobanteArchivo, setComprobanteArchivo] = useState<File | null>(null)
  const [creandoGasto, setCreandoGasto] = useState(false)
  const [tipo, setTipo] = useState<TipoGasto>('operativo')
  const [recurrencia, setRecurrencia] = useState<RecurrenciaGasto>('unica')
  const [tipoComprobante, setTipoComprobante] = useState<TipoComprobante | ''>('')
  const [aprobadoAsamblea, setAprobadoAsamblea] = useState(false)
  const [acta, setActa] = useState('')
  const [cotizaciones, setCotizaciones] = useState<CotizacionForm[]>([{ proveedor: '', monto: '', archivo: null }])

  const [resumen, setResumen] = useState<FinancialSummary | null>(null)
  const [reglamento, setReglamento] = useState<Reglamento | null>(null)
  const [desde, setDesde] = useState('')
  const [hasta, setHasta] = useState('')

  const [presupuestoCategoria, setPresupuestoCategoria] = useState('')
  const [presupuestoPeriodicidad, setPresupuestoPeriodicidad] = useState<PeriodicidadPresupuesto>('mensual')
  const [presupuestoPeriodo, setPresupuestoPeriodo] = useState('')
  const [presupuestoMonto, setPresupuestoMonto] = useState('')
  const [creandoPresupuesto, setCreandoPresupuesto] = useState(false)

  async function reload() {
    setLoading(true)
    try {
      const [expensesResult, reporteResult] = await Promise.all([listExpenses(), getBudgetReport()])
      setExpenses(expensesResult)
      setReporte(reporteResult)
      setError(null)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo cargar gastos y presupuesto.')
    } finally {
      setLoading(false)
    }
  }

  // El resumen es un complemento: si falla, gastos y presupuesto siguen usables.
  async function reloadResumen() {
    try {
      setResumen(await getFinancialSummary(desde || undefined, hasta || undefined))
    } catch {
      setResumen(null)
    }
  }

  useEffect(() => {
    reload()
    getReglamento()
      .then(setReglamento)
      .catch(() => setReglamento(null))
  }, [])

  useEffect(() => {
    reloadResumen()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [desde, hasta])

  const requiereSustento = tipo !== 'operativo'
  const umbral = reglamento?.gasto_umbral_asamblea ?? null

  async function handleCreateExpense(event: FormEvent) {
    event.preventDefault()
    if (!comprobanteArchivo && comprobanteUrl.trim() === '') {
      setError('Adjunta el comprobante del gasto (foto o PDF), o pega su enlace.')
      return
    }
    if (categoria === '') {
      setError('Escribe el nombre de la categoría.')
      return
    }
    setCreandoGasto(true)
    try {
      // Los archivos se suben primero; el gasto solo lleva sus identificadores.
      const comprobanteSubido = comprobanteArchivo ? await uploadFile(comprobanteArchivo, 'gasto') : null
      const cotizacionesValidas = await Promise.all(
        cotizaciones
          .filter((c) => c.proveedor.trim() !== '' && c.monto !== '')
          .map(async (c) => ({
            proveedor: c.proveedor.trim(),
            monto: Number(c.monto),
            ...(c.archivo ? { archivo_id: (await uploadFile(c.archivo, 'gasto')).id } : {}),
          })),
      )
      await createExpense({
        categoria,
        monto: Number(monto),
        fecha,
        ...(comprobanteSubido ? { comprobante_archivo_id: comprobanteSubido.id } : { comprobante_url: comprobanteUrl.trim() }),
        tipo,
        recurrencia,
        ...(tipoComprobante ? { tipo_comprobante: tipoComprobante } : {}),
        ...(requiereSustento
          ? {
              aprobado_en_asamblea: aprobadoAsamblea,
              ...(acta.trim() ? { acta_referencia: acta.trim() } : {}),
              ...(cotizacionesValidas.length > 0 ? { cotizaciones: cotizacionesValidas } : {}),
            }
          : {}),
      })
      setCategoriaSeleccionada(CATEGORIAS_SUGERIDAS[0])
      setCategoriaOtra('')
      setMonto('')
      setFecha('')
      setComprobanteUrl('')
      setComprobanteArchivo(null)
      setTipo('operativo')
      setRecurrencia('unica')
      setTipoComprobante('')
      setAprobadoAsamblea(false)
      setActa('')
      setCotizaciones([{ proveedor: '', monto: '', archivo: null }])
      setError(null)
      await reload()
      await reloadResumen()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo registrar el gasto.')
    } finally {
      setCreandoGasto(false)
    }
  }

  async function handleCreateBudget(event: FormEvent) {
    event.preventDefault()
    setCreandoPresupuesto(true)
    try {
      await createBudget({
        categoria: presupuestoCategoria,
        periodicidad: presupuestoPeriodicidad,
        periodo: presupuestoPeriodo,
        monto_planeado: Number(presupuestoMonto),
      })
      setPresupuestoCategoria('')
      setPresupuestoPeriodo('')
      setPresupuestoMonto('')
      await reload()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo registrar el presupuesto.')
    } finally {
      setCreandoPresupuesto(false)
    }
  }

  return (
    <div>
      <h2>Gastos y presupuesto</h2>
      {error && <p style={{ color: 'var(--brick)' }}>{error}</p>}

      <h3>Resumen financiero</h3>
      <div style={{ display: 'flex', gap: 'var(--space-2)', margin: 'var(--space-2) 0', alignItems: 'center' }}>
        <input type="date" aria-label="Resumen desde" value={desde} onChange={(e) => setDesde(e.target.value)} />
        <input type="date" aria-label="Resumen hasta" value={hasta} onChange={(e) => setHasta(e.target.value)} />
        {(desde || hasta) && (
          <button
            onClick={() => {
              setDesde('')
              setHasta('')
            }}
          >
            Todo el historial
          </button>
        )}
      </div>
      {resumen && (
        <>
          <div style={{ display: 'flex', gap: 'var(--space-3)', marginBottom: 'var(--space-3)', flexWrap: 'wrap' }}>
            <StatCard label="Ingresos (cuotas cobradas)" color="var(--teal)">
              {money(resumen.ingresos)}
            </StatCard>
            <StatCard label="Gastos" color="var(--amber)">
              {money(resumen.gastos)}
            </StatCard>
            <StatCard label={resumen.saldo >= 0 ? 'Saldo a favor' : 'Saldo en contra'} color={resumen.saldo >= 0 ? 'var(--teal)' : 'var(--brick)'}>
              {money(Math.abs(resumen.saldo))}
            </StatCard>
            <StatCard label="Cuotas por cobrar">{money(resumen.por_cobrar)}</StatCard>
          </div>
          <div style={{ display: 'flex', gap: 'var(--space-4)', flexWrap: 'wrap', marginBottom: 'var(--space-4)' }}>
            {resumen.gastos_por_categoria.length > 0 && (
              <table style={{ borderCollapse: 'collapse', flex: 1, minWidth: 280 }}>
                <thead>
                  <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
                    <th>Gasto por categoría</th>
                    <th>Movimientos</th>
                    <th>Total</th>
                  </tr>
                </thead>
                <tbody>
                  {resumen.gastos_por_categoria.map((c) => (
                    <tr key={c.concepto} style={{ borderBottom: '1px solid var(--border)' }}>
                      <td>{c.concepto}</td>
                      <td className="mono">{c.cantidad}</td>
                      <td className="mono">{money(c.total)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            {resumen.gastos_por_mes.length > 0 && (
              <table style={{ borderCollapse: 'collapse', flex: 1, minWidth: 280 }}>
                <thead>
                  <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
                    <th>Gasto por mes</th>
                    <th>Movimientos</th>
                    <th>Total</th>
                  </tr>
                </thead>
                <tbody>
                  {resumen.gastos_por_mes.map((m) => (
                    <tr key={m.concepto} style={{ borderBottom: '1px solid var(--border)' }}>
                      <td>{m.concepto}</td>
                      <td className="mono">{m.cantidad}</td>
                      <td className="mono">{money(m.total)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}

      <h3>Gastos</h3>
      {isAdmin && (
        <form onSubmit={handleCreateExpense} style={{ display: 'flex', gap: 'var(--space-2)', flexWrap: 'wrap', margin: 'var(--space-3) 0' }}>
          <select
            aria-label="Categoría del gasto"
            value={categoriaSeleccionada}
            onChange={(e) => setCategoriaSeleccionada(e.target.value)}
          >
            {CATEGORIAS_SUGERIDAS.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
            <option value={OTRA_CATEGORIA}>Otra…</option>
          </select>
          {categoriaSeleccionada === OTRA_CATEGORIA && (
            <input
              placeholder="Nombre de la categoría"
              aria-label="Nombre de la categoría"
              value={categoriaOtra}
              onChange={(e) => setCategoriaOtra(e.target.value)}
              required
            />
          )}
          <select aria-label="Recurrencia" value={recurrencia} onChange={(e) => setRecurrencia(e.target.value as RecurrenciaGasto)}>
            <option value="unica">Una vez</option>
            <option value="semanal">Semanal</option>
            <option value="mensual">Mensual</option>
          </select>
          <input type="number" step="0.01" placeholder="Monto" value={monto} onChange={(e) => setMonto(e.target.value)} required />
          <input type="date" aria-label="Fecha del gasto" value={fecha} onChange={(e) => setFecha(e.target.value)} required />
          <label style={{ display: 'flex', flexDirection: 'column', gap: 4, flexBasis: '100%' }}>
            Comprobante (foto o PDF, hasta 10 MB)
            <input
              type="file"
              accept={TIPOS_DE_ARCHIVO_ACEPTADOS}
              onChange={(e) => setComprobanteArchivo(e.target.files?.[0] ?? null)}
            />
          </label>
          <input
            placeholder="URL del comprobante"
            aria-label="O pega el enlace del comprobante"
            value={comprobanteUrl}
            onChange={(e) => setComprobanteUrl(e.target.value)}
          />
          <select aria-label="Tipo de gasto" value={tipo} onChange={(e) => setTipo(e.target.value as TipoGasto)}>
            {(Object.keys(ETIQUETA_TIPO) as TipoGasto[]).map((t) => (
              <option key={t} value={t}>
                {ETIQUETA_TIPO[t]}
              </option>
            ))}
          </select>
          <select
            aria-label="Tipo de comprobante"
            value={tipoComprobante}
            onChange={(e) => setTipoComprobante(e.target.value as TipoComprobante | '')}
          >
            <option value="">Comprobante: sin especificar</option>
            <option value="factura">Factura</option>
            <option value="remision">Remisión</option>
          </select>

          {requiereSustento && (
            <fieldset style={{ flexBasis: '100%', border: '1px solid var(--border)', borderRadius: 'var(--radius)' }}>
              <legend>Sustento del gasto</legend>
              {umbral !== null && (
                <p style={{ color: 'var(--ink-soft)' }}>
                  Un gasto {tipo} mayor a <span className="mono">{money(umbral)}</span> requiere aprobación de la
                  asamblea y al menos {reglamento?.cotizaciones_minimas ?? 3} cotizaciones de proveedores distintos
                  (reglamento).
                </p>
              )}
              <label style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                <input type="checkbox" checked={aprobadoAsamblea} onChange={(e) => setAprobadoAsamblea(e.target.checked)} />
                Aprobado en asamblea
              </label>
              <input
                placeholder="Acta o referencia de la asamblea"
                value={acta}
                onChange={(e) => setActa(e.target.value)}
                style={{ margin: 'var(--space-2) 0' }}
              />
              {cotizaciones.map((c, indice) => (
                <div key={indice} style={{ display: 'flex', gap: 'var(--space-2)', marginBottom: 'var(--space-2)' }}>
                  <input
                    placeholder={`Proveedor de la cotización ${indice + 1}`}
                    value={c.proveedor}
                    onChange={(e) =>
                      setCotizaciones(cotizaciones.map((x, i) => (i === indice ? { ...x, proveedor: e.target.value } : x)))
                    }
                  />
                  <input
                    type="number"
                    step="0.01"
                    placeholder="Monto cotizado"
                    aria-label={`Monto de la cotización ${indice + 1}`}
                    value={c.monto}
                    onChange={(e) =>
                      setCotizaciones(cotizaciones.map((x, i) => (i === indice ? { ...x, monto: e.target.value } : x)))
                    }
                  />
                  <input
                    type="file"
                    accept={TIPOS_DE_ARCHIVO_ACEPTADOS}
                    aria-label={`Archivo de la cotización ${indice + 1}`}
                    onChange={(e) =>
                      setCotizaciones(cotizaciones.map((x, i) => (i === indice ? { ...x, archivo: e.target.files?.[0] ?? null } : x)))
                    }
                  />
                  {cotizaciones.length > 1 && (
                    <button type="button" onClick={() => setCotizaciones(cotizaciones.filter((_, i) => i !== indice))}>
                      Quitar
                    </button>
                  )}
                </div>
              ))}
              <button type="button" onClick={() => setCotizaciones([...cotizaciones, { proveedor: '', monto: '', archivo: null }])}>
                Agregar cotización
              </button>
            </fieldset>
          )}

          <button type="submit" disabled={creandoGasto}>
            {creandoGasto ? 'Registrando…' : 'Registrar gasto'}
          </button>
        </form>
      )}

      {loading ? (
        <p>Cargando…</p>
      ) : expenses.length === 0 ? (
        <p>Todavía no hay gastos registrados.</p>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: 'var(--space-4)' }}>
          <thead>
            <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
              <th>Fecha</th>
              <th>Categoría</th>
              <th>Tipo</th>
              <th>Recurrencia</th>
              <th>Monto</th>
              <th>Comprobante</th>
              <th>Sustento</th>
            </tr>
          </thead>
          <tbody>
            {expenses.map((gasto) => (
              <tr key={gasto.id} style={{ borderBottom: '1px solid var(--border)' }}>
                <td className="mono">{gasto.fecha}</td>
                <td>{gasto.categoria}</td>
                <td>{ETIQUETA_TIPO[gasto.tipo] ?? gasto.tipo}</td>
                <td>
                  {gasto.recurrencia === 'unica' ? (
                    <span style={{ color: 'var(--ink-faint)' }}>—</span>
                  ) : (
                    <span className="chip chip-blue">{ETIQUETA_RECURRENCIA[gasto.recurrencia]}</span>
                  )}
                </td>
                <td className="mono">${gasto.monto.toFixed(2)}</td>
                <td>
                  <a href={gasto.comprobante_url} target="_blank" rel="noreferrer">
                    Ver
                  </a>
                  {gasto.tipo_comprobante && (
                    <span style={{ color: 'var(--ink-soft)' }}>
                      {' '}
                      ({gasto.tipo_comprobante === 'factura' ? 'factura' : 'remisión'})
                    </span>
                  )}
                </td>
                <td>
                  {[
                    gasto.aprobado_en_asamblea ? 'Asamblea' : null,
                    gasto.cotizaciones && gasto.cotizaciones.length > 0 ? `${gasto.cotizaciones.length} cotizaciones` : null,
                  ]
                    .filter(Boolean)
                    .join(' · ') || '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h3>Presupuesto vs. real</h3>
      {isAdmin && (
        <form onSubmit={handleCreateBudget} style={{ display: 'flex', gap: 'var(--space-2)', flexWrap: 'wrap', margin: 'var(--space-3) 0' }}>
          <input
            placeholder="Categoría del presupuesto"
            value={presupuestoCategoria}
            onChange={(e) => setPresupuestoCategoria(e.target.value)}
            required
          />
          <select value={presupuestoPeriodicidad} onChange={(e) => setPresupuestoPeriodicidad(e.target.value as PeriodicidadPresupuesto)}>
            <option value="mensual">Mensual</option>
            <option value="anual">Anual</option>
          </select>
          <input
            type="date"
            aria-label="Periodo del presupuesto"
            value={presupuestoPeriodo}
            onChange={(e) => setPresupuestoPeriodo(e.target.value)}
            required
          />
          <input
            type="number"
            step="0.01"
            placeholder="Monto planeado"
            value={presupuestoMonto}
            onChange={(e) => setPresupuestoMonto(e.target.value)}
            required
          />
          <button type="submit" disabled={creandoPresupuesto}>
            {creandoPresupuesto ? 'Registrando…' : 'Registrar presupuesto'}
          </button>
        </form>
      )}

      {reporte.length === 0 ? (
        <p>Todavía no hay presupuesto configurado para este periodo.</p>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
              <th>Categoría</th>
              <th>Periodicidad</th>
              <th>Planeado</th>
              <th>Real</th>
            </tr>
          </thead>
          <tbody>
            {reporte.map((fila) => (
              <tr key={fila.categoria} style={{ borderBottom: '1px solid var(--border)' }}>
                <td>{fila.categoria}</td>
                <td>{fila.periodicidad === 'mensual' ? 'Mensual' : 'Anual'}</td>
                <td className="mono">${fila.monto_planeado.toFixed(2)}</td>
                <td className="mono" style={{ color: fila.monto_real > fila.monto_planeado ? 'var(--brick)' : 'var(--teal)' }}>
                  ${fila.monto_real.toFixed(2)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
