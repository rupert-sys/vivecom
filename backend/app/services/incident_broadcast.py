"""
F2-06: alertas en tiempo real de incidencias (HU-S06) vía WebSocket, para
admin y comité.

LIMITACIÓN CONOCIDA: este manager de conexiones vive en memoria del propio
proceso. En dev (un solo proceso Uvicorn) funciona directo; en producción
con varios workers/contenedores, una incidencia creada en el proceso A no
le llega a un admin conectado al proceso B — cada proceso solo conoce sus
propias conexiones. Para eso hace falta pub/sub real (Redis, que el
proyecto ya usa como broker de Celery — ver settings.redis_url), pero no se
implementó aquí: no hay un Redis real disponible en las pruebas de esta
sesión para verificarlo de punta a punta, y este manager en memoria sí es
completamente probable con el TestClient de FastAPI (ver
test_incident_websocket.py). Si se despliega con más de un proceso, esto es
lo primero que hay que resolver antes de confiar en la alerta en tiempo real.
"""

from collections import defaultdict

from fastapi import WebSocket


class IncidentConnectionManager:
    def __init__(self):
        self._conexiones: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, schema_name: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._conexiones[schema_name].add(websocket)

    def disconnect(self, schema_name: str, websocket: WebSocket) -> None:
        self._conexiones[schema_name].discard(websocket)

    async def broadcast(self, schema_name: str, mensaje: dict) -> None:
        muertas = []
        for ws in self._conexiones[schema_name]:
            try:
                await ws.send_json(mensaje)
            except Exception:  # noqa: BLE001 — una conexión muerta no debe tumbar el broadcast a las demás
                muertas.append(ws)
        for ws in muertas:
            self._conexiones[schema_name].discard(ws)


manager = IncidentConnectionManager()
