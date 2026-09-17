import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AmenitiesPollsPage } from './AmenitiesPollsPage'
import * as amenitiesApi from '../api/amenities'
import * as pollsApi from '../api/polls'
import * as usersApi from '../api/users'
import { useAuth } from '../auth/AuthContext'
import type { Amenity, Poll, UserAccount } from '../types'

vi.mock('../auth/AuthContext', () => ({ useAuth: vi.fn() }))

const amenidad: Amenity = { id: 'am1', nombre: 'Salón de eventos', periodo_limite_horas: 24 }
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

    await waitFor(() => expect(createSpy).toHaveBeenCalledWith('Salón de eventos', 24))
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
})
