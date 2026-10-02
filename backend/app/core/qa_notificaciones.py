"""
F1-35: QA de entrega de notificaciones — valida, contra un backend real, que cada punto de disparo
(paquetería, recordatorios/confirmaciones de cuota, avisos) de verdad manda el mensaje correcto al
teléfono correcto por el canal correcto, y que la caída de WhatsApp a SMS ("distintas condiciones de
red", F1-12) funciona de punta a punta — no solo a nivel del provider aislado (eso ya lo cubre
tests/test_twilio_provider.py), sino pasando por el código real de cada flujo del producto.

No hay cuenta de Twilio real (ver el aviso en notification_providers/twilio_provider.py) ni falta
hace una para esto: este guion levanta un servidor HTTP local que imita el endpoint de Twilio
(Messages.json) y captura cada request que le llega — a quién, qué canal (whatsapp: o SMS), y el
contenido — en vez de mandarlo a ningún lado de verdad. El backend debe arrancarse apuntando ahí:

    TWILIO_API_BASE=http://127.0.0.1:8991/2010-04-01 uvicorn app.main:app --reload

y, con eso corriendo:

    python -m app.core.qa_notificaciones

Como qa_flujo_cobro.py y qa_recorrido_arequipa.py, corre por HTTP contra Postgres real (no
pytest/SQLite) y no se detiene en la primera falla: imprime ✓/✗ por cada verificación y un resumen al
final, saliendo con código 1 si algo falló.

Lo que este guion NO puede validar (requiere personas y teléfonos reales, no un backend):
entrega visible en la propia app de WhatsApp o como SMS en un teléfono físico, en Android/iOS,
con la red real del operador — eso sigue siendo una prueba manual. Lo que sí deja cubierto de forma
repetible: que el backend intenta el canal correcto, con el contenido correcto, al teléfono correcto,
y que cae a SMS cuando WhatsApp falla — que es la parte que si se rompe, se rompe en el código, no en
el teléfono de nadie.
"""

import json
import sys
import threading
import time
from datetime import date, datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

import httpx

BASE_URL = "http://localhost:8000"
STUB_HOST = "127.0.0.1"  # lo que se imprime/usa por default en TWILIO_API_BASE (backend corriendo directo en el host)
# 0.0.0.0, no STUB_HOST: si el backend corre dentro de Docker (ver qa_notificaciones de una corrida contra
# docker compose), le llega por la IP del gateway del bridge (ej. 192.168.65.x en Docker Desktop/Mac), no por
# 127.0.0.1 — un bind a loopback solo-mente rechaza esas conexiones aunque la ruta de red sí exista.
STUB_BIND_HOST = "0.0.0.0"
STUB_PORT = 8991


class Recorrido:
    """Mismo patrón que qa_recorrido_arequipa.Recorrido: no se detiene en la primera falla."""

    def __init__(self) -> None:
        self.resultados: list[tuple[bool, str, str]] = []
        self.seccion = ""

    def titulo(self, texto: str) -> None:
        self.seccion = texto
        print(f"\n== {texto}")

    def ok(self, descripcion: str, condicion: bool, detalle: str = "") -> bool:
        self.resultados.append((bool(condicion), f"{self.seccion}: {descripcion}", detalle))
        print(f"  {'✓' if condicion else '✗'} {descripcion}" + (f"  → {detalle}" if detalle and not condicion else ""))
        return bool(condicion)


R = Recorrido()


class StubTwilio:
    """
    Imita lo mínimo del endpoint real de Twilio (POST .../Messages.json, Basic Auth, form-encoded
    From/To/Body) que TwilioProvider._enviar() necesita para no distinguir esto de la API real.
    `fallar_proximas` hace que las próximas N peticiones respondan 400 (como un número de WhatsApp sin
    aprobar, o Twilio caído) — así se puede forzar y verificar la caída a SMS en vivo.
    """

    def __init__(self) -> None:
        self.peticiones: list[dict] = []
        self.fallar_proximas = 0
        self._lock = threading.Lock()

    def recibir(self, from_: str, to: str, body: str) -> int:
        with self._lock:
            self.peticiones.append({"from": from_, "to": to, "body": body})
            if self.fallar_proximas > 0:
                self.fallar_proximas -= 1
                return 400
        return 201

    def ultimas(self, n: int) -> list[dict]:
        with self._lock:
            return self.peticiones[-n:]


def _levantar_stub(stub: StubTwilio) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802 — nombre que exige BaseHTTPRequestHandler
            largo = int(self.headers.get("Content-Length", 0))
            campos = parse_qs(self.rfile.read(largo).decode())
            codigo = stub.recibir(
                from_=campos.get("From", [""])[0], to=campos.get("To", [""])[0], body=campos.get("Body", [""])[0]
            )
            self.send_response(codigo)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"{}")

        def log_message(self, *args) -> None:  # silencioso: qa_recorrido_arequipa.py también evita ruido extra
            pass

    servidor = ThreadingHTTPServer((STUB_BIND_HOST, STUB_PORT), Handler)
    hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
    hilo.start()
    return servidor


