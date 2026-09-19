import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AnnouncementsPage } from './AnnouncementsPage'
import * as announcementsApi from '../api/announcements'
import * as reglamentoApi from '../api/reglamento'
import { useAuth } from '../auth/AuthContext'
import type { Announcement, ReadStatusEntry, Reglamento } from '../types'

vi.mock('../auth/AuthContext', () => ({ useAuth: vi.fn() }))

const publicado: Announcement = {
  id: 'a1',
  titulo: 'Corte de agua programado',
  contenido: 'El día 20 se cortará el agua de 9am a 1pm por mantenimiento.',
  fecha_publicacion: '2020-01-01T10:00:00',
  permite_dudas: false,
  dudas_hasta: null,
  dudas_abiertas: false,
}

const programado: Announcement = {
  id: 'a2',
  titulo: 'Junta de vecinos',
  contenido: 'Convocatoria para la junta anual.',
  fecha_publicacion: '2099-01-01T10:00:00',
  permite_dudas: false,
  dudas_hasta: null,
  dudas_abiertas: false,
}

const reglamentoSinDudas: Reglamento = {
  dia_limite_pago: 5,
  dia_recargo: 6,
  recargo_porcentaje: 0.1,
  recargo_modalidad: 'unico',
  acepta_pago_efectivo: false,
  morosos_sin_voto: false,
  morosos_sin_areas_comunes: false,
  gasto_umbral_asamblea: null,
  cotizaciones_minimas: 3,
  cajones_visitas: 0,
  horas_max_estacionamiento_visitas: 24,
  dudas_en_avisos_por_defecto: false,
}

function mockUser(rol: string) {
  vi.mocked(useAuth).mockReturnValue({
    user: { sub: 'u1', tenant_id: 't1', schema: 's1', rol, property_id: null, exp: 0 },
    login: vi.fn(),
    logout: vi.fn(),
  })
}

