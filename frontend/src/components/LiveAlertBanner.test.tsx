import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { LiveAlertBanner } from './LiveAlertBanner'
import type { LiveAlert } from '../services/liveAlerts'

describe('LiveAlertBanner', () => {
  it('no muestra nada sin alertas', () => {
    const { container } = render(<LiveAlertBanner alertas={[]} onDescartar={() => {}} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('muestra el texto correcto para cada tipo de evento', () => {
    const alertas: LiveAlert[] = [
      { id: '1', mensaje: { evento: 'incidencia_creada', incident_id: 'i1', descripcion: 'Fuga de agua', tipo: 'mantenimiento' } },
      { id: '2', mensaje: { evento: 'incidencia_actualizada', incident_id: 'i1', estado: 'resuelta' } },
      { id: '3', mensaje: { evento: 'incidencia_comentada', incident_id: 'i1', comentario: 'Ya se revisó' } },
      { id: '4', mensaje: { evento: 'sync_conflicto', recurso: 'package', client_id: 'c1', motivo: 'ya existe con otros datos' } },
    ]

    render(<LiveAlertBanner alertas={alertas} onDescartar={() => {}} />)

    expect(screen.getByText('Nueva incidencia (mantenimiento): Fuga de agua')).toBeInTheDocument()
    expect(screen.getByText('Una incidencia cambió de estado: ahora está "resuelta"')).toBeInTheDocument()
    expect(screen.getByText('Nuevo comentario en una incidencia: Ya se revisó')).toBeInTheDocument()
    expect(screen.getByText('Conflicto de sincronización (package): ya existe con otros datos')).toBeInTheDocument()
  })

  it('descartar llama a onDescartar con el id de esa alerta', async () => {
    const onDescartar = vi.fn()
    const alertas: LiveAlert[] = [
      { id: 'abc', mensaje: { evento: 'sync_conflicto', recurso: 'incident', client_id: 'c1', motivo: 'motivo x' } },
    ]
    const user = userEvent.setup()

    render(<LiveAlertBanner alertas={alertas} onDescartar={onDescartar} />)
    await user.click(screen.getByRole('button', { name: /descartar/i }))

    expect(onDescartar).toHaveBeenCalledWith('abc')
  })
})