def _preparar_tenant_con_residente(client: httpx.Client, sufijo: str) -> dict:
    # /signup ya no pide CLABE ni email/contraseña propios (v3.4, F3-06): los deriva del nombre del
    # condominio. La contraseña inicial del admin es el propio nombre_condominio, con
    # debe_cambiar_password=True — eso solo afecta a la UI (redirige a cambiarla), no bloquea la API.
    nombre_condominio = f"QA Notificaciones {sufijo}"
    signup = client.post(
        "/signup",
        json={
            "nombre_condominio": nombre_condominio,
            "cantidad_casas": 1,
            "nombre_admin": "Admin QA",
            "telefono_admin": f"+5215599{sufijo}",
        },
    )
    signup.raise_for_status()
    admin_email = signup.json()["admin_email"]
    admin_token = client.post("/auth/login", json={"email": admin_email, "password": nombre_condominio}).json()[
        "access_token"
    ]
    admin = {"Authorization": f"Bearer {admin_token}"}

    # signup ya creó "Casa 1" (con un residente sin activar, que no sirve para esto: sin teléfono y sin
    # Resident/ResidentProperty propios — ver POST /residents/activar). Se usa esa vivienda ya creada, pero
    # se liga un Resident de verdad (con teléfono) para poder notificarlo.
    prop_id = client.get("/properties", headers=admin).json()[0]["id"]
    telefono = f"+5215500{sufijo}"
    residente = client.post("/residents", json={"nombre": "Residente QA", "telefono": telefono}, headers=admin).json()
    client.post(
        f"/properties/{prop_id}/residents",
        json={"resident_id": residente["id"], "rol": "propietario"},
        headers=admin,
    ).raise_for_status()

    # La CLABE se configura aparte (PATCH /tenant/clabe) — /signup ya no la pide.
    clabe = sufijo.rjust(18, "8")
    client.patch(
        "/tenant/clabe", json={"clabe_nueva": clabe, "confirmo_cambio": True}, headers=admin
    ).raise_for_status()

    return {"admin": admin, "property_id": prop_id, "telefono": telefono, "clabe": clabe}


