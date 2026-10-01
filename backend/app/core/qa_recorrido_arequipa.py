"""
Recorrido de punta a punta de un mes de un condominio con el reglamento de Arequipa (18-ene-2026).

Aprovisiona un condominio NUEVO, lo configura con el reglamento y hace pasar por él a todos los actores
(administrador, tesorero, comité, vocero, guardia y cinco viviendas) con todo lo que el reglamento
promete: cuotas con recargo del 5% mensual sobre saldo, pago por SPEI / en efectivo / con comprobante,
morosos sin voto ni áreas comunes, el área adoquinada (8 días, hasta la 01:00, $1,000), gastos que
requieren asamblea y 3 cotizaciones, la caseta (bitácora, cajones de visitas, proveedores, paquetes,
incidencias con foto), las dudas en avisos y el acuerdo de pago (prórroga de cuotas).

Como qa_flujo_cobro.py, NO corre con pytest/SQLite: usa /signup, el webhook firmado de STP y varios
schemas de Postgres reales. Corre por HTTP contra un backend levantado (uvicorn + Postgres):

    python -m app.core.qa_recorrido_arequipa

Cada corrida crea un condominio nuevo (sufijo aleatorio, o el de RECORRIDO_SUFIJO para tener un login conocido) y lo deja en la base de desarrollo.

A diferencia de un guion con `assert`, NO se detiene en la primera falla: cada verificación imprime ✓ o ✗
y al final hay un resumen, para ver de una vez todo lo que no cumple el reglamento. Sale con código 1 si
alguna falló. Los montos esperados se calculan con la fecha de HOY (el recargo depende de cuántos meses
lleva vencida cada cuota), así que el guion sirve cualquier día del mes.
"""

import hashlib
import hmac
import json
import os
import secrets
import sys
import uuid
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import httpx

BASE_URL = "http://localhost:8000"
STP_WEBHOOK_SECRET = "cambia-esto-en-produccion"  # noqa: S105 — valor de desarrollo, no un secreto real
TZ = ZoneInfo("America/Mexico_City")
CUOTA = 750.0
JPEG = b"\xff\xd8\xff\xe0" + b"\x07" * 400
PDF = b"%PDF-1.7\n" + b"0" * 200


class Recorrido:
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

    def excepcion(self, exc: Exception) -> None:
        self.resultados.append((False, f"{self.seccion}: excepción", repr(exc)))
        print(f"  ✗ EXCEPCIÓN en esta sección: {exc!r}")


R = Recorrido()


# ---------- utilidades ----------


def _meses_vencidos(periodo: date, hoy: date, dia_recargo: int = 6) -> int:
    """Cuántas veces ya corrió el recargo mensual de una cuota (la misma regla del backend, escrita a parte)."""
    transcurridos = (hoy.year - periodo.year) * 12 + (hoy.month - periodo.month)
    return max(0, transcurridos + (1 if hoy.day >= dia_recargo else 0))


