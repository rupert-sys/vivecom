import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { apiFetch, apiUpload, ApiError, getToken, setToken } from './client'

describe('apiFetch', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('adjunta el header Authorization cuando hay un token guardado', async () => {
    setToken('un-token-jwt')
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200, headers: { 'content-type': 'application/json' } }),
    )

    await apiFetch('/algo')

    const [, options] = vi.mocked(fetch).mock.calls[0]
    expect((options?.headers as Record<string, string>).Authorization).toBe('Bearer un-token-jwt')
  })

  it('no adjunta Authorization cuando auth=false (ej. login)', async () => {
    setToken('un-token-jwt')
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200, headers: { 'content-type': 'application/json' } }),
    )

    await apiFetch('/auth/login', { method: 'POST', body: { email: 'a@a.com' }, auth: false })

    const [, options] = vi.mocked(fetch).mock.calls[0]
    expect((options?.headers as Record<string, string>).Authorization).toBeUndefined()
  })

  it('lanza ApiError con el detail del backend cuando la respuesta no es 2xx', async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Credenciales inválidas' }), {
        status: 401,
        headers: { 'content-type': 'application/json' },
      }),
    )

    await expect(apiFetch('/auth/login')).rejects.toThrow('Credenciales inválidas')
  })

  it('extrae el mensaje del primer error cuando detail es una lista de validación de Pydantic (422)', async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: [
            {
              type: 'value_error',
              loc: ['body', 'clabe_nueva'],
              msg: 'Value error, La CLABE debe tener exactamente 18 dígitos numéricos',
            },
          ],
        }),
        { status: 422, headers: { 'content-type': 'application/json' } },
      ),
    )

    await expect(apiFetch('/tenant/clabe', { method: 'PATCH' })).rejects.toThrow(
      'La CLABE debe tener exactamente 18 dígitos numéricos',
    )
  })

  it('regresa undefined en respuestas 204 sin intentar parsear JSON', async () => {
    vi.mocked(fetch).mockResolvedValue(new Response(null, { status: 204 }))

    const result = await apiFetch('/properties/123')

    expect(result).toBeUndefined()
  })

  it('getToken/setToken persisten en localStorage', () => {
    expect(getToken()).toBeNull()
    setToken('abc')
    expect(getToken()).toBe('abc')
    setToken(null)
    expect(getToken()).toBeNull()
  })

  it('ApiError expone el status HTTP', async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Vivienda no encontrada' }), {
        status: 404,
        headers: { 'content-type': 'application/json' },
      }),
    )

    try {
      await apiFetch('/properties/no-existe')
      expect.unreachable()
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError)
      expect((err as ApiError).status).toBe(404)
    }
  })
})

describe('apiUpload', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('manda el FormData con el token y SIN fijar Content-Type (lo arma el navegador con el boundary)', async () => {
    setToken('un-token-jwt')
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ id: 'f1' }), { status: 201, headers: { 'content-type': 'application/json' } }),
    )
    const formData = new FormData()
    formData.append('kind', 'gasto')

    const resultado = await apiUpload<{ id: string }>('/files', formData)

    const [url, options] = vi.mocked(fetch).mock.calls[0]
    expect(String(url)).toMatch(/\/files$/)
    expect(options?.method).toBe('POST')
    expect(options?.body).toBe(formData)
    const headers = options?.headers as Record<string, string>
    expect(headers.Authorization).toBe('Bearer un-token-jwt')
    expect(headers['Content-Type']).toBeUndefined()
    expect(resultado).toEqual({ id: 'f1' })
  })

  it('convierte un error del backend en ApiError con su mensaje', async () => {
    // Una respuesta nueva por llamada: el cuerpo de una Response solo se puede leer una vez.
    vi.mocked(fetch).mockImplementation(async () =>
      new Response(JSON.stringify({ detail: 'El archivo pesa más de 10 MB.' }), {
        status: 413,
        headers: { 'content-type': 'application/json' },
      }),
    )

    await expect(apiUpload('/files', new FormData())).rejects.toMatchObject({
      status: 413,
      message: 'El archivo pesa más de 10 MB.',
    })
    await expect(apiUpload('/files', new FormData())).rejects.toBeInstanceOf(ApiError)
  })
})
