import { useState, type FormEvent } from 'react'
import type { AmenityRulesInput } from '../api/amenities'
import type { Amenity } from '../types'

const DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

// La hora llega como "01:00:00"; <input type="time"> solo entiende "01:00".
function aHoraCorta(hora: string | null | undefined): string {
  return hora ? hora.slice(0, 5) : ''
}

interface Props {
  // Con `inicial` el formulario edita esa amenidad; sin ella, crea una nueva.
  inicial?: Amenity
  submitLabel: string
  busy: boolean
  onSubmit: (nombre: string, periodoLimiteHoras: number, reglas: AmenityRulesInput) => void
  onCancel?: () => void
}

// Alta y edición de una amenidad con las reglas que salen del reglamento del condominio:
// anticipación mínima, horario, días permitidos, capacidad (ej. cajones), cuota y notas.
export function AmenityForm({ inicial, submitLabel, busy, onSubmit, onCancel }: Props) {
  const [nombre, setNombre] = useState(inicial?.nombre ?? '')
  const [periodoLimite, setPeriodoLimite] = useState(inicial ? String(inicial.periodo_limite_horas) : '')
  const [anticipacion, setAnticipacion] = useState(String(inicial?.dias_anticipacion_minimos ?? 0))
  const [horaInicio, setHoraInicio] = useState(aHoraCorta(inicial?.hora_inicio_permitida))
  const [horaFin, setHoraFin] = useState(aHoraCorta(inicial?.hora_fin_maxima))
  const [dias, setDias] = useState<number[]>(inicial?.dias_semana_permitidos ?? [0, 1, 2, 3, 4, 5, 6])
  const [capacidad, setCapacidad] = useState(String(inicial?.capacidad ?? 1))
  const [cuota, setCuota] = useState(String(inicial?.cuota ?? 0))
  const [duracionMax, setDuracionMax] = useState(inicial?.max_duracion_horas ? String(inicial.max_duracion_horas) : '')
  const [notas, setNotas] = useState(inicial?.notas_reglamento ?? '')

  function alternarDia(dia: number) {
    setDias(dias.includes(dia) ? dias.filter((d) => d !== dia) : [...dias, dia].sort())
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    onSubmit(nombre, Number(periodoLimite), {
      dias_anticipacion_minimos: Number(anticipacion),
      hora_inicio_permitida: horaInicio || null,
      hora_fin_maxima: horaFin || null,
      // Todos los días (o ninguno marcado) = sin restricción de días.
      dias_semana_permitidos: dias.length === 0 || dias.length === 7 ? null : dias,
      capacidad: Number(capacidad),
      cuota: Number(cuota),
      max_duracion_horas: duracionMax === '' ? null : Number(duracionMax),
      notas_reglamento: notas.trim() === '' ? null : notas.trim(),
    })
  }

  const campo = { display: 'flex', flexDirection: 'column', gap: 4 } as const

  return (
    <form
      onSubmit={handleSubmit}
      style={{ display: 'grid', gap: 'var(--space-2)', maxWidth: 480, margin: 'var(--space-3) 0' }}
    >
      <input placeholder="Nombre de la amenidad" value={nombre} onChange={(e) => setNombre(e.target.value)} required />
      <input
        type="number"
        placeholder="Periodo límite de respuesta (horas)"
        value={periodoLimite}
        onChange={(e) => setPeriodoLimite(e.target.value)}
        required
      />

      <fieldset style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius)', display: 'grid', gap: 'var(--space-2)' }}>
        <legend>Reglas de uso (reglamento)</legend>
        <label style={campo}>
          Días de anticipación mínimos para solicitarla
          <input type="number" min={0} max={365} value={anticipacion} onChange={(e) => setAnticipacion(e.target.value)} />
        </label>
        <label style={campo}>
          Puede empezar a partir de
          <input type="time" value={horaInicio} onChange={(e) => setHoraInicio(e.target.value)} />
        </label>
        <label style={campo}>
          Hora máxima de uso (puede ser de madrugada, ej. 01:00)
          <input type="time" value={horaFin} onChange={(e) => setHoraFin(e.target.value)} />
        </label>
        <div>
          <div>Días en que se puede usar</div>
          <div style={{ display: 'flex', gap: 'var(--space-2)', flexWrap: 'wrap' }}>
            {DIAS.map((nombreDia, indice) => (
              <label key={nombreDia} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <input type="checkbox" checked={dias.includes(indice)} onChange={() => alternarDia(indice)} />
                {nombreDia}
              </label>
            ))}
          </div>
        </div>
        <label style={campo}>
          Capacidad (reservaciones al mismo tiempo, ej. cajones)
          <input type="number" min={1} max={500} value={capacidad} onChange={(e) => setCapacidad(e.target.value)} />
        </label>
        <label style={campo}>
          Cuota de uso (MXN, 0 = gratis)
          <input type="number" min={0} step="0.01" value={cuota} onChange={(e) => setCuota(e.target.value)} />
        </label>
        <label style={campo}>
          Duración máxima (horas, vacío = sin límite)
          <input type="number" min={1} value={duracionMax} onChange={(e) => setDuracionMax(e.target.value)} />
        </label>
        <label style={campo}>
          Nota para el residente (ej. artículo del reglamento)
          <input value={notas} onChange={(e) => setNotas(e.target.value)} />
        </label>
      </fieldset>

      <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
        <button type="submit" disabled={busy}>
          {busy ? 'Guardando…' : submitLabel}
        </button>
        {onCancel && (
          <button type="button" onClick={onCancel}>
            Cancelar
          </button>
        )}
      </div>
    </form>
  )
}