def main(stub: StubTwilio) -> None:
    sufijo = str(int(time.time()))[-6:]

    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        R.titulo("Preparación")
        ctx = _preparar_tenant_con_residente(client, sufijo)
        admin, prop_id, telefono = ctx["admin"], ctx["property_id"], ctx["telefono"]
        R.ok("tenant, vivienda y residente con teléfono quedaron listos", True)

        # ---------- Paquetería ----------
        R.titulo("Paquetería (F2-04)")
        paquete = client.post("/packages", json={"property_id": prop_id}, headers=admin).json()
        antes = len(stub.peticiones)
        client.post("/packages/send-notifications", headers=admin).raise_for_status()
        nuevas = stub.ultimas(len(stub.peticiones) - antes)
        llegada = next((p for p in nuevas if p["to"] == f"whatsapp:{telefono}"), None)
        R.ok("la notificación de llegada se mandó por WhatsApp al teléfono del residente", llegada is not None, str(nuevas))
        if llegada:
            R.ok("el mensaje menciona el paquete", "paquete" in llegada["body"].lower(), llegada["body"])

        antes = len(stub.peticiones)
        client.post(f"/packages/{paquete['id']}/pickup", headers=admin).raise_for_status()
        client.post("/packages/send-notifications", headers=admin).raise_for_status()
        nuevas = stub.ultimas(len(stub.peticiones) - antes)
        recogido = next((p for p in nuevas if p["to"] == f"whatsapp:{telefono}"), None)
        R.ok("la notificación de recogido se mandó por WhatsApp", recogido is not None, str(nuevas))
        if recogido:
            R.ok("el mensaje dice que ya se recogió", "recogi" in recogido["body"].lower(), recogido["body"])

        # ---------- Cuotas: recordatorio y confirmación (F1-13) ----------
        R.titulo("Cuotas: recordatorio y confirmación de pago (F1-13)")
        client.post(
            "/fees", json={"monto": 500.00, "periodicidad": "mensual", "activa_desde": "2026-01-01"}, headers=admin
        ).raise_for_status()
        client.post("/fees/generate-charges", headers=admin).raise_for_status()

        antes = len(stub.peticiones)
        client.post("/fees/send-reminders", json=None, headers=admin).raise_for_status()
        nuevas = stub.ultimas(len(stub.peticiones) - antes)
        recordatorio = next((p for p in nuevas if p["to"] == f"whatsapp:{telefono}"), None)
        R.ok("el recordatorio de cuota se mandó por WhatsApp", recordatorio is not None, str(nuevas))

        raw = json.dumps(
            {
                "monto": "500.00",
                "referenciaNumerica": client.get(f"/properties/{prop_id}", headers=admin).json()["referencia_pago"],
                "claveRastreo": f"STP-QANOTIF-{sufijo}",
                # Naive (sin zona), como en qa_flujo_cobro.py: la columna real es TIMESTAMP WITHOUT TIME
                # ZONE y asyncpg rechaza un datetime con tzinfo contra ella.
                "fechaOperacion": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
                "cuentaBeneficiario": ctx["clabe"],
            }
        ).encode()
        import hashlib
        import hmac

        firma = hmac.new(b"cambia-esto-en-produccion", raw, hashlib.sha256).hexdigest()
        client.post(
            "/payments/webhook/stp", content=raw, headers={"X-STP-Signature": firma, "Content-Type": "application/json"}
        ).raise_for_status()

        antes = len(stub.peticiones)
        client.post("/fees/send-payment-confirmations", headers=admin).raise_for_status()
        nuevas = stub.ultimas(len(stub.peticiones) - antes)
        confirmacion = next((p for p in nuevas if p["to"] == f"whatsapp:{telefono}"), None)
        R.ok("la confirmación de pago se mandó por WhatsApp", confirmacion is not None, str(nuevas))

        # ---------- Avisos (F1-32) ----------
        R.titulo("Avisos (F1-32)")
        client.post(
            "/announcements",
            json={"titulo": "Corte de agua programado", "contenido": "Mañana de 9 a 13h por mantenimiento."},
            headers=admin,
        ).raise_for_status()
        antes = len(stub.peticiones)
        client.post("/announcements/send-notifications", headers=admin).raise_for_status()
        nuevas = stub.ultimas(len(stub.peticiones) - antes)
        aviso = next((p for p in nuevas if p["to"] == f"whatsapp:{telefono}"), None)
        R.ok("el aviso se mandó por WhatsApp al residente", aviso is not None, str(nuevas))
        if aviso:
            R.ok("el mensaje incluye el título del aviso", "corte de agua" in aviso["body"].lower(), aviso["body"])

        # ---------- Condiciones de red: WhatsApp cae, debe caer a SMS (F1-12) ----------
        R.titulo("Condiciones de red: WhatsApp falla → cae a SMS (F1-12)")
        paquete2 = client.post("/packages", json={"property_id": prop_id}, headers=admin).json()
        stub.fallar_proximas = 1  # el próximo intento (WhatsApp) va a fallar con 400
        antes = len(stub.peticiones)
        client.post("/packages/send-notifications", headers=admin).raise_for_status()
        nuevas = stub.ultimas(len(stub.peticiones) - antes)
        R.ok("se intentaron los 2 canales (WhatsApp falló, se reintentó por SMS)", len(nuevas) == 2, str(nuevas))
        if len(nuevas) == 2:
            R.ok("el primer intento fue por WhatsApp", nuevas[0]["to"] == f"whatsapp:{telefono}", nuevas[0]["to"])
            R.ok("el segundo intento (respaldo) fue por SMS, sin el prefijo whatsapp:", nuevas[1]["to"] == telefono, nuevas[1]["to"])
        client.post(f"/packages/{paquete2['id']}/pickup", headers=admin)  # limpieza, no es parte de la prueba

        print(f"\nTenant de prueba: {admin['Authorization'][:20]}... (CLABE {ctx['clabe']}) — no requiere limpieza manual.")


if __name__ == "__main__":
    stub = StubTwilio()
    servidor = _levantar_stub(stub)
    print(f"Stub de Twilio escuchando en http://{STUB_HOST}:{STUB_PORT} — confirma que el backend arrancó con")
    print(f"  TWILIO_API_BASE=http://{STUB_HOST}:{STUB_PORT}/2010-04-01")
    try:
        main(stub)
    except AssertionError as exc:
        print(f"FALLÓ: {exc}", file=sys.stderr)
        sys.exit(1)
    except httpx.HTTPStatusError as exc:
        print(f"FALLÓ: {exc.response.status_code} {exc.response.text}", file=sys.stderr)
        sys.exit(1)
    finally:
        servidor.shutdown()

    fallidos = [r for r in R.resultados if not r[0]]
    print(f"\n{'='*60}\n{len(R.resultados) - len(fallidos)}/{len(R.resultados)} verificaciones OK")
    if fallidos:
        print("Fallaron:")
        for _, descripcion, detalle in fallidos:
            print(f"  ✗ {descripcion}" + (f" → {detalle}" if detalle else ""))
        sys.exit(1)
