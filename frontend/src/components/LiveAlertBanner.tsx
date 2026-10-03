import type { LiveAlert, LiveAlertEvento } from '../services/liveAlerts'

interface Props {
  alertas: LiveAlert[]
  onDescartar: (id: string) => void
}

function textoDe(mensaje: LiveAlertEvento): string {
  switch (mensaje.evento) {
    case 'incidencia_creada':
      return `Nueva incidencia (${mensaje.tipo}): ${mensaje.descripcion}`
    case 'incidencia_actualizada':
      return `Una incidencia cambió de estado: ahora está "${mensaje.estado}"`
    case 'incidencia_comentada':
      return `Nuevo comentario en una incidencia: ${mensaje.comentario}`
    case 'sync_conflicto':
      return `Conflicto de sincronización (${mensaje.recurso}): ${mensaje.motivo}`
  }
}

// Avisos en vivo (F2-06/F2-13): incidencias nuevas/actualizadas/comentadas y conflictos de sincronización
// de la app caseta, por WebSocket (ver services/liveAlerts.ts). Fijo arriba de toda la pantalla porque el
// admin puede estar en cualquier sección del panel cuando llega la alerta.
export function LiveAlertBanner({ alertas, onDescartar }: Props) {
  if (alertas.length === 0) return null

  return (
    <div
      aria-live="polite"
      style={{
        position: 'fixed', top: 0, left: 0, right: 0, zIndex: 1000,
        display: 'flex', flexDirection: 'column', gap: 4, padding: 'var(--space-2)',
      }}
    >
      {alertas.map((alerta) => (
        <div
          key={alerta.id}
          role="alert"
          style={{
            background: 'var(--ink-2)', color: '#fff', padding: '10px 16px', borderRadius: 'var(--radius-sm)',
            display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 'var(--space-3)',
            boxShadow: '0 2px 8px rgba(0,0,0,0.25)',
          }}
        >
          <span>{textoDe(alerta.mensaje)}</span>
          <button
            type="button"
            onClick={() => onDescartar(alerta.id)}
            aria-label="Descartar"
            style={{ background: 'transparent', border: 'none', color: '#fff', cursor: 'pointer', fontSize: '1rem' }}
          >
            ✕
          </button>
        </div>
      ))}
    </div>
  )
}
