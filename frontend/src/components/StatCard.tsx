import type { ReactNode } from 'react'

// Tarjeta de cifra del panel (mismo aspecto que las de Dashboard y Seguridad). Con onClick se vuelve un botón (ej.
// Dashboard: pinchar una tarjeta filtra el detalle de abajo) sin perder la apariencia de tarjeta; `active` la resalta
// mientras es el filtro vigente. `tint`: fondo de color suave a juego con `color` — antes toda tarjeta era blanca
// (solo la cifra tenía color), lo que se sentía plano; con `tint` el conjunto del Dashboard se ve más vivo de un
// vistazo, sin perder legibilidad (son los mismos tokens *-tint ya usados en los chips del resto del panel).
export function StatCard({
  label,
  children,
  color,
  tint,
  onClick,
  active,
}: {
  label: string
  children: ReactNode
  color?: string
  tint?: string
  onClick?: () => void
  active?: boolean
}) {
  const estilo = {
    background: tint ?? 'var(--surface)',
    border: `1px solid ${active ? 'var(--teal)' : tint ? 'transparent' : 'var(--border)'}`,
    borderRadius: 'var(--radius)',
    padding: 'var(--space-3)',
    flex: 1,
    minWidth: 140,
  }
  const contenido = (
    <>
      <div style={{ color: 'var(--ink-soft)' }}>{label}</div>
      <div className="mono" style={{ color, fontSize: '1.5rem' }}>
        {children}
      </div>
    </>
  )
  if (!onClick) return <div style={estilo}>{contenido}</div>
  return (
    <button
      type="button"
      onClick={onClick}
      style={{ ...estilo, textAlign: 'left', cursor: 'pointer', font: 'inherit' }}
    >
      {contenido}
    </button>
  )
}
