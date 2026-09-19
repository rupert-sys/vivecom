import { apiFetch } from './client'
import type { AnnouncementQuestion } from '../types'

// La bandeja: dudas sin responder de todos los avisos, las más viejas primero.
export function listPendingQuestions(): Promise<AnnouncementQuestion[]> {
  return apiFetch<AnnouncementQuestion[]>('/announcement-questions/pending')
}

export function listAnsweredQuestions(): Promise<AnnouncementQuestion[]> {
  return apiFetch<AnnouncementQuestion[]>('/announcement-questions/answered')
}

// `publicar`: la muestra a todos como aclaración, sin nombre ni vivienda.
export function answerQuestion(id: string, respuesta: string, publicar: boolean): Promise<AnnouncementQuestion> {
  return apiFetch<AnnouncementQuestion>(`/announcement-questions/${id}/answer`, {
    method: 'POST',
    body: { respuesta, publicar },
  })
}

export function updateQuestion(id: string, cambios: { publica?: boolean; respuesta?: string }): Promise<AnnouncementQuestion> {
  return apiFetch<AnnouncementQuestion>(`/announcement-questions/${id}`, { method: 'PATCH', body: cambios })
}
