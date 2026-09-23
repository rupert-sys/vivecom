import type { ReactNode } from 'react'

// Tarjeta de cifra del panel (mismo aspecto que las de Dashboard y Seguridad). Con onClick se vuelve un botón (ej.
// Dashboard: pinchar una tarjeta filtra el detalle de abajo) sin perder la apariencia de tarjeta; `active` la resalta
// mientras es el filtro vigente.
export function StatCard({
  label,
  children,
  color,
  onClick,
  active,
}: {
  label: string
  children: ReactNode
  color?: string
  onClick?: () => void
  active?: boolean
}) {
  const estilo = {
    background: 'var(--surface)',
    border: `1px solid ${active ? 'var(--teal)' : 'var(--border)'}`,
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
