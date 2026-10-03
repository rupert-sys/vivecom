import { useEffect, useRef, useState } from 'react'
import { API_URL, getToken } from '../api/client'

// Mismos eventos que manager.broadcast() manda desde el backend (incidents.py, access_log.py, packages.py).
export type LiveAlertEvento =
  | { evento: 'incidencia_creada'; incident_id: string; descripcion: string; tipo: string }
  | { evento: 'incidencia_actualizada'; incident_id: string; estado: string }
  | { evento: 'incidencia_comentada'; incident_id: string; comentario: string }
  | { evento: 'sync_conflicto'; recurso: string; client_id: string; motivo: string }

export interface LiveAlert {
  id: string
  mensaje: LiveAlertEvento
}

// Mismos roles que el backend deja conectarse a /incidents/ws (ver incidents.py) — nunca se intenta para
// los demás (residente, guardia, tesorero, vocero), ni siquiera para fallar: evita abrir y cerrar una
// conexión que el servidor rechazaría en cada carga de página.
const ROLES_CON_ALERTAS = new Set(['admin', 'comite_lectura', 'comite_aprobador'])

// El token va en la URL (?token=...) porque el handshake de WebSocket desde un navegador no permite mandar
// un header Authorization personalizado — mismo motivo documentado en el propio endpoint del backend.
function urlDeAlertas(token: string): string {
  const url = new URL('/incidents/ws', API_URL)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  url.searchParams.set('token', token)
  return url.toString()
}

type WebSocketFactory = (url: string) => WebSocket

// Inyectable para que las pruebas no abran un WebSocket real (mismo patrón que AbrirUrl en la app residente
// de Flutter): por default, el WebSocket real del navegador. Identidad fija (no una función nueva por
// render) para poder distinguirlo abajo de un factory inyectado explícitamente.
const webSocketReal: WebSocketFactory = (url) => new WebSocket(url)

export function useLiveAlerts(rol: string | undefined, webSocketFactory: WebSocketFactory = webSocketReal) {
  const [alertas, setAlertas] = useState<LiveAlert[]>([])
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!rol || !ROLES_CON_ALERTAS.has(rol)) return
    const token = getToken()
    if (!token) return
    // Nadie inyectó un factory de prueba y estamos bajo Vitest (import.meta.env.MODE === 'test'): no hay
    // backend real que acepte la conexión — sin esto, cualquier prueba que renderice Layout con un rol que
    // SÍ ve alertas (ej. admin) dispara un WebSocket real contra localhost:8000 en cada corrida de la suite.
    if (webSocketFactory === webSocketReal && import.meta.env.MODE === 'test') return

    // Se lee fuera de conectar() para que el cierre de limpieza (unmount, logout) nunca reintente — solo
    // una caída real de la conexión mientras el componente sigue montado dispara el reintento.
    let detenido = false
    let reintento: ReturnType<typeof setTimeout> | null = null

    function conectar() {
      const ws = webSocketFactory(urlDeAlertas(token!))
      wsRef.current = ws
      ws.onmessage = (event) => {
        try {
          const mensaje = JSON.parse(event.data) as LiveAlertEvento
          setAlertas((previas) => [...previas, { id: `${Date.now()}-${Math.random().toString(36).slice(2)}`, mensaje }])
        } catch {
          // Mensaje sin JSON válido: no hay nada útil que mostrar, se ignora.
        }
      }
      ws.onclose = () => {
        if (!detenido) reintento = setTimeout(conectar, 5000)
      }
    }
    conectar()

    return () => {
      detenido = true
      if (reintento) clearTimeout(reintento)
      wsRef.current?.close()
    }
  }, [rol, webSocketFactory])

  function descartar(id: string) {
    setAlertas((previas) => previas.filter((a) => a.id !== id))
  }

  return { alertas, descartar }
}
