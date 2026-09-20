import { apiUpload } from './client'

export type TipoArchivo = 'gasto' | 'pago' | 'incidencia' | 'acuerdo'

export interface UploadedFile {
  id: string
  nombre_original: string
  content_type: string
  size: number
  ref: string
}

// Fotos (JPG, PNG, WEBP, HEIC) o PDF de hasta 10 MB. El backend valida el tipo por los bytes del archivo.
export const TIPOS_DE_ARCHIVO_ACEPTADOS = 'image/jpeg,image/png,image/webp,image/heic,application/pdf'

export function uploadFile(file: File, kind: TipoArchivo): Promise<UploadedFile> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('kind', kind)
  return apiUpload<UploadedFile>('/files', formData)
}