describe('AnnouncementsPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(reglamentoApi, 'getReglamento').mockResolvedValue(reglamentoSinDudas)
  })

  it('lista avisos y distingue publicados de programados', async () => {
    mockUser('admin')
    vi.spyOn(announcementsApi, 'listAnnouncements').mockResolvedValue([publicado, programado])

    render(<AnnouncementsPage />)

    expect(await screen.findByText('Corte de agua programado')).toBeInTheDocument()
    expect(screen.getByText('Publicado')).toBeInTheDocument()
    expect(screen.getByText('Programado')).toBeInTheDocument()
  })

  it('un residente no ve el formulario de alta ni los botones de editar/ver lectura', async () => {
    mockUser('residente')
    vi.spyOn(announcementsApi, 'listAnnouncements').mockResolvedValue([publicado])

    render(<AnnouncementsPage />)

    await screen.findByText('Corte de agua programado')
    expect(screen.queryByPlaceholderText('Título')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /editar/i })).not.toBeInTheDocument()
  })

  it('la vista previa refleja lo que se está escribiendo', async () => {
    mockUser('admin')
    vi.spyOn(announcementsApi, 'listAnnouncements').mockResolvedValue([])
    const user = userEvent.setup()

    render(<AnnouncementsPage />)
    await screen.findByText(/todavía no hay avisos/i)

    await user.type(screen.getByPlaceholderText('Título'), 'Aviso de prueba')
    await user.type(screen.getByPlaceholderText('Contenido'), 'Contenido de prueba')

    const vistaPrevia = screen.getByText('Vista previa').closest('div')!
    expect(vistaPrevia).toHaveTextContent('Aviso de prueba')
    expect(vistaPrevia).toHaveTextContent('Contenido de prueba')
  })

  it('admin puede crear un aviso nuevo', async () => {
    mockUser('admin')
    vi.spyOn(announcementsApi, 'listAnnouncements').mockResolvedValue([])
    const createSpy = vi.spyOn(announcementsApi, 'createAnnouncement').mockResolvedValue(publicado)
    const user = userEvent.setup()

    render(<AnnouncementsPage />)
    await screen.findByText(/todavía no hay avisos/i)

    await user.type(screen.getByPlaceholderText('Título'), 'Corte de agua programado')
    await user.type(screen.getByPlaceholderText('Contenido'), 'El día 20 se cortará el agua.')
    await user.click(screen.getByRole('button', { name: /publicar aviso/i }))

    await waitFor(() =>
      expect(createSpy).toHaveBeenCalledWith({
        titulo: 'Corte de agua programado',
        contenido: 'El día 20 se cortará el agua.',
        fecha_publicacion: undefined,
        permite_dudas: false,
        dudas_hasta: undefined,
      }),
    )
  })

  it('admin puede editar un aviso existente', async () => {
    mockUser('admin')
    vi.spyOn(announcementsApi, 'listAnnouncements').mockResolvedValue([publicado])
    const updateSpy = vi.spyOn(announcementsApi, 'updateAnnouncement').mockResolvedValue(publicado)
    const user = userEvent.setup()

    render(<AnnouncementsPage />)
    await screen.findByText('Corte de agua programado')

    await user.click(screen.getByRole('button', { name: /editar/i }))
    expect(screen.getByRole('heading', { name: /editar aviso/i })).toBeInTheDocument()

    const tituloInput = screen.getByPlaceholderText('Título')
    await user.clear(tituloInput)
    await user.type(tituloInput, 'Título corregido')
    await user.click(screen.getByRole('button', { name: /guardar cambios/i }))

    await waitFor(() => expect(updateSpy).toHaveBeenCalled())
    const payload = updateSpy.mock.calls[0][1]
    expect(payload.titulo).toBe('Título corregido')
    expect(payload.contenido).toBe(publicado.contenido)
    // Se compara el INSTANTE, no el string exacto: fecha_publicacion se
    // recarga a datetime-local (hora local del runner) y se vuelve a
    // convertir a ISO-UTC al enviar — el round-trip debe conservar el
    // mismo instante que el aviso original, sin importar la zona horaria
    // del entorno donde corre esta prueba.
    expect(new Date(payload.fecha_publicacion!).getTime()).toBe(new Date(`${publicado.fecha_publicacion}Z`).getTime())
  })

  it('admin puede ver quién ha leído un aviso publicado', async () => {
    mockUser('admin')
    vi.spyOn(announcementsApi, 'listAnnouncements').mockResolvedValue([publicado])
    const lectura: ReadStatusEntry[] = [
      { property_id: 'p1', identificador: 'Casa 1', leido: true, leido_at: '2026-09-01T12:00:00' },
      { property_id: 'p2', identificador: 'Casa 2', leido: false, leido_at: null },
    ]
    vi.spyOn(announcementsApi, 'getReadStatus').mockResolvedValue(lectura)
    const user = userEvent.setup()

    render(<AnnouncementsPage />)
    await screen.findByText('Corte de agua programado')

    await user.click(screen.getByRole('button', { name: /ver lectura/i }))

    expect(await screen.findByText(/Casa 1/)).toBeInTheDocument()
    expect(screen.getByText(/Casa 2/)).toBeInTheDocument()
    expect(screen.getByText(/no leído/i)).toBeInTheDocument()
  })

  it('un aviso publicado hace un instante se clasifica como Publicado, no Programado', async () => {
    // Bug real encontrado en el navegador: fecha_publicacion llega del
    // backend como naive-UTC (sin sufijo de zona) — sin utcNaiveToDate(),
    // JS la interpreta como hora LOCAL del navegador, así que en cualquier
    // zona horaria detrás de UTC un aviso recién publicado (ahora mismo en
    // UTC) parece estar en el FUTURO respecto al reloj local, y se muestra
    // como "Programado". Se fuerza una zona detrás de UTC (México, UTC-6)
    // para que esta prueba distinga el comportamiento correcto del bug —
    // en el contenedor de Docker donde normalmente corre esta suite (UTC),
    // ambos casos coincidirían por casualidad.
    const TZ_ORIGINAL = process.env.TZ
    process.env.TZ = 'America/Mexico_City'
    try {
      mockUser('admin')
      const ahoraUtcNaive = new Date().toISOString().replace('Z', '')
      vi.spyOn(announcementsApi, 'listAnnouncements').mockResolvedValue([
        { id: 'a3', titulo: 'Recién publicado', contenido: '...', fecha_publicacion: ahoraUtcNaive, permite_dudas: false, dudas_hasta: null, dudas_abiertas: false },
      ])

      render(<AnnouncementsPage />)

      await screen.findByText('Recién publicado')
      expect(screen.getByText('Publicado')).toBeInTheDocument()
      expect(screen.queryByText('Programado')).not.toBeInTheDocument()
    } finally {
      process.env.TZ = TZ_ORIGINAL
    }
  })

  it('muestra el error del backend si falla la carga', async () => {
    mockUser('admin')
    vi.spyOn(announcementsApi, 'listAnnouncements').mockRejectedValue(new Error('caída'))

    render(<AnnouncementsPage />)

    expect(await screen.findByText(/no se pudieron cargar los avisos/i)).toBeInTheDocument()
  })

  it('un aviso nuevo permite dudas si el reglamento del condominio lo pide por defecto', async () => {
    mockUser('admin')
    vi.spyOn(announcementsApi, 'listAnnouncements').mockResolvedValue([])
    vi.spyOn(reglamentoApi, 'getReglamento').mockResolvedValue({ ...reglamentoSinDudas, dudas_en_avisos_por_defecto: true })
    const createSpy = vi.spyOn(announcementsApi, 'createAnnouncement').mockResolvedValue(publicado)
    const user = userEvent.setup({ delay: null })

    render(<AnnouncementsPage />)
    await screen.findByText(/todavía no hay avisos/i)
    await waitFor(() => expect(screen.getByLabelText(/permitir que los residentes manden dudas/i)).toBeChecked())
    await user.type(screen.getByPlaceholderText('Título'), 'Aviso')
    await user.type(screen.getByPlaceholderText('Contenido'), 'Texto')
    await user.click(screen.getByRole('button', { name: /publicar aviso/i }))

    await waitFor(() => expect(createSpy).toHaveBeenCalled())
    expect(createSpy.mock.calls[0][0]).toMatchObject({ permite_dudas: true })
  })

  it('el administrador activa las dudas al publicar y les pone fecha límite', async () => {
    mockUser('admin')
    vi.spyOn(announcementsApi, 'listAnnouncements').mockResolvedValue([])
    const createSpy = vi.spyOn(announcementsApi, 'createAnnouncement').mockResolvedValue(publicado)
    const user = userEvent.setup({ delay: null })

    render(<AnnouncementsPage />)
    await screen.findByText(/todavía no hay avisos/i)
    expect(screen.queryByLabelText('Recibir dudas hasta')).not.toBeInTheDocument() // el plazo solo aparece con dudas activadas
    await user.type(screen.getByPlaceholderText('Título'), 'Corte de agua')
    await user.type(screen.getByPlaceholderText('Contenido'), 'El jueves.')
    await user.click(screen.getByLabelText(/permitir que los residentes manden dudas/i))
    await user.type(screen.getByLabelText('Recibir dudas hasta'), '2026-09-30')
    await user.click(screen.getByRole('button', { name: /publicar aviso/i }))

    await waitFor(() => expect(createSpy).toHaveBeenCalled())
    expect(createSpy.mock.calls[0][0]).toMatchObject({ permite_dudas: true, dudas_hasta: '2026-09-30' })
  })

  it('al editar un aviso el formulario trae su configuración de dudas y un plazo vacío se manda como null', async () => {
    mockUser('admin')
    const conDudas: Announcement = { ...publicado, permite_dudas: true, dudas_hasta: '2026-09-30', dudas_abiertas: true }
    vi.spyOn(announcementsApi, 'listAnnouncements').mockResolvedValue([conDudas])
    const updateSpy = vi.spyOn(announcementsApi, 'updateAnnouncement').mockResolvedValue(conDudas)
    const user = userEvent.setup({ delay: null })

    render(<AnnouncementsPage />)
    await user.click(await screen.findByRole('button', { name: /editar/i }))
    expect(screen.getByLabelText(/permitir que los residentes manden dudas/i)).toBeChecked()
    expect(screen.getByLabelText('Recibir dudas hasta')).toHaveValue('2026-09-30')

    await user.clear(screen.getByLabelText('Recibir dudas hasta'))
    await user.click(screen.getByRole('button', { name: /guardar cambios/i }))

    await waitFor(() => expect(updateSpy).toHaveBeenCalled())
    expect(updateSpy.mock.calls[0][1]).toMatchObject({ permite_dudas: true, dudas_hasta: null })
  })

  it('la lista dice si cada aviso recibe dudas: abiertas hasta una fecha, cerradas o sin dudas', async () => {
    mockUser('admin')
    vi.spyOn(announcementsApi, 'listAnnouncements').mockResolvedValue([
      { ...publicado, id: 'a1', titulo: 'Con plazo', permite_dudas: true, dudas_hasta: '2099-12-31', dudas_abiertas: true },
      { ...publicado, id: 'a2', titulo: 'Vencido', permite_dudas: true, dudas_hasta: '2020-01-01', dudas_abiertas: false },
      { ...publicado, id: 'a3', titulo: 'Sin dudas' },
    ])

    render(<AnnouncementsPage />)

    expect((await screen.findByText('Con plazo')).closest('tr')).toHaveTextContent('Abiertas hasta 2099-12-31')
    expect(screen.getByText('Vencido').closest('tr')).toHaveTextContent('Cerradas')
    expect(screen.getByText('Sin dudas').closest('tr')).not.toHaveTextContent(/abiertas|cerradas/i)
  })
})