def _primer_dia_de_mes(hoy: date, meses_atras: int) -> date:
    indice = hoy.year * 12 + (hoy.month - 1) - meses_atras
    return date(indice // 12, indice % 12 + 1, 1)


def _utc(dia: date, hora: int, minuto: int = 0) -> str:
    local = datetime.combine(dia, time(hora, minuto), tzinfo=TZ)
    return local.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _spei(client: httpx.Client, *, clabe: str, monto: float, referencia: str, clave: str) -> dict:
    cuerpo = {
        "monto": f"{monto:.2f}", "referenciaNumerica": referencia, "claveRastreo": clave,
        "fechaOperacion": datetime.now().isoformat(timespec="seconds"), "cuentaBeneficiario": clabe,
    }
    raw = json.dumps(cuerpo).encode()
    firma = hmac.new(STP_WEBHOOK_SECRET.encode(), raw, hashlib.sha256).hexdigest()
    r = client.post("/payments/webhook/stp", content=raw, headers={"X-STP-Signature": firma, "Content-Type": "application/json"})
    r.raise_for_status()
    return r.json()


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _subir(client: httpx.Client, token: str, kind: str, contenido: bytes = JPEG, nombre: str = "archivo.jpg") -> dict:
    r = client.post("/files", headers=_h(token), data={"kind": kind}, files={"file": (nombre, contenido, "application/octet-stream")})
    r.raise_for_status()
    return r.json()


def _descargar(_client: httpx.Client, url: str) -> httpx.Response:
    """Abre un enlace firmado tal como lo haría el navegador o la app: sin Authorization."""
    return httpx.get(url, timeout=30)


# ---------- el recorrido ----------


def main() -> int:
    hoy = datetime.now(TZ).date()
    sufijo = os.environ.get("RECORRIDO_SUFIJO") or str(secrets.randbelow(900000) + 100000)  # fijo para tener un login conocido
    clabe = sufijo.rjust(18, "8")
    pw = "Recorrido12345"
    correo = lambda rol: f"{rol}{sufijo}@recorrido.mx"  # noqa: E731

    with httpx.Client(base_url=BASE_URL, timeout=60.0) as c:
        # ------------------------------------------------------------------ 1
        R.titulo("1. El condominio nace y se configura con el reglamento")
        try:
            r = c.post("/signup", json={"nombre_condominio": f"QA Recorrido Arequipa {sufijo}", "admin_email": correo("admin"),
                                        "admin_password": pw, "clabe_destino": clabe})
            r.raise_for_status()
            admin = c.post("/auth/login", json={"email": correo("admin"), "password": pw}).json()["access_token"]
            A = _h(admin)
            reglamento_inicial = c.get("/tenant/reglamento", headers=A).json()
            R.ok("un condominio sin configurar arranca con las reglas por defecto (10% único, sin efectivo)",
                 reglamento_inicial["recargo_modalidad"] == "unico" and reglamento_inicial["acepta_pago_efectivo"] is False)

            casas = {}
            for n in range(1, 6):
                p = c.post("/properties", headers=A, json={"identificador": f"Casa {n}"}).json()
                casas[n] = p
            residentes = {}
            for n in casas:
                u = c.post("/users", headers=A, json={"email": correo(f"casa{n}"), "password": pw, "rol": "residente",
                                                     "property_id": casas[n]["id"]})
                u.raise_for_status()
                residentes[n] = c.post("/auth/login", json={"email": correo(f"casa{n}"), "password": pw}).json()["access_token"]
            staff = {}
            ids = {}
            for rol in ("tesorero", "guardia", "comite_aprobador", "comite_lectura", "vocero"):
                u = c.post("/users", headers=A, json={"email": correo(rol), "password": pw, "rol": rol})
                u.raise_for_status()
                ids[rol] = u.json()["id"]
                staff[rol] = c.post("/auth/login", json={"email": correo(rol), "password": pw}).json()["access_token"]
            T, G, CA, CL, V = (_h(staff[k]) for k in ("tesorero", "guardia", "comite_aprobador", "comite_lectura", "vocero"))
            RES = {n: _h(t) for n, t in residentes.items()}
            R.ok("5 viviendas con su residente y 5 roles de personal dados de alta", len(casas) == 5 and len(staff) == 5)

            c.post("/fees", headers=A, json={"monto": CUOTA, "periodicidad": "mensual", "activa_desde": "2026-01-01"}).raise_for_status()

            efectivo_sin_activar = c.post("/payments/manual", headers=T, json={"property_id": casas[1]["id"], "monto": 10, "metodo": "efectivo"})
            R.ok("el efectivo se rechaza mientras el condominio no lo active", efectivo_sin_activar.status_code == 409,
                 str(efectivo_sin_activar.status_code))

            cambio = c.patch("/tenant/reglamento", headers=A, json={
                "dia_limite_pago": 5, "recargo_porcentaje": 0.05, "recargo_modalidad": "mensual_sobre_saldo",
                "acepta_pago_efectivo": True, "morosos_sin_voto": True, "morosos_sin_areas_comunes": True,
                "gasto_umbral_asamblea": 10000, "cotizaciones_minimas": 3, "cajones_visitas": 7,
                "horas_max_estacionamiento_visitas": 24, "dudas_en_avisos_por_defecto": False,
            })
            reg = cambio.json()
            R.ok("el reglamento de Arequipa queda configurado (5% mensual sobre saldo, día 5, efectivo, 7 cajones)",
                 cambio.status_code == 200 and reg["dia_recargo"] == 6 and reg["recargo_porcentaje"] == 0.05 and reg["cajones_visitas"] == 7)
            R.ok("un residente no puede cambiar el reglamento pero sí consultarlo",
                 c.patch("/tenant/reglamento", headers=RES[1], json={"cajones_visitas": 99}).status_code == 403
                 and c.get("/tenant/reglamento", headers=RES[1]).status_code == 200)
        except Exception as exc:  # noqa: BLE001
            R.excepcion(exc)
            return _resumen()

        propiedad = {n: casas[n]["id"] for n in casas}

        # ------------------------------------------------------------------ 2
        R.titulo("2. Las cuotas del trimestre y el recargo del 5% mensual sobre saldo")
        try:
            periodos = [_primer_dia_de_mes(hoy, m) for m in (2, 1, 0)]
            for p in periodos:
                g = c.post("/fees/generate-charges", headers=A, params={"periodo": p.isoformat()})
                g.raise_for_status()
            estado1 = c.get(f"/properties/{propiedad[1]}/statement", headers=RES[1]).json()
            R.ok("cada vivienda tiene 3 cargos de $750 (el trimestre)", len(estado1["cargos"]) == 3 and estado1["deuda_total"] == 3 * CUOTA,
                 str(estado1["deuda_total"]))
            recargos = [round(CUOTA * 0.05 * _meses_vencidos(p, hoy), 2) for p in periodos]
            deuda_con_recargo = round(3 * CUOTA + sum(recargos), 2)
            R.ok(f"hoy es {hoy}: el reglamento dice que la deuda de una vivienda que no pagó sería ${deuda_con_recargo:,.2f}", True)
        except Exception as exc:  # noqa: BLE001
            R.excepcion(exc)
            return _resumen()

        # ------------------------------------------------------------------ 3
        R.titulo("3. Casa 1 paga a tiempo por SPEI, antes de que corra el recargo")
        try:
            _spei(c, clabe=clabe, monto=3 * CUOTA, referencia=casas[1]["referencia_pago"], clave=f"REC-{sufijo}-1")
            e = c.get(f"/properties/{propiedad[1]}/statement", headers=RES[1]).json()
            R.ok("Casa 1 queda sin deuda", e["deuda_total"] == 0.0 and all(x["estado"] == "pagado" for x in e["cargos"]))
            spei_sin_match = _spei(c, clabe=clabe, monto=500, referencia="9999999", clave=f"REC-{sufijo}-X")
            R.ok("un depósito con referencia desconocida queda pendiente para tesorería (no se pierde)", spei_sin_match["payment_estado"] == "pendiente")
            rj = c.post(f"/payments/{spei_sin_match['payment_id']}/reject", headers=T)
            R.ok("tesorería lo rechaza", rj.status_code == 200 and rj.json()["estado"] == "rechazado")
        except Exception as exc:  # noqa: BLE001
            R.excepcion(exc)

        # ------------------------------------------------------------------ 4
        R.titulo("4. Corre el recargo: las viviendas que no pagaron son morosas")
        try:
            c.post("/fees/apply-late-surcharges", headers=A).raise_for_status()
            e2 = c.get(f"/properties/{propiedad[2]}/statement", headers=RES[2]).json()
            R.ok("Casa 2 debe sus 3 cuotas MÁS el 5% mensual por cada mes vencido", abs(e2["deuda_total"] - deuda_con_recargo) < 0.01,
                 f"debe {e2['deuda_total']}, esperado {deuda_con_recargo}")
            R.ok("Casa 2 está en mora y la app le explica qué pierde (voto y áreas comunes)",
                 e2["en_mora"] is True and len(e2["restricciones_por_mora"]) == 2)
            antes = e2["deuda_total"]
            c.post("/fees/apply-late-surcharges", headers=A).raise_for_status()
            despues = c.get(f"/properties/{propiedad[2]}/statement", headers=RES[2]).json()["deuda_total"]
            R.ok("correr el recargo otra vez NO lo duplica (es idempotente)", abs(antes - despues) < 0.01, f"{antes} → {despues}")
            R.ok("Casa 1, que pagó a tiempo, no tiene recargo ni mora",
                 c.get(f"/properties/{propiedad[1]}/statement", headers=RES[1]).json()["en_mora"] is False)
        except Exception as exc:  # noqa: BLE001
            R.excepcion(exc)

        # ------------------------------------------------------------------ 5
        R.titulo("5. Casa 3 paga en efectivo y Casa 4 y 5 mandan su comprobante del banco")
        ingresos = 3 * CUOTA  # lo de Casa 1
        try:
            deuda3 = c.get(f"/properties/{propiedad[3]}/statement", headers=RES[3]).json()["deuda_total"]
            pago3 = c.post("/payments/manual", headers=T, json={"property_id": propiedad[3], "monto": deuda3, "metodo": "efectivo"})
            R.ok("tesorería registra el efectivo de Casa 3 y queda al corriente",
                 pago3.status_code == 201 and c.get(f"/properties/{propiedad[3]}/statement", headers=RES[3]).json()["deuda_total"] == 0.0)
            ingresos += deuda3
            recibo = c.get(f"/payments/{pago3.json()['id']}/receipt", headers=RES[3])
            R.ok("Casa 3 descarga su recibo (PDF)", recibo.status_code == 200 and recibo.content.startswith(b"%PDF"))
            R.ok("Casa 2 no puede descargar el recibo de Casa 3",
                 c.get(f"/payments/{pago3.json()['id']}/receipt", headers=RES[2]).status_code == 403)

            deuda4 = c.get(f"/properties/{propiedad[4]}/statement", headers=RES[4]).json()["deuda_total"]
            f4 = _subir(c, residentes[4], "pago")
            p4 = c.post("/payment-proofs", headers=RES[4], json={"monto": deuda4, "archivo_id": f4["id"], "nota": "Transferencia BBVA",
                                                                 "fecha_pago": hoy.isoformat()})
            R.ok("Casa 4 adjunta su comprobante y queda pendiente (no toca su cuenta todavía)",
                 p4.status_code == 201 and p4.json()["estado"] == "pendiente"
                 and c.get(f"/properties/{propiedad[4]}/statement", headers=RES[4]).json()["deuda_total"] == deuda4)
            R.ok("tesorería abre el archivo con un enlace firmado", _descargar(c, p4.json()["archivo_url"]).content == JPEG)
            R.ok("un residente no puede aceptar comprobantes", c.post(f"/payment-proofs/{p4.json()['id']}/accept", headers=RES[4], json={}).status_code == 403)
            acepta = c.post(f"/payment-proofs/{p4.json()['id']}/accept", headers=T, json={})
            R.ok("tesorería lo acepta: se registra el pago y Casa 4 queda al corriente",
                 acepta.status_code == 200 and c.get(f"/properties/{propiedad[4]}/statement", headers=RES[4]).json()["deuda_total"] == 0.0,
                 acepta.text[:120])
            ingresos += deuda4
            R.ok("aceptarlo dos veces no cuenta el dinero dos veces",
                 c.post(f"/payment-proofs/{p4.json()['id']}/accept", headers=T, json={}).status_code == 409)

            f5 = _subir(c, residentes[5], "pago")
            p5 = c.post("/payment-proofs", headers=RES[5], json={"monto": 100, "archivo_id": f5["id"]})
            rechazo = c.post(f"/payment-proofs/{p5.json()['id']}/reject", headers=T, json={"motivo": "Comprobante ilegible"})
            visto = c.get("/payment-proofs", headers=RES[5]).json()[0]
            R.ok("tesorería rechaza el de Casa 5 con un motivo y ella lo ve", rechazo.status_code == 200 and visto["motivo_rechazo"] == "Comprobante ilegible")
            R.ok("Casa 5 sigue debiendo (un comprobante rechazado no paga nada)",
                 c.get(f"/properties/{propiedad[5]}/statement", headers=RES[5]).json()["deuda_total"] > 0)
        except Exception as exc:  # noqa: BLE001
            R.excepcion(exc)

        # ------------------------------------------------------------------ 6
        R.titulo("6. Tesorería ve quién pagó, quién falta y quién es moroso")
        try:
            cobranza = c.get("/reports/collection-status", headers=T).json()
            R.ok("3 viviendas al corriente y 2 morosas (Casa 2 y Casa 5)",
                 cobranza["al_corriente"] == 3 and cobranza["morosas"] == 2 and cobranza["pendientes"] == 0, str({k: cobranza[k] for k in ("al_corriente", "pendientes", "morosas")}))
            nombres_morosos = {v["identificador"] for v in cobranza["viviendas"] if v["estatus"] == "moroso"}
            R.ok("los morosos son exactamente Casa 2 y Casa 5", nombres_morosos == {"Casa 2", "Casa 5"}, str(nombres_morosos))
            R.ok("los morosos aparecen primero en la lista", cobranza["viviendas"][0]["estatus"] == "moroso")
            constancia_ok = c.get(f"/reports/no-debt-certificate/{propiedad[1]}", headers=T)
            constancia_no = c.get(f"/reports/no-debt-certificate/{propiedad[2]}", headers=T)
            R.ok("Casa 1 obtiene su constancia de no adeudo (PDF)", constancia_ok.status_code == 200 and constancia_ok.content.startswith(b"%PDF"))
            R.ok("Casa 2 NO puede obtener constancia (debe)", constancia_no.status_code == 409)
            R.ok("un residente no ve el reporte de cobranza", c.get("/reports/collection-status", headers=RES[1]).status_code == 403)
        except Exception as exc:  # noqa: BLE001
            R.excepcion(exc)

        # ------------------------------------------------------------------ 7
        R.titulo("7. Votación: los morosos conservan voz pero no voto")
        try:
            poll = c.post("/polls", headers=V, json={"pregunta": "¿Cambiamos el portón de acceso?", "opciones": ["Sí", "No"],
                                                     "fecha_cierre": (hoy + timedelta(days=30)).isoformat()})
            poll.raise_for_status()
            pid, opcion = poll.json()["id"], poll.json()["opciones"][0]["id"]
            visto2 = next(p for p in c.get("/polls", headers=RES[2]).json() if p["id"] == pid)
            R.ok("la app de Casa 2 sabe que su vivienda no puede votar", visto2["voto_restringido_por_mora"] is True)
            R.ok("Casa 2 (morosa) no puede votar: 403", c.post(f"/polls/{pid}/vote", headers=RES[2], json={"option_id": opcion}).status_code == 403)
            R.ok("Casa 1 (al corriente) vota", c.post(f"/polls/{pid}/vote", headers=RES[1], json={"option_id": opcion}).status_code == 204)
            R.ok("Casa 1 no puede votar dos veces", c.post(f"/polls/{pid}/vote", headers=RES[1], json={"option_id": opcion}).status_code == 409)
            R.ok("Casa 3 (pagó en efectivo) ya puede votar", c.post(f"/polls/{pid}/vote", headers=RES[3], json={"option_id": opcion}).status_code == 204)
        except Exception as exc:  # noqa: BLE001
            R.excepcion(exc)

        # ------------------------------------------------------------------ 8
        R.titulo("8. El área adoquinada: 8 días, hasta la 01:00 y $1,000")
        try:
            area = c.post("/amenities", headers=A, json={
                "nombre": "Área adoquinada", "periodo_limite_horas": 48, "dias_anticipacion_minimos": 8, "hora_fin_maxima": "01:00",
                "cuota": 1000, "notas_reglamento": "Reglamento Art. 2 III-VIII"}).json()
            R.ok("el área muestra sus reglas en lenguaje llano", any("8 días" in x for x in area["reglas"]) and any("01:00" in x for x in area["reglas"])
                 and any("$1,000.00" in x for x in area["reglas"]))
            c.post(f"/amenities/{area['id']}/approvers", headers=A, json={"user_id": ids["comite_aprobador"]}).raise_for_status()
            evento = hoy + timedelta(days=10)
            reservar = lambda n, ini, fin: c.post("/reservations", headers=RES[n], json={"amenity_id": area["id"], "fecha_inicio": ini, "fecha_fin": fin})  # noqa: E731

            corta = reservar(1, _utc(hoy + timedelta(days=3), 15), _utc(hoy + timedelta(days=3), 23))
            R.ok("con 3 días de anticipación se rechaza (mínimo 8)", corta.status_code == 422 and "8 días" in corta.text, corta.text[:100])
            tarde = reservar(1, _utc(evento, 15), _utc(evento + timedelta(days=1), 2))
            R.ok("un evento que termina a las 02:00 se rechaza (tope 01:00)", tarde.status_code == 422 and "01:00" in tarde.text, tarde.text[:100])
            morosa = reservar(2, _utc(evento, 15), _utc(evento + timedelta(days=1), 1))
            R.ok("Casa 2 (morosa) no puede reservar áreas comunes: 403", morosa.status_code == 403, morosa.text[:100])
            buena = reservar(1, _utc(evento, 15), _utc(evento + timedelta(days=1), 1))
            R.ok("Casa 1 reserva con 10 días de anticipación y hasta la 01:00 del día siguiente",
                 buena.status_code == 201 and buena.json()["cuota"] == 1000.0 and buena.json()["cuota_pagada"] is False, buena.text[:120])
            choque = reservar(3, _utc(evento, 18), _utc(evento, 22))
            R.ok("Casa 3 no puede tomar el mismo horario (409)", choque.status_code == 409, choque.text[:100])
            disp = c.get(f"/amenities/{area['id']}/disponibilidad", headers=RES[3], params={"fecha": evento.isoformat()}).json()
            R.ok("la disponibilidad dice que ese día no queda lugar", disp["cupos_libres_todo_el_dia"] == 0 and len(disp["reservaciones"]) == 1)
            aprobada = c.post(f"/reservations/{buena.json()['id']}/approve", headers=CA)
            R.ok("el comité aprobador designado la aprueba", aprobada.status_code == 200 and aprobada.json()["estado"] == "aprobada", aprobada.text[:100])
            R.ok("el comité de solo lectura no puede aprobar", c.post(f"/reservations/{buena.json()['id']}/approve", headers=CL).status_code == 403)
            R.ok("un residente no marca la cuota como recibida", c.post(f"/reservations/{buena.json()['id']}/cuota-pagada", headers=RES[1]).status_code == 403)
            cuota = c.post(f"/reservations/{buena.json()['id']}/cuota-pagada", headers=T)
            R.ok("tesorería recibe los $1,000 y Casa 1 lo ve", cuota.status_code == 200
                 and c.get("/reservations", headers=RES[1]).json()[0]["cuota_pagada"] is True)
            R.ok("tesorería ve todas las reservaciones para cobrarlas", len(c.get("/reservations", headers=T).json()) == 1)
        except Exception as exc:  # noqa: BLE001
            R.excepcion(exc)

        # ------------------------------------------------------------------ 9
        R.titulo("9. Gastos: comprobante como archivo, asamblea y 3 cotizaciones")
        gastos = 0.0
        try:
            comprobante = _subir(c, admin, "gasto", PDF, "factura.pdf")
            g1 = c.post("/expenses", headers=A, json={"categoria": "Jardinería", "monto": 1200, "fecha": hoy.isoformat(),
                                                      "comprobante_archivo_id": comprobante["id"], "tipo_comprobante": "factura"})
            R.ok("un gasto operativo se registra con su factura en PDF", g1.status_code == 201, g1.text[:120])
            gastos += 1200
            R.ok("un gasto sin comprobante se rechaza",
                 c.post("/expenses", headers=A, json={"categoria": "X", "monto": 10, "fecha": hoy.isoformat()}).status_code == 422)
            portón = {"categoria": "Portón", "monto": 45000, "fecha": hoy.isoformat(), "tipo": "extraordinario",
                      "comprobante_archivo_id": _subir(c, admin, "gasto", PDF, "portón.pdf")["id"]}
            sin_asamblea = c.post("/expenses", headers=A, json=portón)
            R.ok("un gasto extraordinario de $45,000 sin asamblea se rechaza", sin_asamblea.status_code == 422 and "asamblea" in sin_asamblea.text)
            dos = c.post("/expenses", headers=A, json={**portón, "aprobado_en_asamblea": True, "cotizaciones": [
                {"proveedor": "Herrería López", "monto": 45000}, {"proveedor": "Portones MX", "monto": 52000}]})
            R.ok("con asamblea pero solo 2 cotizaciones se rechaza", dos.status_code == 422 and "3 cotizaciones" in dos.text)
            cot_archivo = _subir(c, admin, "gasto", PDF, "cotizacion.pdf")
            tres = c.post("/expenses", headers=A, json={**portón, "aprobado_en_asamblea": True, "acta_referencia": "Asamblea 18-ene-2026",
                                                        "cotizaciones": [{"proveedor": "Herrería López", "monto": 45000, "archivo_id": cot_archivo["id"]},
                                                                         {"proveedor": "Portones MX", "monto": 52000},
                                                                         {"proveedor": "Cercas del Norte", "monto": 48000}]})
            R.ok("con asamblea y 3 cotizaciones se registra", tres.status_code == 201, tres.text[:120])
            gastos += 45000
            R.ok("un residente puede abrir el comprobante de un gasto (transparencia)",
                 _descargar(c, c.get("/expenses", headers=RES[1]).json()[0]["comprobante_url"]).status_code == 200)
            R.ok("y también la cotización subida como archivo",
                 _descargar(c, next(g for g in c.get("/expenses", headers=RES[1]).json() if g["categoria"] == "Portón")["cotizaciones"][0]["url"]).content == PDF)
            R.ok("un residente no registra gastos", c.post("/expenses", headers=RES[1], json={"categoria": "X", "monto": 1, "fecha": hoy.isoformat(), "comprobante_url": "x"}).status_code == 403)
            resumen = c.get("/expenses/summary", headers=RES[1]).json()
            R.ok(f"el resumen cuadra: ingresos ${ingresos:,.2f}, gastos ${gastos:,.2f}",
                 abs(resumen["ingresos"] - ingresos) < 0.01 and abs(resumen["gastos"] - gastos) < 0.01, str(resumen))
            R.ok("el saldo es en contra (se gastó más de lo cobrado)", abs(resumen["saldo"] - (ingresos - gastos)) < 0.01 and resumen["saldo"] < 0)
            R.ok("lo que falta por cobrar es la deuda de Casa 2 y Casa 5", resumen["por_cobrar"] > 0)
        except Exception as exc:  # noqa: BLE001
            R.excepcion(exc)

        # ------------------------------------------------------------------ 10
        R.titulo("10. La caseta: bitácora, cajones, proveedores, paquetes e incidencias")
        try:
            cid = str(uuid.uuid4())
            entrada = {"tipo": "visitante", "property_id": propiedad[1], "placas": ["ABC123"], "client_id": cid, "nombre_visitante": "Juan Pérez",
                       "acompanantes": 2, "identificacion": "INE 1234", "autorizado_por": "telefono"}
            e1 = c.post("/access-log", headers=G, json=entrada)
            R.ok("el guardia registra al visitante con nombre, acompañantes, identificación y quién autorizó",
                 e1.status_code == 201 and e1.json()["nombre_visitante"] == "Juan Pérez" and e1.json()["acompanantes"] == 2)
            R.ok("reenviar el mismo registro (sincronización offline) no lo duplica",
                 c.post("/access-log", headers=G, json=entrada).json()["id"] == e1.json()["id"])
            R.ok("el mismo registro con otro nombre es un conflicto (409)",
                 c.post("/access-log", headers=G, json={**entrada, "nombre_visitante": "Otro"}).status_code == 409)
            c.post("/access-log", headers=G, json={"tipo": "proveedor", "placas": ["PRV999"], "nombre_visitante": "Mensajería"})
            c.post("/access-log", headers=G, json={"tipo": "residente", "placas": ["RES001"]})
            c.post("/access-log", headers=G, json={"tipo": "visitante", "nombre_visitante": "A pie"})
            park = c.get("/access-log/estacionamiento-visitas", headers=G).json()
            R.ok("hay 7 cajones y 2 ocupados (visitante y proveedor con vehículo; el residente y quien va a pie no cuentan)",
                 park["total_cajones"] == 7 and park["ocupados"] == 2 and park["libres"] == 5, str(park))
            c.post(f"/access-log/{e1.json()['id']}/exit", headers=G).raise_for_status()
            R.ok("al salir el visitante se libera un cajón", c.get("/access-log/estacionamiento-visitas", headers=G).json()["libres"] == 6)
            R.ok("un residente no accede a la bitácora", c.get("/access-log", headers=RES[1]).status_code == 403)

            prov = c.post("/visitor-qr/provider", headers=G, json={"descripcion": "Plomería López", "property_id": propiedad[4]})
            val = c.post(f"/visitor-qr/{prov.json()['codigo']}/validate", headers=G).json()
            R.ok("el guardia emite un código de proveedor y al escanearlo ve quién es y a dónde va",
                 val["valido"] and val["tipo"] == "proveedor" and val["vivienda"] == "Casa 4" and val["descripcion"] == "Plomería López", str(val))
            R.ok("el código no se puede usar dos veces", c.post(f"/visitor-qr/{prov.json()['codigo']}/validate", headers=G).json()["motivo"] == "ya_usado")
            R.ok("un residente no emite códigos de proveedor", c.post("/visitor-qr/provider", headers=RES[1], json={"descripcion": "X"}).status_code == 403)
            qr = c.post("/visitor-qr", headers=RES[1], json={"nombre_visitante": "Juan Pérez"}).json()
            valqr = c.post(f"/visitor-qr/{qr['codigo']}/validate", headers=G).json()
            R.ok("Casa 1 genera el QR de su visita y el guardia lo valida diciendo a qué casa va",
                 valqr["valido"] and valqr["tipo"] == "visitante" and valqr["vivienda"] == "Casa 1")
            R.ok("Casa 1 ve sus códigos y si ya se usaron", c.get("/visitor-qr", headers=RES[1]).json()[0]["usado"] is True)

            pcid = str(uuid.uuid4())
            k1 = c.post("/packages", headers=G, json={"property_id": propiedad[3], "client_id": pcid}).json()
            k2 = c.post("/packages", headers=G, json={"property_id": propiedad[3], "client_id": pcid}).json()
            R.ok("un paquete registrado dos veces (sincronización) es uno solo", k1["id"] == k2["id"])
            R.ok("la caseta pide avisar al residente", c.post("/packages/send-notifications", headers=G).status_code == 200)
            R.ok("Casa 3 ve su paquete en la caseta y Casa 1 no ve el ajeno",
                 len(c.get("/packages/mine", headers=RES[3]).json()) == 1 and c.get("/packages/mine", headers=RES[1]).json() == [])
            c.post(f"/packages/{k1['id']}/pickup", headers=G).raise_for_status()
            R.ok("al entregarlo queda como recogido", c.get("/packages/mine", headers=RES[3]).json()[0]["fecha_recogido"] is not None)

            foto = _subir(c, staff["guardia"], "incidencia", JPEG, "luminaria.jpg")
            inc = c.post("/incidents", headers=G, json={"descripcion": "Luminaria fundida frente a la Casa 2", "tipo": "mantenimiento",
                                                        "property_id": propiedad[2], "persona_involucrada": "Vecino", "foto_archivo_id": foto["id"],
                                                        "client_id": str(uuid.uuid4())})
            R.ok("el guardia levanta una incidencia de mantenimiento con foto, casa y persona", inc.status_code == 201, inc.text[:120])
            lista = c.get("/incidents", headers=CL).json()
            R.ok("el comité la ve y abre la foto", len(lista) == 1 and _descargar(c, lista[0]["foto_url"]).content == JPEG)
            R.ok("se puede filtrar por tipo", len(c.get("/incidents", headers=A, params={"tipo": "mantenimiento"}).json()) == 1
                 and c.get("/incidents", headers=A, params={"tipo": "seguridad"}).json() == [])
            R.ok("un residente no ve incidencias", c.get("/incidents", headers=RES[1]).status_code == 403)
        except Exception as exc:  # noqa: BLE001
            R.excepcion(exc)

        # ------------------------------------------------------------------ 11
        R.titulo("11. Avisos y dudas: un canal acotado, no un chat")
        try:
            aviso = c.post("/announcements", headers=A, json={"titulo": "Corte de agua el jueves", "contenido": "De 10am a 2pm.", "permite_dudas": True,
                                                              "dudas_hasta": (hoy + timedelta(days=7)).isoformat()})
            aid = aviso.json()["id"]
            sin = c.post("/announcements", headers=A, json={"titulo": "Solo informativo", "contenido": "x"}).json()
            R.ok("el administrador activa las dudas de un aviso (y otro nace sin dudas)", aviso.json()["dudas_abiertas"] is True and sin["permite_dudas"] is False)
            R.ok("no se puede preguntar en un aviso sin dudas",
                 c.post(f"/announcements/{sin['id']}/questions", headers=RES[1], json={"texto": "¿?"}).status_code == 409)
            q = c.post(f"/announcements/{aid}/questions", headers=RES[1], json={"texto": "¿Habrá agua en la caseta?"})
            R.ok("Casa 1 manda su duda", q.status_code == 201 and q.json()["estado"] == "abierta")
            R.ok("Casa 3 NO ve la duda de Casa 1", c.get(f"/announcements/{aid}/questions", headers=RES[3]).json() == [])
            bandeja = c.get("/announcement-questions/pending", headers=CL).json()
            R.ok("el comité ve la duda con su vivienda", [(d["vivienda"], d["texto"]) for d in bandeja] == [("Casa 1", "¿Habrá agua en la caseta?")])
            R.ok("el comité de solo lectura no puede responder",
                 c.post(f"/announcement-questions/{q.json()['id']}/answer", headers=CL, json={"respuesta": "x"}).status_code == 403)
            resp = c.post(f"/announcement-questions/{q.json()['id']}/answer", headers=CA, json={"respuesta": "Sí, hay cisterna.", "publicar": True})
            R.ok("el comité aprobador responde y la publica como aclaración", resp.status_code == 200 and resp.json()["publica"] is True)
            aclaracion = c.get(f"/announcements/{aid}/questions", headers=RES[3]).json()
            R.ok("Casa 3 ve la aclaración SIN nombre ni vivienda",
                 len(aclaracion) == 1 and aclaracion[0]["vivienda"] is None and aclaracion[0]["propia"] is False and aclaracion[0]["respuesta"] == "Sí, hay cisterna.")
            R.ok("Casa 1 ve su respuesta como nueva y deja de serlo al abrirla",
                 c.get("/announcement-questions/mine", headers=RES[1]).json()[0]["respuesta_nueva"] is True
                 and c.post("/announcement-questions/mine/seen", headers=RES[1]).status_code == 204
                 and c.get("/announcement-questions/mine", headers=RES[1]).json()[0]["respuesta_nueva"] is False)
            for i in range(3):
                c.post(f"/announcements/{aid}/questions", headers=RES[1], json={"texto": f"Duda {i}"})
            R.ok("el tope de 3 dudas sin responder por vivienda se respeta",
                 c.post(f"/announcements/{aid}/questions", headers=RES[1], json={"texto": "Una más"}).status_code == 409)
            R.ok("el administrador ve quién leyó el aviso", c.get(f"/announcements/{aid}/read-status", headers=A).status_code == 200)
        except Exception as exc:  # noqa: BLE001
            R.excepcion(exc)

        # ------------------------------------------------------------------ 12
        R.titulo("12. Al final del mes: ponerse al corriente devuelve los derechos")
        try:
            deuda2 = c.get(f"/properties/{propiedad[2]}/statement", headers=RES[2]).json()["deuda_total"]
            c.post("/payments/manual", headers=T, json={"property_id": propiedad[2], "monto": deuda2, "metodo": "efectivo"}).raise_for_status()
            e = c.get(f"/properties/{propiedad[2]}/statement", headers=RES[2]).json()
            R.ok("Casa 2 paga todo en efectivo y deja de estar en mora", e["deuda_total"] == 0.0 and e["en_mora"] is False)
            pid2 = c.post("/polls", headers=V, json={"pregunta": "¿Pintamos la fachada?", "opciones": ["Sí", "No"],
                                                     "fecha_cierre": (hoy + timedelta(days=30)).isoformat()}).json()
            R.ok("y ya puede votar en una votación nueva",
                 c.post(f"/polls/{pid2['id']}/vote", headers=RES[2], json={"option_id": pid2["opciones"][0]["id"]}).status_code == 204)
            cobranza2 = c.get("/reports/collection-status", headers=T).json()
            R.ok("el estatus de cobranza ahora tiene 4 al corriente y 1 moroso (Casa 5)", cobranza2["al_corriente"] == 4 and cobranza2["morosas"] == 1)
        except Exception as exc:  # noqa: BLE001
            R.excepcion(exc)

        # ------------------------------------------------------------------ 13
        R.titulo("13. Casa 5 no puede pagar todo a tiempo: acuerdo de pago en 3 mensualidades")
        try:
            deuda5 = c.get(f"/properties/{propiedad[5]}/statement", headers=RES[5]).json()["deuda_total"]
            primer_pago = hoy + timedelta(days=30)
            causa = "Perdí mi empleo en el último mes y regularizo mis ingresos."
            solicitar = lambda n, **cuerpo: c.post("/payment-agreements", headers=RES[n], json=cuerpo)  # noqa: E731

            R.ok("Casa 1, que no debe nada, no tiene qué prorrogar (409)",
                 solicitar(1, causa=causa, numero_de_pagos=2, primer_pago=primer_pago.isoformat()).status_code == 409)
            R.ok("una causa de menos de 20 caracteres se rechaza",
                 solicitar(5, causa="No puedo", numero_de_pagos=3, primer_pago=primer_pago.isoformat()).status_code == 422)
            R.ok("un primer pago que ya pasó se rechaza",
                 solicitar(5, causa=causa, numero_de_pagos=3, primer_pago=hoy.isoformat()).status_code == 422)
            R.ok("6 pagos desde dentro de un mes rebasan el plazo máximo de 3 meses",
                 solicitar(5, causa=causa, numero_de_pagos=6, primer_pago=primer_pago.isoformat()).status_code == 422)

            nueva = solicitar(5, causa=causa, numero_de_pagos=3, primer_pago=primer_pago.isoformat())
            R.ok("Casa 5 solicita 3 pagos y queda 'solicitado'", nueva.status_code == 201 and nueva.json()["estado"] == "solicitado", nueva.text[:150])
            aid5 = nueva.json()["id"]
            R.ok("no puede tener dos acuerdos abiertos a la vez",
                 solicitar(5, causa=causa, numero_de_pagos=2, primer_pago=primer_pago.isoformat()).status_code == 409)

            pid5 = c.post("/polls", headers=V, json={"pregunta": "¿Ponemos cámaras en el acceso?", "opciones": ["Sí", "No"],
                                                     "fecha_cierre": (hoy + timedelta(days=30)).isoformat()}).json()
            e5 = c.get(f"/properties/{propiedad[5]}/statement", headers=RES[5]).json()
            R.ok("una solicitud pendiente NO suspende nada: sigue en mora y sin voto",
                 e5["en_mora"] is True and e5["en_acuerdo"] is False
                 and c.post(f"/polls/{pid5['id']}/vote", headers=RES[5], json={"option_id": pid5["opciones"][0]["id"]}).status_code == 403)
            R.ok("Casa 4 no ve la solicitud de Casa 5", c.get("/payment-agreements", headers=RES[4]).json() == [])
            R.ok("el comité de solo lectura la ve pero no la decide",
                 [a["vivienda"] for a in c.get("/payment-agreements", headers=CL).json()] == ["Casa 5"]
                 and c.post(f"/payment-agreements/{aid5}/approve", headers=CL, json={}).status_code == 403)
            R.ok("un residente no puede aprobar su propia solicitud",
                 c.post(f"/payment-agreements/{aid5}/approve", headers=RES[5], json={}).status_code == 403)

            aprobado = c.post(f"/payment-agreements/{aid5}/approve", headers=CA, json={"congela_recargo": True})
            ac = aprobado.json()
            R.ok("el comité aprobador lo aprueba: queda vigente con su calendario de 3 pagos que suman la deuda",
                 aprobado.status_code == 200 and ac["estado"] == "vigente" and len(ac["calendario"]) == 3
                 and abs(sum(x["monto"] for x in ac["calendario"]) - deuda5) < 0.01 and abs(ac["deuda_inicial"] - deuda5) < 0.01,
                 f"{aprobado.status_code} {aprobado.text[:200]}")
            R.ok("el primer pago es el que pidió Casa 5 y el recargo queda congelado",
                 ac["calendario"][0]["fecha"] == primer_pago.isoformat() and ac["congela_recargo"] is True)

            e5 = c.get(f"/properties/{propiedad[5]}/statement", headers=RES[5]).json()
            R.ok("con el acuerdo vigente Casa 5 deja de estar en mora, aunque sigue debiendo",
                 e5["en_mora"] is False and e5["en_acuerdo"] is True and e5["restricciones_por_mora"] == [] and abs(e5["deuda_total"] - deuda5) < 0.01,
                 str({k: e5[k] for k in ("en_mora", "en_acuerdo", "deuda_total")}))
            R.ok("y recupera el voto", c.post(f"/polls/{pid5['id']}/vote", headers=RES[5], json={"option_id": pid5["opciones"][0]["id"]}).status_code == 204)
            reserva5 = c.post("/reservations", headers=RES[5], json={"amenity_id": area["id"], "fecha_inicio": _utc(hoy + timedelta(days=20), 15),
                                                                     "fecha_fin": _utc(hoy + timedelta(days=21), 1)})
            R.ok("y las áreas comunes", reserva5.status_code == 201, f"{reserva5.status_code} {reserva5.text[:120]}")
            cobranza3 = c.get("/reports/collection-status", headers=T).json()
            fila5 = next(v for v in cobranza3["viviendas"] if v["identificador"] == "Casa 5")
            R.ok("tesorería ve a Casa 5 'con acuerdo', ya no como morosa",
                 fila5["estatus"] == "con_acuerdo" and cobranza3["con_acuerdo"] == 1 and cobranza3["morosas"] == 0,
                 str({k: cobranza3[k] for k in ("al_corriente", "con_acuerdo", "morosas")}))
            R.ok("la constancia de no adeudo sigue negada mientras haya deuda",
                 c.get(f"/reports/no-debt-certificate/{propiedad[5]}", headers=T).status_code == 409)
            c.post("/fees/apply-late-surcharges", headers=A).raise_for_status()
            R.ok("correr el recargo no le suma nada mientras el acuerdo esté vigente",
                 abs(c.get(f"/properties/{propiedad[5]}/statement", headers=RES[5]).json()["deuda_total"] - deuda5) < 0.01)

            pago1 = ac["calendario"][0]["monto"]
            _spei(c, clabe=clabe, monto=pago1, referencia=casas[5]["referencia_pago"], clave=f"REC-{sufijo}-A1")
            va = next(a for a in c.get("/payment-agreements", headers=RES[5]).json() if a["id"] == aid5)
            R.ok("Casa 5 hace su primer pago: el acuerdo lo cuenta y el siguiente es el 2º del calendario",
                 va["estado"] == "vigente" and abs(va["abonado"] - pago1) < 0.01 and va["proximo_pago"]["fecha"] == ac["calendario"][1]["fecha"],
                 str({k: va[k] for k in ("estado", "abonado", "proximo_pago")}))
            R.ok("sigue sin estar en mora", c.get(f"/properties/{propiedad[5]}/statement", headers=RES[5]).json()["en_mora"] is False)

            _spei(c, clabe=clabe, monto=va["pendiente_cubierto"], referencia=casas[5]["referencia_pago"], clave=f"REC-{sufijo}-A2")
            c.post("/payment-agreements/process", headers=A).raise_for_status()
            va = next(a for a in c.get("/payment-agreements", headers=RES[5]).json() if a["id"] == aid5)
            e5 = c.get(f"/properties/{propiedad[5]}/statement", headers=RES[5]).json()
            R.ok("al liquidar lo acordado el seguimiento diario lo marca 'cumplido' y Casa 5 queda sin deuda",
                 va["estado"] == "cumplido" and e5["deuda_total"] == 0.0 and e5["en_mora"] is False and e5["en_acuerdo"] is False,
                 str({"estado": va["estado"], "deuda": e5["deuda_total"]}))
            R.ok("con todo pagado, las 5 viviendas están al corriente",
                 c.get("/reports/collection-status", headers=T).json()["al_corriente"] == 5)
        except Exception as exc:  # noqa: BLE001
            R.excepcion(exc)

        return _resumen()


def _resumen() -> int:
    total = len(R.resultados)
    fallas = [(d, det) for ok, d, det in R.resultados if not ok]
    print("\n" + "=" * 70)
    print(f"RESULTADO: {total - len(fallas)}/{total} verificaciones correctas")
    for descripcion, detalle in fallas:
        print(f"  ✗ {descripcion}" + (f"\n      {detalle[:300]}" if detalle else ""))
    print("(el condominio de la corrida queda en la base de desarrollo, como el de qa_flujo_cobro.py)")
    return 1 if fallas else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except httpx.ConnectError:
        print("No se pudo conectar con el backend en localhost:8000. Levántalo primero (uvicorn app.main:app).", file=sys.stderr)
        sys.exit(2)
