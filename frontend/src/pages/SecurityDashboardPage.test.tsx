import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { SecurityDashboardPage } from './SecurityDashboardPage'
import * as incidentsApi from '../api/incidents'
import * as accessLogApi from '../api/accessLog'
import * as propertiesApi from '../api/properties'
import { useAuth } from '../auth/AuthContext'
import type { AccessLogEntry, Incident, Property, VisitorParking } from '../types'

vi.mock('../auth/AuthContext', () => ({ useAuth: vi.fn() }))

const incidentes: Incident[] = [
  { id: 'i1', reportado_por: 'u1', estado: 'abierta', descripcion: 'Fuga de agua', created_at: '2026-09-01T10:00:00', resolved_at: null, foto_url: null, tipo: 'seguridad', property_id: null, persona_involucrada: null },
  { id: 'i2', reportado_por: 'u1', estado: 'en_proceso', descripcion: 'Portón dañado', created_at: '2026-09-02T10:00:00', resolved_at: null, foto_url: null, tipo: 'mantenimiento', property_id: 'p1', persona_involucrada: 'Vecino' },
  {
    id: 'i3',
    reportado_por: 'u1',
    estado: 'resuelta',
    descripcion: 'Elevador atorado',
    created_at: '2026-09-01T10:00:00',
    resolved_at: '2026-09-01T12:00:00', // 2 horas después
    foto_url: null,
    tipo: 'seguridad',
    property_id: null,
    persona_involucrada: null,
  },
]

const propiedades: Property[] = [{ id: 'p1', identificador: 'Casa 1', referencia_pago: '0000001', saldo_a_favor: 0, residente_principal: null, residente_principal_rol: null, total_residentes: 0 }]

const accesos: AccessLogEntry[] = [
  { id: 'a1', property_id: 'p1', tipo: 'visitante', hora_entrada: '2026-09-01T09:00:00', hora_salida: '2026-09-01T10:00:00', placas: [], nombre_visitante: 'Ana López', acompanantes: 2, identificacion: 'INE', autorizado_por: 'telefono' },
  { id: 'a2', property_id: null, tipo: 'proveedor', hora_entrada: '2026-09-01T11:00:00', hora_salida: null, placas: [], nombre_visitante: null, acompanantes: 0, identificacion: null, autorizado_por: null },
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
    vi.spyOn(accessLogApi, 'getVisitorParking').mockResolvedValue({
      total_cajones: 7,
      ocupados: 3,
      libres: 4,
      horas_maximas: 24,
      excedidos: [],
    })
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

  it('la tabla de incidencias dice el tipo, la casa y la persona involucrada', async () => {
    mockUser('admin')
    vi.spyOn(incidentsApi, 'listIncidents').mockResolvedValue(incidentes)
    vi.spyOn(accessLogApi, 'listAccessLogs').mockResolvedValue([])
    vi.spyOn(propertiesApi, 'listProperties').mockResolvedValue(propiedades)

    render(<SecurityDashboardPage />)

    const fila = (await screen.findByText('Portón dañado')).closest('tr')!
    expect(within(fila).getByText('Mantenimiento')).toBeInTheDocument()
    expect(within(fila).getByText('Casa 1')).toBeInTheDocument()
    expect(within(fila).getByText('Vecino')).toBeInTheDocument()
  })

  it('filtrar por mantenimiento deja solo las fallas de mantenimiento', async () => {
    mockUser('admin')
    vi.spyOn(incidentsApi, 'listIncidents').mockResolvedValue(incidentes)
    vi.spyOn(accessLogApi, 'listAccessLogs').mockResolvedValue([])
    vi.spyOn(propertiesApi, 'listProperties').mockResolvedValue(propiedades)
    const user = userEvent.setup()

    render(<SecurityDashboardPage />)
    await screen.findByText('Fuga de agua')
    await user.selectOptions(screen.getByLabelText('Tipo de incidencia'), 'mantenimiento')

    expect(screen.getByText('Portón dañado')).toBeInTheDocument()
    expect(screen.queryByText('Fuga de agua')).not.toBeInTheDocument()
  })

  it('la bitácora de accesos muestra el nombre, los acompañantes y quién autorizó', async () => {
    mockUser('guardia')
    vi.spyOn(accessLogApi, 'listAccessLogs').mockResolvedValue(accesos)
    vi.spyOn(incidentsApi, 'listIncidents').mockResolvedValue([])
    vi.spyOn(propertiesApi, 'listProperties').mockResolvedValue(propiedades)

    render(<SecurityDashboardPage />)

    const fila = (await screen.findByText(/Ana López/)).closest('tr')!
    expect(within(fila).getByText(/\+2 acompañantes/)).toBeInTheDocument()
    expect(within(fila).getByText('Llamada al residente')).toBeInTheDocument()
  })

  it('muestra los cajones de visitas libres y cuántos vehículos rebasaron el plazo', async () => {
    mockUser('admin')
    vi.spyOn(incidentsApi, 'listIncidents').mockResolvedValue([])
    vi.spyOn(accessLogApi, 'listAccessLogs').mockResolvedValue(accesos)
    vi.spyOn(propertiesApi, 'listProperties').mockResolvedValue(propiedades)
    const excedidos: VisitorParking = { total_cajones: 7, ocupados: 7, libres: 0, horas_maximas: 24, excedidos: ['a1'] }
    vi.spyOn(accessLogApi, 'getVisitorParking').mockResolvedValue(excedidos)

    render(<SecurityDashboardPage />)

    expect(await screen.findByText('0 libres de 7')).toHaveStyle({ color: 'var(--brick)' })
    expect(screen.getByText(/1 vehículo rebasó las 24 h permitidas/)).toBeInTheDocument()
  })

  it('sin cajones de visitas configurados no muestra la tarjeta, y si falla el resto sigue', async () => {
    mockUser('admin')
    vi.spyOn(incidentsApi, 'listIncidents').mockResolvedValue([])
    vi.spyOn(accessLogApi, 'listAccessLogs').mockResolvedValue(accesos)
    vi.spyOn(propertiesApi, 'listProperties').mockResolvedValue(propiedades)
    vi.spyOn(accessLogApi, 'getVisitorParking').mockRejectedValue(new Error('caída'))

    render(<SecurityDashboardPage />)

    expect(await screen.findByText(/Ana López/)).toBeInTheDocument()
    expect(screen.queryByText(/cajones de visitas/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/no se pudo cargar/i)).not.toBeInTheDocument()
  })

  it('una incidencia con foto ofrece el enlace para verla y una sin foto no', async () => {
    mockUser('admin')
    vi.spyOn(incidentsApi, 'listIncidents').mockResolvedValue([
      { ...incidentes[0], foto_url: 'http://localhost:8000/files/f1/content?t=abc' },
      incidentes[1],
    ])
    vi.spyOn(accessLogApi, 'listAccessLogs').mockResolvedValue([])
    vi.spyOn(propertiesApi, 'listProperties').mockResolvedValue(propiedades)

    render(<SecurityDashboardPage />)

    const conFoto = (await screen.findByText('Fuga de agua')).closest('tr')!
    expect(within(conFoto).getByRole('link', { name: /ver foto/i })).toHaveAttribute(
      'href',
      'http://localhost:8000/files/f1/content?t=abc',
    )
    const sinFoto = screen.getByText('Portón dañado').closest('tr')!
    expect(within(sinFoto).queryByRole('link', { name: /ver foto/i })).not.toBeInTheDocument()
  })
})
