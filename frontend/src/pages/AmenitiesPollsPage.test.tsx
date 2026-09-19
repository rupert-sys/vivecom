import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AmenitiesPollsPage } from './AmenitiesPollsPage'
import * as amenitiesApi from '../api/amenities'
import * as pollsApi from '../api/polls'
import * as usersApi from '../api/users'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import type { Amenity, Poll, UserAccount } from '../types'

vi.mock('../auth/AuthContext', () => ({ useAuth: vi.fn() }))

const amenidad: Amenity = {
  id: 'am1',
  nombre: 'Salón de eventos',
  periodo_limite_horas: 24,
  dias_anticipacion_minimos: 0,
  hora_inicio_permitida: null,
  hora_fin_maxima: null,
  dias_semana_permitidos: null,
  capacidad: 1,
  cuota: 0,
  max_duracion_horas: null,
  notas_reglamento: null,
  reglas: [],
}
// El área adoquinada de Arequipa (reglamento Art. 2): 8 días de anticipación, hasta la 01:00, cuota de $1,000.
const adoquinada: Amenity = {
  ...amenidad,
  id: 'am2',
  nombre: 'Área adoquinada',
  dias_anticipacion_minimos: 8,
  hora_fin_maxima: '01:00:00',
  cuota: 1000,
  notas_reglamento: 'Reglamento Art. 2',
  reglas: ['Solicítala con al menos 8 días de anticipación.', 'Horario máximo de uso: hasta las 01:00.'],
}
const votacion: Poll = {
  id: 'p1',
  pregunta: '¿Aprobamos el nuevo reglamento?',
  fecha_cierre: '2026-10-01',
  resultados_en_vivo: false,
  quorum_alcanzado: false,
  reactivada: false,
  opciones: [
    { id: 'o1', texto: 'Sí' },
    { id: 'o2', texto: 'No' },
  ],
}
const aprobador: UserAccount = { id: 'u1', email: 'aprobador@condo.mx', rol: 'comite_aprobador' }

function mockUser(rol: string) {
  vi.mocked(useAuth).mockReturnValue({
    user: { sub: 'u1', tenant_id: 't1', schema: 's1', rol, property_id: null, exp: 0 },
    login: vi.fn(),
    logout: vi.fn(),
  })
}

