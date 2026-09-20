import { useEffect, useState, type FormEvent } from 'react'
import { getReglamento, updateReglamento } from '../api/reglamento'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import type { RecargoModalidad } from '../types'

// Reglamento interior del condominio: reglas que el sistema hace cumplir (recargo por mora,
// pago en efectivo, restricciones a morosos, gastos que requieren asamblea, cajones de visitas).
// Cualquier rol las puede consultar; solo el administrador las cambia.
export function ReglamentoPage() {
  const { user } = useAuth()
  const isAdmin = user?.rol === 'admin'

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [guardado, setGuardado] = useState(false)
  const [saving, setSaving] = useState(false)

  const [diaLimite, setDiaLimite] = useState('')
  const [recargoPct, setRecargoPct] = useState('')
  const [modalidad, setModalidad] = useState<RecargoModalidad>('unico')
  const [efectivo, setEfectivo] = useState(false)
  const [sinVoto, setSinVoto] = useState(false)
  const [sinAreas, setSinAreas] = useState(false)
  const [umbral, setUmbral] = useState('')
  const [cotizaciones, setCotizaciones] = useState('')
  const [cajones, setCajones] = useState('')
  const [horasVisitas, setHorasVisitas] = useState('')
  const [dudasPorDefecto, setDudasPorDefecto] = useState(false)
  const [prorrogaMeses, setProrrogaMeses] = useState('')

  useEffect(() => {
    getReglamento()
      .then((r) => {
        setDiaLimite(String(r.dia_limite_pago))
        // 0.07 * 100 = 7.000000000000001: se redondea para no mostrar basura de coma flotante.
        setRecargoPct(String(Number((r.recargo_porcentaje * 100).toFixed(2))))
        setModalidad(r.recargo_modalidad)
        setEfectivo(r.acepta_pago_efectivo)
        setSinVoto(r.morosos_sin_voto)
        setSinAreas(r.morosos_sin_areas_comunes)
        setUmbral(r.gasto_umbral_asamblea === null ? '' : String(r.gasto_umbral_asamblea))
        setCotizaciones(String(r.cotizaciones_minimas))
        setCajones(String(r.cajones_visitas))
        setHorasVisitas(String(r.horas_max_estacionamiento_visitas))
        setDudasPorDefecto(r.dudas_en_avisos_por_defecto)
        setProrrogaMeses(String(r.prorroga_max_meses))
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : 'No se pudo cargar el reglamento.'))
      .finally(() => setLoading(false))
  }, [])

  async function handleSave(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    setGuardado(false)
    try {
      await updateReglamento({
        dia_limite_pago: Number(diaLimite),
        recargo_porcentaje: Number(recargoPct) / 100,
        recargo_modalidad: modalidad,
        acepta_pago_efectivo: efectivo,
        morosos_sin_voto: sinVoto,
        morosos_sin_areas_comunes: sinAreas,
        gasto_umbral_asamblea: umbral.trim() === '' ? null : Number(umbral),
        cotizaciones_minimas: Number(cotizaciones),
        cajones_visitas: Number(cajones),
        horas_max_estacionamiento_visitas: Number(horasVisitas),
        dudas_en_avisos_por_defecto: dudasPorDefecto,
        prorroga_max_meses: Number(prorrogaMeses),
      })
      setError(null)
      setGuardado(true)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo guardar el reglamento.')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <p>Cargando…</p>

  const campo = { display: 'flex', flexDirection: 'column', gap: 4, maxWidth: 360 } as const
  const casilla = { display: 'flex', alignItems: 'center', gap: 'var(--space-2)' } as const

  return (
    <div>
      <h2>Reglamento del condominio</h2>
      <p style={{ color: 'var(--ink-soft)' }}>
        Reglas de tu reglamento interior que el sistema hace cumplir. Lo que no configures aquí se comporta con los
        valores por defecto de la plataforma.
        {!isAdmin && ' Solo el administrador puede cambiarlas.'}
      </p>
      {error && <p style={{ color: 'var(--brick)' }}>{error}</p>}
      {guardado && <p style={{ color: 'var(--teal)' }}>Reglamento guardado.</p>}

      <form onSubmit={handleSave}>
        <fieldset disabled={!isAdmin || saving} style={{ border: 'none', padding: 0, display: 'grid', gap: 'var(--space-3)' }}>
          <h3>Cuotas y recargo por mora</h3>
          <label style={campo}>
            Día límite de pago del mes
            <input type="number" min={1} max={27} value={diaLimite} onChange={(e) => setDiaLimite(e.target.value)} required />
            <small style={{ color: 'var(--ink-soft)' }}>El recargo corre a partir del día siguiente.</small>
          </label>
          <label style={campo}>
            Recargo (%)
            <input
              type="number"
              min={0}
              max={100}
              step="0.01"
              value={recargoPct}
              onChange={(e) => setRecargoPct(e.target.value)}
              required
            />
          </label>
          <label style={campo}>
            Modalidad del recargo
            <select value={modalidad} onChange={(e) => setModalidad(e.target.value as RecargoModalidad)}>
              <option value="unico">Por única vez</option>
              <option value="mensual_sobre_saldo">Mensual sobre el saldo vencido</option>
            </select>
          </label>
          <label style={casilla}>
            <input type="checkbox" checked={efectivo} onChange={(e) => setEfectivo(e.target.checked)} />
            Se acepta pago en efectivo (lo registra el tesorero y entrega recibo)
          </label>

          <h3>Viviendas con adeudo</h3>
          <label style={casilla}>
            <input type="checkbox" checked={sinVoto} onChange={(e) => setSinVoto(e.target.checked)} />
            Conservan voz pero no voto en las votaciones
          </label>
          <label style={casilla}>
            <input type="checkbox" checked={sinAreas} onChange={(e) => setSinAreas(e.target.checked)} />
            No pueden reservar áreas comunes
          </label>

          <h3>Gastos</h3>
          <label style={campo}>
            Monto desde el cual un gasto programado o extraordinario requiere asamblea
            <input
              type="number"
              min={0}
              step="0.01"
              placeholder="Sin umbral"
              value={umbral}
              onChange={(e) => setUmbral(e.target.value)}
            />
          </label>
          <label style={campo}>
            Cotizaciones mínimas de proveedores distintos
            <input type="number" min={0} max={10} value={cotizaciones} onChange={(e) => setCotizaciones(e.target.value)} required />
          </label>

          <h3>Avisos</h3>
          <label style={casilla}>
            <input type="checkbox" checked={dudasPorDefecto} onChange={(e) => setDudasPorDefecto(e.target.checked)} />
            Los avisos nuevos reciben dudas de los residentes (el administrador puede cambiarlo al publicar cada aviso)
          </label>

          <h3>Acuerdos de pago (prórroga de cuotas)</h3>
          <label style={campo}>
            Plazo máximo para liquidar un acuerdo (meses)
            <input type="number" min={1} max={12} value={prorrogaMeses} onChange={(e) => setProrrogaMeses(e.target.value)} required />
            <small style={{ color: 'var(--ink-soft)' }}>Se cuenta desde que el vecino lo solicita.</small>
          </label>

          <h3>Estacionamiento de visitas</h3>
          <label style={campo}>
            Cajones de visitas
            <input type="number" min={0} value={cajones} onChange={(e) => setCajones(e.target.value)} required />
          </label>
          <label style={campo}>
            Horas máximas de estancia
            <input type="number" min={1} value={horasVisitas} onChange={(e) => setHorasVisitas(e.target.value)} required />
          </label>
        </fieldset>

        {isAdmin && (
          <button type="submit" disabled={saving} style={{ marginTop: 'var(--space-3)' }}>
            {saving ? 'Guardando…' : 'Guardar reglamento'}
          </button>
        )}
      </form>
    </div>
  )
}
