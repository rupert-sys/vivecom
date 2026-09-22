import { apiUpload } from './client'
import { downloadFile } from './downloadFile'

export interface ResidentImportError {
  fila: number
  motivo: string
}

export interface ResidentImportResult {
  total_filas: number
  viviendas_creadas: number
  residentes_creados: number
  residentes_actualizados: number
  vinculos_creados: number
  vinculos_actualizados: number
  filas_con_error: ResidentImportError[]
}

export function importResidents(file: File): Promise<ResidentImportResult> {
  const formData = new FormData()
  formData.append('archivo', file)
  return apiUpload<ResidentImportResult>('/residents/import', formData)
}

export function downloadImportTemplate(): Promise<void> {
  return downloadFile('/residents/import-template', 'plantilla-condominos.xlsx')
}
