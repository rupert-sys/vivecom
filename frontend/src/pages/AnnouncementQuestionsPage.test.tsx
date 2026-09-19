import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AnnouncementQuestionsPage } from './AnnouncementQuestionsPage'
import * as questionsApi from '../api/announcementQuestions'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import type { AnnouncementQuestion } from '../types'

vi.mock('../auth/AuthContext', () => ({ useAuth: vi.fn() }))

function duda(extra: Partial<AnnouncementQuestion> = {}): AnnouncementQuestion {
  return {
    id: 'q1',
    announcement_id: 'a1',
    aviso_titulo: 'Corte de agua',
    texto: '¿Habrá agua en la caseta?',
    estado: 'abierta',
    respuesta: null,
    respondido_en: null,
    publica: false,
    created_at: '2026-09-18T15:00:00',
    vivienda: 'Casa 4',
    ...extra,
  }
}

function mockUser(rol: string) {
  vi.mocked(useAuth).mockReturnValue({
    user: { sub: 'u1', tenant_id: 't1', schema: 's1', rol, property_id: null, exp: 0 },
    login: vi.fn(),
    logout: vi.fn(),
  })
}

function mockApis(pendientes: AnnouncementQuestion[], respondidas: AnnouncementQuestion[] = []) {
  const p = vi.spyOn(questionsApi, 'listPendingQuestions').mockResolvedValue(pendientes)
  vi.spyOn(questionsApi, 'listAnsweredQuestions').mockResolvedValue(respondidas)
  return p
}

describe('AnnouncementQuestionsPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('lista las dudas por responder con la vivienda, el aviso y la pregunta', async () => {
    mockUser('admin')
    mockApis([duda()])

    render(<AnnouncementQuestionsPage />)

    expect(await screen.findByText('¿Habrá agua en la caseta?')).toBeInTheDocument()
    expect(screen.getByText(/Casa 4 · Corte de agua/)).toBeInTheDocument()
    expect(screen.getByText('Por responder (1)')).toBeInTheDocument()
  })

  it('el administrador responde y puede publicar la duda como aclaración', async () => {
    mockUser('admin')
    const pendientes = mockApis([duda()])
    const responder = vi.spyOn(questionsApi, 'answerQuestion').mockResolvedValue(duda({ estado: 'respondida' }))
    const user = userEvent.setup({ delay: null })

    render(<AnnouncementQuestionsPage />)
    const boton = await screen.findByRole('button', { name: 'Responder' })
    expect(boton).toBeDisabled() // sin texto no se puede enviar

    await user.type(screen.getByPlaceholderText('Escribe la respuesta'), 'Sí, hay cisterna.')
    await user.click(screen.getByLabelText(/publicar como aclaración/i))
    await user.click(boton)

    await waitFor(() => expect(responder).toHaveBeenCalledWith('q1', 'Sí, hay cisterna.', true))
    await waitFor(() => expect(pendientes).toHaveBeenCalledTimes(2)) // se recarga la bandeja
  })

  it('por defecto la respuesta queda privada', async () => {
    mockUser('comite_aprobador')
    mockApis([duda()])
    const responder = vi.spyOn(questionsApi, 'answerQuestion').mockResolvedValue(duda({ estado: 'respondida' }))
    const user = userEvent.setup({ delay: null })

    render(<AnnouncementQuestionsPage />)
    await user.type(await screen.findByPlaceholderText('Escribe la respuesta'), 'Solo torres A y C.')
    await user.click(screen.getByRole('button', { name: 'Responder' }))

    await waitFor(() => expect(responder).toHaveBeenCalledWith('q1', 'Solo torres A y C.', false))
  })

  it('el comité de solo lectura ve las dudas pero no puede responder', async () => {
    mockUser('comite_lectura')
    mockApis([duda()], [duda({ id: 'q2', texto: 'Otra duda ya contestada', estado: 'respondida', respuesta: 'Sí.', publica: true })])

    render(<AnnouncementQuestionsPage />)

    expect(await screen.findByText('¿Habrá agua en la caseta?')).toBeInTheDocument()
    expect(screen.queryByPlaceholderText('Escribe la respuesta')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Responder' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /retirar aclaración/i })).not.toBeInTheDocument()
    expect(screen.getByText(/solo lectura/i)).toBeInTheDocument()
  })

  it('las respondidas muestran si están publicadas y se pueden publicar o retirar', async () => {
    mockUser('admin')
    mockApis([], [
      duda({ id: 'q2', texto: 'Duda con aclaración publicada', estado: 'respondida', respuesta: 'R1', publica: true }),
      duda({ id: 'q3', texto: 'Duda sin publicar', estado: 'respondida', respuesta: 'R2', publica: false }),
    ])
    const actualizar = vi.spyOn(questionsApi, 'updateQuestion').mockResolvedValue(duda())
    const user = userEvent.setup({ delay: null })

    render(<AnnouncementQuestionsPage />)
    const publica = (await screen.findByText('Duda con aclaración publicada')).closest('tr')!
    const privada = screen.getByText('Duda sin publicar').closest('tr')!
    expect(within(publica).getByText('Publicada')).toBeInTheDocument()
    expect(within(privada).getByText('Privada', { selector: 'span' })).toBeInTheDocument()

    await user.click(within(publica).getByRole('button', { name: /retirar aclaración/i }))
    await waitFor(() => expect(actualizar).toHaveBeenCalledWith('q2', { publica: false }))
    await user.click(within(privada).getByRole('button', { name: /publicar como aclaración/i }))
    await waitFor(() => expect(actualizar).toHaveBeenCalledWith('q3', { publica: true }))
  })

  it('sin dudas lo dice', async () => {
    mockUser('admin')
    mockApis([])

    render(<AnnouncementQuestionsPage />)

    expect(await screen.findByText('No hay dudas por responder.')).toBeInTheDocument()
    expect(screen.getByText('Todavía no hay dudas respondidas.')).toBeInTheDocument()
  })

  it('muestra el error del backend si no se puede responder', async () => {
    mockUser('admin')
    mockApis([duda()])
    vi.spyOn(questionsApi, 'answerQuestion').mockRejectedValue(new ApiError(409, 'Esta duda ya fue respondida'))
    const user = userEvent.setup({ delay: null })

    render(<AnnouncementQuestionsPage />)
    await user.type(await screen.findByPlaceholderText('Escribe la respuesta'), 'Hola')
    await user.click(screen.getByRole('button', { name: 'Responder' }))

    expect(await screen.findByText('Esta duda ya fue respondida')).toBeInTheDocument()
  })

  it('un rol sin acceso no ve las dudas ni las pide', () => {
    mockUser('residente')
    const p = mockApis([duda()])

    render(<AnnouncementQuestionsPage />)

    expect(screen.getByText(/no tienes acceso a esta vista/i)).toBeInTheDocument()
    expect(p).not.toHaveBeenCalled()
  })
})
