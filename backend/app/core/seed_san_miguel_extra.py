"""
Segunda pasada de siembra sobre San Miguel (muestra), YA creado y con sus 30 residentes activados
(ver seed_san_miguel.py): CLABE de ejemplo, una amenidad con una reservación aprobada, dos acuerdos de pago
(uno solicitado, uno vigente), un aviso de bienvenida, 3 votaciones (abierta con resultados en vivo, abierta
con resultados secretos, y una ya cerrada con resultados), visitas y paquetes registrados, objetos perdidos
(uno autorizado, uno pendiente) e incidencias en sus 3 estados (abierta, en proceso, resuelta).

Corre por HTTP contra el backend público, DESPUÉS de seed_san_miguel.py:

    python -m app.core.seed_san_miguel_extra --api https://api.vivecom.com.mx

No es necesariamente idempotente (algunas acciones, como pedir un acuerdo de pago, rechazan un segundo intento
sobre la misma vivienda con un adeudo ya cubierto) — pensado para correr una sola vez.
"""

import argparse
import sys
from datetime import date, datetime, timedelta, timezone

import httpx

DOMINIO = "sanmiguelmuestra.com.mx"
ADMIN_PASSWORD = "SanMiguelAdmin2026"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--api", default="https://api.vivecom.com.mx")
    args = parser.parse_args()
    hoy = date.today()

    with httpx.Client(base_url=args.api, timeout=90.0) as c:
        def ok(r: httpx.Response, que: str) -> httpx.Response:
            if r.status_code >= 400:
                raise SystemExit(f"✗ {que}: {r.status_code} {r.text[:300]}")
            return r

        admin_tok = ok(c.post("/auth/login", json={"email": f"administracion@{DOMINIO}", "password": ADMIN_PASSWORD}), "login admin").json()["access_token"]
        A = {"Authorization": f"Bearer {admin_tok}"}

        usuarios = ok(c.get("/users", headers=A), "listar usuarios").json()
        propiedades = {p["identificador"]: p for p in ok(c.get("/properties", headers=A), "listar viviendas").json()}

        # --- 1. CLABE de ejemplo ---
        ok(c.patch("/tenant/clabe", headers=A, json={"clabe_nueva": "646180001122334455", "confirmo_cambio": True}), "clabe")

        # --- 2. Amenidad + reservación aprobada ---
        amenidad = ok(c.post("/amenities", headers=A, json={
            "nombre": "Salón de eventos", "periodo_limite_horas": 48, "dias_anticipacion_minimos": 3,
            "capacidad": 1, "cuota": 500, "notas_reglamento": "Reglamento interior, Art. 2 (áreas comunes).",
        }), "amenidad").json()

        # Casa 1 (al corriente) pide prestado el salón; se resetea su clave porque la original se perdió.
        clave_casa1 = "CasaUnoResidente1"
        cuenta_casa1 = next(u for u in usuarios if u["email"] == f"casa1@{DOMINIO}")
        ok(c.patch(f"/users/{cuenta_casa1['id']}", headers=A, json={"password": clave_casa1}), "reset clave casa1")
        r1_tok = ok(c.post("/auth/login", json={"email": f"casa1@{DOMINIO}", "password": clave_casa1}), "login casa1").json()["access_token"]
        R1 = {"Authorization": f"Bearer {r1_tok}"}

        inicio = (datetime.now(timezone.utc) + timedelta(days=10)).replace(hour=18, minute=0, second=0, microsecond=0)
        fin = inicio + timedelta(hours=4)
        reserva = ok(c.post("/reservations", headers=R1, json={
            "amenity_id": amenidad["id"], "fecha_inicio": inicio.isoformat(), "fecha_fin": fin.isoformat(),
        }), "reservación").json()
        ok(c.post(f"/reservations/{reserva['id']}/approve", headers=A), "aprobar reservación")

        # --- 3. Acuerdos de pago (2 de las 8 viviendas morosas: Casa 23 y Casa 25) ---
        primer_pago_futuro = hoy + timedelta(days=15)
        ok(c.post("/payment-agreements", headers=A, json={
            "property_id": propiedades["Casa 23"]["id"],
            "causa": "El residente reporta pérdida temporal de empleo y solicita diferir el pago en 3 parcialidades.",
            "numero_de_pagos": 3, "primer_pago": primer_pago_futuro.isoformat(),
        }), "acuerdo solicitado (Casa 23)").json()

        vigente = ok(c.post("/payment-agreements", headers=A, json={
            "property_id": propiedades["Casa 25"]["id"],
            "causa": "Gasto médico familiar imprevisto; el residente propone dos pagos quincenales para ponerse al corriente.",
            "numero_de_pagos": 2, "primer_pago": primer_pago_futuro.isoformat(),
        }), "acuerdo a aprobar (Casa 25)").json()
        ok(c.post(f"/payment-agreements/{vigente['id']}/approve", headers=A, json={"congela_recargo": True}), "aprobar acuerdo (Casa 25)")

        # --- 4. Aviso de bienvenida ---
        ok(c.post("/announcements", headers=A, json={
            "titulo": "Bienvenidos a San Miguel", "permite_dudas": True,
            "contenido": "Este es el condominio de muestra de Vivecom: todos los datos (residentes, pagos, "
                         "incidencias) son inventados. Recorre el panel y la app con confianza — nada de esto "
                         "es real, y puedes restablecerlo cuando quieras.",
        }), "aviso de bienvenida")

        # --- 5. Tres votaciones ---
        # A: abierta, resultados en vivo, varios residentes ya votaron.
        poll_a = ok(c.post("/polls", headers=A, json={
            "pregunta": "¿Cambiamos el portón de acceso peatonal?", "opciones": ["Sí", "No"],
            "fecha_cierre": (hoy + timedelta(days=30)).isoformat(), "resultados_en_vivo": True,
        }), "votación A").json()
        opcion_si = poll_a["opciones"][0]["id"]
        ok(c.post(f"/polls/{poll_a['id']}/vote", headers=R1, json={"option_id": opcion_si}), "voto casa1 en A")

        # B: abierta, resultados secretos hasta el cierre (elección de mesa directiva).
        ok(c.post("/polls", headers=A, json={
            "pregunta": "Elección de mesa directiva 2027", "opciones": ["Planilla A", "Planilla B", "Planilla C"],
            "fecha_cierre": (hoy + timedelta(days=20)).isoformat(), "resultados_en_vivo": False,
        }), "votación B")

        # C: se cierra de inmediato para mostrar una votación YA resuelta con resultados.
        poll_c = ok(c.post("/polls", headers=A, json={
            "pregunta": "¿Aprueban el nuevo reglamento de mascotas?", "opciones": ["Sí", "No"],
            "fecha_cierre": hoy.isoformat(), "resultados_en_vivo": True,
        }), "votación C").json()
        ok(c.post(f"/polls/{poll_c['id']}/vote", headers=R1, json={"option_id": poll_c["opciones"][0]["id"]}), "voto casa1 en C")
        ok(c.post("/polls/process-closures", headers=A), "cerrar votaciones vencidas")

        # --- 6. Visitas y paquetes ---
        visita = ok(c.post("/access-log", headers=A, json={
            "property_id": propiedades["Casa 4"]["id"], "tipo": "visitante", "nombre_visitante": "Carlos Iván Mendoza",
            "acompanantes": 1, "identificacion": "INE", "autorizado_por": "residente_previo",
        }), "registrar visita").json()
        ok(c.post(f"/access-log/{visita['id']}/exit", headers=A), "registrar salida de la visita")
        ok(c.post("/access-log", headers=A, json={
            "property_id": propiedades["Casa 10"]["id"], "tipo": "proveedor", "nombre_visitante": "Instalador de gas",
            "identificacion": "Credencial de la empresa", "autorizado_por": "telefono",
        }), "registrar proveedor")

        paquete1 = ok(c.post("/packages", headers=A, json={"property_id": propiedades["Casa 7"]["id"]}), "paquete Casa 7").json()
        ok(c.post(f"/packages/{paquete1['id']}/pickup", headers=A), "recoger paquete Casa 7")
        ok(c.post("/packages", headers=A, json={"property_id": propiedades["Casa 16"]["id"]}), "paquete Casa 16 (sin recoger)")

        # --- 7. Objetos perdidos: uno autorizado, uno pendiente ---
        objeto1 = ok(c.post("/lost-found", headers=R1, json={"descripcion": "Llavero con 3 llaves y un llavero de conejo, encontrado junto a la alberca."}), "objeto 1").json()
        ok(c.patch(f"/lost-found/{objeto1['id']}/moderate", headers=A, json={"estado": "autorizado"}), "autorizar objeto 1")
        ok(c.post("/lost-found", headers=R1, json={"descripcion": "Bicicleta infantil rodada 16, color rosa, sin candado."}), "objeto 2 (pendiente)")

        # --- 8. Incidencias en sus 3 estados ---
        ok(c.post("/incidents", headers=A, json={
            "descripcion": "Fuga de agua en el jardín central, cerca del área de juegos.", "tipo": "mantenimiento",
        }), "incidencia abierta").json()  # se deja tal cual: nace "abierta"

        en_proceso = ok(c.post("/incidents", headers=A, json={
            "descripcion": "Luminaria fundida en el andador entre Casa 12 y Casa 18.", "tipo": "mantenimiento",
        }), "incidencia en proceso").json()
        ok(c.patch(f"/incidents/{en_proceso['id']}/status", headers=A, json={"estado": "en_proceso"}), "marcar en proceso")

        resuelta = ok(c.post("/incidents", headers=A, json={
            "descripcion": "Vehículo desconocido estacionado en cajón de visitas por más de 24 horas.",
            "tipo": "seguridad", "property_id": propiedades["Casa 9"]["id"], "persona_involucrada": "Visitante sin identificar",
        }), "incidencia a resolver").json()
        ok(c.patch(f"/incidents/{resuelta['id']}/status", headers=A, json={"estado": "en_proceso"}), "resuelta: paso 1/2")
        ok(c.patch(f"/incidents/{resuelta['id']}/status", headers=A, json={"estado": "resuelta"}), "resuelta: paso 2/2")

        print("✓ San Miguel: CLABE, amenidad+reservación, 2 acuerdos de pago, aviso, 3 votaciones, visitas/paquetes,")
        print("  2 objetos perdidos, 3 incidencias (abierta/en_proceso/resuelta). Contraseña de Casa 1 (para pruebas):"
              f" {clave_casa1}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
