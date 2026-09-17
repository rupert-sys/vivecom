import { render, screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { SecurityDashboardPage } from './SecurityDashboardPage'
import * as incidentsApi from '../api/incidents'
import * as accessLogApi from '../api/accessLog'
import * as propertiesApi from '../api/properties'
import { useAuth } from '../auth/AuthContext'
import type { AccessLogEntry, Incident, Property } from '../types'

vi.mock('../auth/AuthContext', () => ({ useAuth: vi.fn() }))

const incidentes: Incident[] = [
  { id: 'i1', reportado_por: 'u1', estado: 'abierta', descripcion: 'Fuga de agua', created_at: '2026-09-01T10:00:00', resolved_at: null },
  { id: 'i2', reportado_por: 'u1', estado: 'en_proceso', descripcion: 'Portón dañado', created_at: '2026-09-02T10:00:00', resolved_at: null },
  {
    id: 'i3',
    reportado_por: 'u1',
    estado: 'resuelta',
    descripcion: 'Elevador atorado',
    created_at: '2026-09-01T10:00:00',
    resolved_at: '2026-09-01T12:00:00', // 2 horas después
  },
]

const propiedades: Property[] = [{ id: 'p1', identificador: 'Casa 1', referencia_pago: '0000001', saldo_a_favor: 0 }]

const accesos: AccessLogEntry[] = [
  { id: 'a1', property_id: 'p1', tipo: 'visitante', hora_entrada: '2026-09-01T09:00:00', hora_salida: '2026-09-01T10:00:00', placas: [] },
  { id: 'a2', property_id: null, tipo: 'proveedor', hora_entrada: '2026-09-01T11:00:00', hora_salida: null, placas: [] },
]

function mockUser(rol: string | null) {
  vi.mocked(useAuth).mockReturnValue({
    user: rol ? { sub: 'u1', tenant_id: 't1', schema: 's1', rol, property_id: null, exp: 0 } : null,
    login: vi.fn(),
    logout: vi.fn(),
  })
}

describe('SecurityDashboardPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('admin ve incidencias y accesos, con los conteos y el tiempo promedio de resolución correctos', async () => {
    mockUser('admin')
    vi.spyOn(incidentsApi, 'listIncidents').mockResolvedValue(incidentes)
    vi.spyOn(accessLogApi, 'listAccessLogs').mockResolvedValue(accesos)
    vi.spyOn(propertiesApi, 'listProperties').mockResolvedValue(propiedades)

    render(<SecurityDashboardPage />)

    expect(await screen.findByText('Fuga de agua')).toBeInTheDocument()
    expect(screen.getByText('Portón dañado')).toBeInTheDocument()
    // "Elevador atorado" ya está resuelta, no debe listarse entre las abiertas/en proceso.
    expect(screen.queryByText('Elevador atorado')).not.toBeInTheDocument()
    expect(screen.getByText('2.0h')).toBeInTheDocument()

    const tablaAccesos = within(screen.getAllByRole('table')[1])
    expect(tablaAccesos.getByText('Casa 1')).toBeInTheDocument()
    expect(tablaAccesos.getByText('General')).toBeInTheDocument()
  })

  it('comite_lectura ve incidencias pero no accesos', async () => {
    mockUser('comite_lectura')
    vi.spyOn(incidentsApi, 'listIncidents').mockResolvedValue(incidentes)
    const accessLogSpy = vi.spyOn(accessLogApi, 'listAccessLogs')

    render(<SecurityDashboardPage />)

    await screen.findByText('Fuga de agua')
    expect(screen.queryByText('Accesos')).not.toBeInTheDocument()
    expect(accessLogSpy).not.toHaveBeenCalled()
  })

  it('un rol sin acceso a ninguna sección ve un mensaje', () => {
    mockUser('residente')

    render(<SecurityDashboardPage />)

    expect(screen.getByText(/no tienes acceso a esta vista/i)).toBeInTheDocument()
  })

  it('muestra "Sin datos aún" cuando no hay incidencias resueltas todavía', async () => {
    mockUser('admin')
    vi.spyOn(incidentsApi, 'listIncidents').mockResolvedValue([incidentes[0], incidentes[1]])
    vi.spyOn(accessLogApi, 'listAccessLogs').mockResolvedValue([])
    vi.spyOn(propertiesApi, 'listProperties').mockResolvedValue([])

    render(<SecurityDashboardPage />)

    expect(await screen.findByText('Sin datos aún')).toBeInTheDocument()
  })

  it('muestra el error del backend si falla la carga', async () => {
    mockUser('admin')
    vi.spyOn(incidentsApi, 'listIncidents').mockRejectedValue(new Error('caída'))
    vi.spyOn(accessLogApi, 'listAccessLogs').mockResolvedValue([])
    vi.spyOn(propertiesApi, 'listProperties').mockResolvedValue([])

    render(<SecurityDashboardPage />)

    expect(await screen.findByText(/no se pudo cargar el dashboard de seguridad/i)).toBeInTheDocument()
  })
})