describe('AmenitiesPollsPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('lista amenidades y votaciones existentes', async () => {
    mockUser('residente')
    vi.spyOn(amenitiesApi, 'listAmenities').mockResolvedValue([amenidad])
    vi.spyOn(pollsApi, 'listPolls').mockResolvedValue([votacion])

    render(<AmenitiesPollsPage />)

    expect(await screen.findByText(/Salón de eventos/)).toBeInTheDocument()
    expect(screen.getByText('¿Aprobamos el nuevo reglamento?')).toBeInTheDocument()
  })

  it('un residente no ve los formularios de alta ni la sección de personal', async () => {
    mockUser('residente')
    vi.spyOn(amenitiesApi, 'listAmenities').mockResolvedValue([])
    vi.spyOn(pollsApi, 'listPolls').mockResolvedValue([])

    render(<AmenitiesPollsPage />)

    await screen.findByText(/todavía no hay amenidades/i)
    expect(screen.queryByPlaceholderText('Nombre de la amenidad')).not.toBeInTheDocument()
    expect(screen.queryByText('Cuentas de personal')).not.toBeInTheDocument()
    expect(screen.queryByPlaceholderText('Pregunta')).not.toBeInTheDocument()
  })

  it('un vocero (no admin) puede crear una votación pero no ve la sección de personal', async () => {
    mockUser('vocero')
    vi.spyOn(amenitiesApi, 'listAmenities').mockResolvedValue([])
    vi.spyOn(pollsApi, 'listPolls').mockResolvedValue([])
    const createSpy = vi.spyOn(pollsApi, 'createPoll').mockResolvedValue(votacion)
    const user = userEvent.setup()

    render(<AmenitiesPollsPage />)
    await screen.findByText(/todavía no hay votaciones/i)

    expect(screen.queryByText('Cuentas de personal')).not.toBeInTheDocument()

    await user.type(screen.getByPlaceholderText('Pregunta'), '¿Aprobamos el nuevo reglamento?')
    await user.type(screen.getByPlaceholderText(/opciones separadas por coma/i), 'Sí, No')
    await user.type(screen.getByLabelText('Fecha de cierre'), '2026-10-01')
    await user.click(screen.getByRole('button', { name: /crear votación/i }))

    await waitFor(() =>
      expect(createSpy).toHaveBeenCalledWith({
        pregunta: '¿Aprobamos el nuevo reglamento?',
        opciones: ['Sí', 'No'],
        fecha_cierre: '2026-10-01',
        resultados_en_vivo: false,
      }),
    )
  })

  it('admin puede crear una amenidad', async () => {
    mockUser('admin')
    vi.spyOn(amenitiesApi, 'listAmenities').mockResolvedValue([])
    vi.spyOn(pollsApi, 'listPolls').mockResolvedValue([])
    vi.spyOn(usersApi, 'listUsers').mockResolvedValue([])
    const createSpy = vi.spyOn(amenitiesApi, 'createAmenity').mockResolvedValue(amenidad)
    const user = userEvent.setup()

    render(<AmenitiesPollsPage />)
    await screen.findByText(/todavía no hay amenidades/i)

    await user.type(screen.getByPlaceholderText('Nombre de la amenidad'), 'Salón de eventos')
    await user.type(screen.getByPlaceholderText(/periodo límite/i), '24')
    await user.click(screen.getByRole('button', { name: /agregar amenidad/i }))

    await waitFor(() =>
      expect(createSpy).toHaveBeenCalledWith('Salón de eventos', 24, {
        dias_anticipacion_minimos: 0,
        hora_inicio_permitida: null,
        hora_fin_maxima: null,
        dias_semana_permitidos: null, // todos los días marcados = sin restricción
        capacidad: 1,
        cuota: 0,
        max_duracion_horas: null,
        notas_reglamento: null,
      }),
    )
  })

  it('admin puede crear una cuenta de personal', async () => {
    mockUser('admin')
    vi.spyOn(amenitiesApi, 'listAmenities').mockResolvedValue([])
    vi.spyOn(pollsApi, 'listPolls').mockResolvedValue([])
    vi.spyOn(usersApi, 'listUsers').mockResolvedValue([])
    const createSpy = vi.spyOn(usersApi, 'createUser').mockResolvedValue(aprobador)
    const user = userEvent.setup()

    render(<AmenitiesPollsPage />)
    await screen.findByText(/todavía no hay cuentas de personal/i)

    await user.type(screen.getByPlaceholderText('Email'), 'aprobador@condo.mx')
    await user.type(screen.getByPlaceholderText('Contraseña temporal'), 'clave-temporal-123')
    await user.click(screen.getByRole('button', { name: /crear cuenta/i }))

    await waitFor(() =>
      expect(createSpy).toHaveBeenCalledWith({
        email: 'aprobador@condo.mx',
        password: 'clave-temporal-123',
        rol: 'comite_aprobador',
      }),
    )
  })

  it('admin puede designar un aprobador para una amenidad', async () => {
    mockUser('admin')
    vi.spyOn(amenitiesApi, 'listAmenities').mockResolvedValue([amenidad])
    vi.spyOn(pollsApi, 'listPolls').mockResolvedValue([])
    vi.spyOn(usersApi, 'listUsers').mockResolvedValue([aprobador])
    vi.spyOn(amenitiesApi, 'listAmenityApprovers').mockResolvedValue([])
    const assignSpy = vi.spyOn(amenitiesApi, 'addAmenityApprover').mockResolvedValue(undefined)
    const user = userEvent.setup()

    render(<AmenitiesPollsPage />)
    // El email es solo parte del texto del <li> (el rol va en un <span>
    // aparte), así que ningún elemento tiene ese string exacto como su
    // textContent completo — un regex hace match por substring en cambio.
    await screen.findByText(/aprobador@condo\.mx/)

    await user.selectOptions(screen.getByText('Elige una amenidad…').closest('select')!, 'am1')
    await screen.findByText(/todavía no tiene aprobadores/i)

    await user.selectOptions(screen.getByText(/elige un usuario con rol comité aprobador/i).closest('select')!, 'u1')
    await user.click(screen.getByRole('button', { name: /designar aprobador/i }))

    await waitFor(() => expect(assignSpy).toHaveBeenCalledWith('am1', 'u1'))
  })

  it('muestra el error del backend si falla la carga', async () => {
    mockUser('admin')
    vi.spyOn(amenitiesApi, 'listAmenities').mockRejectedValue(new Error('caída'))
    vi.spyOn(pollsApi, 'listPolls').mockResolvedValue([])

    render(<AmenitiesPollsPage />)

    expect(await screen.findByText(/no se pudo cargar amenidades y votaciones/i)).toBeInTheDocument()
  })

  it('lista las reglas de cada amenidad en lenguaje llano', async () => {
    mockUser('tesorero')
    vi.spyOn(amenitiesApi, 'listAmenities').mockResolvedValue([adoquinada])
    vi.spyOn(pollsApi, 'listPolls').mockResolvedValue([])

    render(<AmenitiesPollsPage />)

    expect(await screen.findByText('Solicítala con al menos 8 días de anticipación.')).toBeInTheDocument()
    expect(screen.getByText('Horario máximo de uso: hasta las 01:00.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /editar reglas/i })).not.toBeInTheDocument()
  })

  it('un admin crea el área adoquinada con las reglas del reglamento', async () => {
    mockUser('admin')
    vi.spyOn(amenitiesApi, 'listAmenities').mockResolvedValue([])
    vi.spyOn(pollsApi, 'listPolls').mockResolvedValue([])
    vi.spyOn(usersApi, 'listUsers').mockResolvedValue([])
    const createSpy = vi.spyOn(amenitiesApi, 'createAmenity').mockResolvedValue(adoquinada)
    const user = userEvent.setup()

    render(<AmenitiesPollsPage />)
    await screen.findByText(/todavía no hay amenidades/i)
    await user.type(screen.getByPlaceholderText('Nombre de la amenidad'), 'Área adoquinada')
    await user.type(screen.getByPlaceholderText(/periodo límite/i), '48')
    await user.clear(screen.getByLabelText(/días de anticipación mínimos/i))
    await user.type(screen.getByLabelText(/días de anticipación mínimos/i), '8')
    await user.type(screen.getByLabelText(/hora máxima de uso/i), '01:00')
    await user.clear(screen.getByLabelText(/cuota de uso/i))
    await user.type(screen.getByLabelText(/cuota de uso/i), '1000')
    await user.type(screen.getByLabelText(/nota para el residente/i), 'Reglamento Art. 2')
    await user.click(screen.getByRole('button', { name: /agregar amenidad/i }))

    await waitFor(() => expect(createSpy).toHaveBeenCalledTimes(1))
    expect(createSpy).toHaveBeenCalledWith('Área adoquinada', 48, {
      dias_anticipacion_minimos: 8,
      hora_inicio_permitida: null,
      hora_fin_maxima: '01:00',
      dias_semana_permitidos: null,
      capacidad: 1,
      cuota: 1000,
      max_duracion_horas: null,
      notas_reglamento: 'Reglamento Art. 2',
    })
  })

  it('desmarcar días manda solo los permitidos (de lunes a viernes)', async () => {
    mockUser('admin')
    vi.spyOn(amenitiesApi, 'listAmenities').mockResolvedValue([])
    vi.spyOn(pollsApi, 'listPolls').mockResolvedValue([])
    vi.spyOn(usersApi, 'listUsers').mockResolvedValue([])
    const createSpy = vi.spyOn(amenitiesApi, 'createAmenity').mockResolvedValue(amenidad)
    const user = userEvent.setup()

    render(<AmenitiesPollsPage />)
    await screen.findByText(/todavía no hay amenidades/i)
    await user.type(screen.getByPlaceholderText('Nombre de la amenidad'), 'Cajones')
    await user.type(screen.getByPlaceholderText(/periodo límite/i), '24')
    await user.click(screen.getByLabelText('Sábado'))
    await user.click(screen.getByLabelText('Domingo'))
    await user.clear(screen.getByLabelText(/capacidad/i))
    await user.type(screen.getByLabelText(/capacidad/i), '7')
    await user.click(screen.getByRole('button', { name: /agregar amenidad/i }))

    await waitFor(() => expect(createSpy).toHaveBeenCalled())
    expect(createSpy.mock.calls[0][2]).toMatchObject({ dias_semana_permitidos: [0, 1, 2, 3, 4], capacidad: 7 })
  })

  it('un admin edita las reglas de una amenidad existente y el formulario llega con sus valores', async () => {
    mockUser('admin')
    vi.spyOn(amenitiesApi, 'listAmenities').mockResolvedValue([adoquinada])
    vi.spyOn(pollsApi, 'listPolls').mockResolvedValue([])
    vi.spyOn(usersApi, 'listUsers').mockResolvedValue([])
    const updateSpy = vi.spyOn(amenitiesApi, 'updateAmenity').mockResolvedValue(adoquinada)
    const user = userEvent.setup()

    render(<AmenitiesPollsPage />)
    await user.click(await screen.findByRole('button', { name: /editar reglas/i }))
    // Con la edición abierta hay dos formularios (alta y edición): se trabaja dentro del de edición.
    const formulario = within(screen.getByRole('button', { name: /guardar reglas/i }).closest('form')!)

    expect(formulario.getByLabelText(/días de anticipación mínimos/i)).toHaveValue(8)
    expect(formulario.getByLabelText(/hora máxima de uso/i)).toHaveValue('01:00')
    expect(formulario.getByLabelText(/cuota de uso/i)).toHaveValue(1000)

    await user.clear(formulario.getByLabelText(/cuota de uso/i))
    await user.type(formulario.getByLabelText(/cuota de uso/i), '1200')
    await user.click(formulario.getByRole('button', { name: /guardar reglas/i }))

    await waitFor(() => expect(updateSpy).toHaveBeenCalledTimes(1))
    expect(updateSpy).toHaveBeenCalledWith(
      'am2',
      expect.objectContaining({ nombre: 'Área adoquinada', periodo_limite_horas: 24, dias_anticipacion_minimos: 8, cuota: 1200 }),
    )
  })

  it('muestra el error del backend si no se puede guardar la amenidad', async () => {
    mockUser('admin')
    vi.spyOn(amenitiesApi, 'listAmenities').mockResolvedValue([adoquinada])
    vi.spyOn(pollsApi, 'listPolls').mockResolvedValue([])
    vi.spyOn(usersApi, 'listUsers').mockResolvedValue([])
    vi.spyOn(amenitiesApi, 'updateAmenity').mockRejectedValue(new ApiError(422, 'Los días van de 0 (lunes) a 6 (domingo)'))
    const user = userEvent.setup()

    render(<AmenitiesPollsPage />)
    await user.click(await screen.findByRole('button', { name: /editar reglas/i }))
    await user.click(screen.getByRole('button', { name: /guardar reglas/i }))

    expect(await screen.findByText(/los días van de 0/i)).toBeInTheDocument()
  })
})
