import { ApiError, getToken } from './client'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

// Los reportes se descargan como binario (.xlsx), no como JSON — apiFetch()
// asume JSON en la respuesta, así que esto hace su propio fetch y dispara la
// descarga en el navegador con un <a> temporal.
export async function downloadFile(path: string, filename: string): Promise<void> {
  const token = getToken()
  const response = await fetch(`${API_URL}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })

  if (!response.ok) {
    let message = 'No se pudo generar el reporte.'
    if (response.headers.get('content-type')?.includes('application/json')) {
      const data = await response.json()
      if (typeof data?.detail === 'string') message = data.detail
    }
    throw new ApiError(response.status, message)
  }

  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}
