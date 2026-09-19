import type { ReactNode } from 'react'

// Tarjeta de cifra del panel (mismo aspecto que las de Dashboard y Seguridad).
export function StatCard({ label, children, color }: { label: string; children: ReactNode; color?: string }) {
  return (
    <div
      style={{
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius)',
        padding: 'var(--space-3)',
        flex: 1,
        minWidth: 140,
      }}
    >
      <div style={{ color: 'var(--ink-soft)' }}>{label}</div>
      <div className="mono" style={{ color, fontSize: '1.5rem' }}>
        {children}
      </div>
    </div>
  )
}
