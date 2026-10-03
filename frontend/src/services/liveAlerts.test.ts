import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { setToken } from '../api/client'
import { useLiveAlerts } from './liveAlerts'

class FakeWebSocket {
  static instancias: FakeWebSocket[] = []
  url: string
  cerrado = false
  onmessage: ((event: { data: string }) => void) | null = null
  onclose: (() => void) | null = null

  constructor(url: string) {
    this.url = url
    FakeWebSocket.instancias.push(this)
  }

  close() {
    this.cerrado = true
    this.onclose?.()
  }

  recibir(data: unknown) {
    this.onmessage?.({ data: JSON.stringify(data) })
  }
}

function factory(url: string) {
  return new FakeWebSocket(url) as unknown as WebSocket
}

describe('useLiveAlerts', () => {
  beforeEach(() => {
    FakeWebSocket.instancias = []
    setToken('un-token')
  })

  afterEach(() => {
    setToken(null)
    vi.useRealTimers()
  })

  it('no se conecta para un rol sin permiso de alertas (ej. residente)', () => {
    renderHook(() => useLiveAlerts('residente', factory))
    expect(FakeWebSocket.instancias).toHaveLength(0)
  })

  it('no se conecta sin sesión iniciada', () => {
    setToken(null)
    renderHook(() => useLiveAlerts('admin', factory))
    expect(FakeWebSocket.instancias).toHaveLength(0)
  })

  it('se conecta a /incidents/ws con el token para un rol con permiso', () => {
    renderHook(() => useLiveAlerts('admin', factory))
    expect(FakeWebSocket.instancias).toHaveLength(1)
    expect(FakeWebSocket.instancias[0].url).toContain('/incidents/ws?token=un-token')
  })

  it('agrega cada mensaje recibido a la lista de alertas', () => {
    const { result } = renderHook(() => useLiveAlerts('comite_aprobador', factory))

    act(() => {
      FakeWebSocket.instancias[0].recibir({
        evento: 'incidencia_creada', incident_id: 'i1', descripcion: 'Fuga de agua', tipo: 'mantenimiento',
      })
    })

    expect(result.current.alertas).toHaveLength(1)
    expect(result.current.alertas[0].mensaje).toEqual({
      evento: 'incidencia_creada', incident_id: 'i1', descripcion: 'Fuga de agua', tipo: 'mantenimiento',
    })
  })

  it('ignora un mensaje que no es JSON válido, sin tronar', () => {
    const { result } = renderHook(() => useLiveAlerts('admin', factory))
    act(() => {
      FakeWebSocket.instancias[0].onmessage?.({ data: 'esto no es json' })
    })
    expect(result.current.alertas).toHaveLength(0)
  })

  it('descartar quita solo esa alerta', () => {
    const { result } = renderHook(() => useLiveAlerts('admin', factory))

    act(() => {
      FakeWebSocket.instancias[0].recibir({ evento: 'sync_conflicto', recurso: 'package', client_id: 'c1', motivo: 'motivo x' })
      FakeWebSocket.instancias[0].recibir({ evento: 'sync_conflicto', recurso: 'incident', client_id: 'c2', motivo: 'motivo y' })
    })
    expect(result.current.alertas).toHaveLength(2)

    const idAQuitar = result.current.alertas[0].id
    act(() => result.current.descartar(idAQuitar))

    expect(result.current.alertas).toHaveLength(1)
    expect(result.current.alertas[0].mensaje).toMatchObject({ client_id: 'c2' })
  })

  it('reconecta 5 segundos después de un cierre inesperado', () => {
    vi.useFakeTimers()
    renderHook(() => useLiveAlerts('admin', factory))
    expect(FakeWebSocket.instancias).toHaveLength(1)

    act(() => {
      FakeWebSocket.instancias[0].close()
    })
    expect(FakeWebSocket.instancias).toHaveLength(1)

    act(() => {
      vi.advanceTimersByTime(5000)
    })
    expect(FakeWebSocket.instancias).toHaveLength(2)
  })

  it('al desmontar cierra la conexión y no reintenta', () => {
    vi.useFakeTimers()
    const { unmount } = renderHook(() => useLiveAlerts('admin', factory))
    const conexion = FakeWebSocket.instancias[0]

    unmount()

    expect(conexion.cerrado).toBe(true)
    act(() => {
      vi.advanceTimersByTime(10000)
    })
    expect(FakeWebSocket.instancias).toHaveLength(1)
  })
})
