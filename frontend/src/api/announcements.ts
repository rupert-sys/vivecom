import { apiFetch } from './client'
import type { Announcement, ReadStatusEntry } from '../types'

export interface AnnouncementInput {
  titulo: string
  contenido: string
  fecha_publicacion?: string
  permite_dudas?: boolean
  // null quita el plazo; ausente no lo toca.
  dudas_hasta?: string | null
}

export function listAnnouncements(): Promise<Announcement[]> {
  return apiFetch<Announcement[]>('/announcements')
}

export function createAnnouncement(payload: AnnouncementInput): Promise<Announcement> {
  return apiFetch<Announcement>('/announcements', { method: 'POST', body: payload })
}

export function updateAnnouncement(id: string, payload: Partial<AnnouncementInput>): Promise<Announcement> {
  return apiFetch<Announcement>(`/announcements/${id}`, { method: 'PATCH', body: payload })
}

export function getReadStatus(id: string): Promise<ReadStatusEntry[]> {
  return apiFetch<ReadStatusEntry[]>(`/announcements/${id}/read-status`)
}
