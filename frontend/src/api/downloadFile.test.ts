import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { downloadFile } from './downloadFile'
import { ApiError, setToken } from './client'

describe('downloadFile', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.stubGlobal('fetch', vi.fn())
    vi.stubGlobal('URL', {
      createObjectURL: vi.fn(() => 'blob:fake-url'),
      revokeObjectURL: vi.fn(),
    })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('adjunta el token y dispara la descarga con el nombre de archivo dado', async () => {
    setToken('un-token')
    const blob = new Blob(['contenido'], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    vi.mocked(fetch).mockResolvedValue(new Response(blob, { status: 200 }))
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})

    await downloadFile('/reports/expenses/export', 'gastos.xlsx')

    const [, options] = vi.mocked(fetch).mock.calls[0]
    expect((options?.headers as Record<string, string>).Authorization).toBe('Bearer un-token')
    expect(clickSpy).toHaveBeenCalledOnce()
    expect(URL.createObjectURL).toHaveBeenCalledOnce()
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:fake-url')
  })

  it('lanza ApiError con el mensaje del backend si la respuesta no es 2xx', async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ detail: 'No tienes acceso a este reporte' }), {
        status: 403,
        headers: { 'content-type': 'application/json' },
      }),
    )

    await expect(downloadFile('/reports/expenses/export', 'gastos.xlsx')).rejects.toThrow(
      'No tienes acceso a este reporte',
    )
  })

  it('ApiError expone el status HTTP incluso para descargas', async () => {
    vi.mocked(fetch).mockResolvedValue(new Response(null, { status: 500 }))

    try {
      await downloadFile('/reports/expenses/export', 'gastos.xlsx')
      expect.unreachable()
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError)
      expect((err as ApiError).status).toBe(500)
    }
  })
})
