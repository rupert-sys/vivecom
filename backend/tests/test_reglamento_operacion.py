"""
Reglas operativas del reglamento interior (Condominio Arequipa, 18-ene-2026)
que no son de reservaciones: voto de morosos (Art. 5 III), gastos con
asamblea y cotizaciones (Art. 8), bitácora de caseta (Art. 17 V), cajones de
visitas (Art. 2 IX-XI), estatus de cobranza y constancia de no adeudo (Art. 16).
"""

import uuid
from datetime import timedelta

from app.api.deps import get_current_user
from app.main import app
from app.schemas.auth import CurrentUser
from app.services.reglamento_service import hoy_local


def _como(rol: str, property_id: str | None = None):
    tenant_id = app.dependency_overrides[get_current_user]().tenant_id

    def override():
        return CurrentUser(
            user_id=str(uuid.uuid4()), tenant_id=tenant_id, schema_name="test", rol=rol, property_id=property_id
        )

    app.dependency_overrides[get_current_user] = override


def _vivienda(client, nombre="Casa 1") -> str:
    return client.post("/properties", json={"identificador": nombre}).json()["id"]


def _con_cuota_vencida(client, *nombres) -> list[str]:
    ids = [_vivienda(client, n) for n in nombres]
    client.post("/fees", json={"monto": 750, "periodicidad": "mensual", "activa_desde": "2020-01-01"})
    client.post("/fees/generate-charges", params={"periodo": "2020-01-01"})
    return ids


# ---------- Voto de morosos (Art. 5 III) ----------


def _votacion(client):
    _como("vocero")
    poll = client.post(
        "/polls",
        json={"pregunta": "¿Cambiamos el portón?", "opciones": ["Sí", "No"], "fecha_cierre": "2099-12-31"},
    ).json()
    _como("admin")
    return poll


def test_una_vivienda_morosa_conserva_voz_pero_no_voto(client):
    client.patch("/tenant/reglamento", json={"morosos_sin_voto": True})
    (prop,) = _con_cuota_vencida(client, "Casa 1")
    poll = _votacion(client)

    _como("residente", property_id=prop)
    visto = next(p for p in client.get("/polls").json() if p["id"] == poll["id"])
    assert visto["voto_restringido_por_mora"] is True

    respuesta = client.post(f"/polls/{poll['id']}/vote", json={"option_id": poll["opciones"][0]["id"]})
    assert respuesta.status_code == 403
    assert "voz" in respuesta.json()["detail"]


def test_una_vivienda_al_corriente_vota_normal_aunque_la_regla_este_activa(client):
    client.patch("/tenant/reglamento", json={"morosos_sin_voto": True})
    prop = _vivienda(client)
    poll = _votacion(client)

    _como("residente", property_id=prop)
    visto = next(p for p in client.get("/polls").json() if p["id"] == poll["id"])
    assert visto["voto_restringido_por_mora"] is False
    assert client.post(f"/polls/{poll['id']}/vote", json={"option_id": poll["opciones"][0]["id"]}).status_code == 204


def test_sin_la_regla_un_moroso_vota_como_siempre(client):
    (prop,) = _con_cuota_vencida(client, "Casa 1")
    poll = _votacion(client)

    _como("residente", property_id=prop)
    visto = next(p for p in client.get("/polls").json() if p["id"] == poll["id"])
    assert visto["voto_restringido_por_mora"] is None
    assert client.post(f"/polls/{poll['id']}/vote", json={"option_id": poll["opciones"][0]["id"]}).status_code == 204


# ---------- Gastos (Art. 8) ----------

_COTIZACIONES = [
    {"proveedor": "Herrería López", "monto": 45000},
    {"proveedor": "Portones MX", "monto": 52000},
    {"proveedor": "Cercas del Norte", "monto": 48000},
]


def _gasto(**extra):
    base = {"categoria": "portón", "monto": 45000, "comprobante_url": "https://x/f.pdf", "fecha": "2026-09-01"}
    base.update(extra)
    return base


def test_gasto_extraordinario_sobre_el_umbral_requiere_asamblea(client):
    client.patch("/tenant/reglamento", json={"gasto_umbral_asamblea": 10000})
    respuesta = client.post("/expenses", json=_gasto(tipo="extraordinario", cotizaciones=_COTIZACIONES))
    assert respuesta.status_code == 422
    assert "asamblea" in respuesta.json()["detail"]


def test_gasto_sobre_el_umbral_requiere_tres_cotizaciones_distintas(client):
    client.patch("/tenant/reglamento", json={"gasto_umbral_asamblea": 10000})
    dos = client.post(
        "/expenses", json=_gasto(tipo="programado", aprobado_en_asamblea=True, cotizaciones=_COTIZACIONES[:2])
    )
    assert dos.status_code == 422
    assert "3 cotizaciones" in dos.json()["detail"]

    repetidas = [_COTIZACIONES[0], _COTIZACIONES[0], {"proveedor": " herrería lópez ", "monto": 40000}]
    assert client.post(
        "/expenses", json=_gasto(tipo="programado", aprobado_en_asamblea=True, cotizaciones=repetidas)
    ).status_code == 422


def test_gasto_completo_se_registra_con_su_sustento(client):
    client.patch("/tenant/reglamento", json={"gasto_umbral_asamblea": 10000})
    respuesta = client.post(
        "/expenses",
        json=_gasto(
            tipo="extraordinario", aprobado_en_asamblea=True, acta_referencia="Asamblea 18-ene-2026",
            cotizaciones=_COTIZACIONES, tipo_comprobante="factura",
        ),
    )
    assert respuesta.status_code == 201
    creado = respuesta.json()
    assert creado["tipo"] == "extraordinario" and len(creado["cotizaciones"]) == 3
    assert client.get(f"/expenses/{creado['id']}").json()["acta_referencia"] == "Asamblea 18-ene-2026"


def test_gasto_operativo_o_bajo_el_umbral_no_pide_asamblea(client):
    client.patch("/tenant/reglamento", json={"gasto_umbral_asamblea": 10000})
    assert client.post("/expenses", json=_gasto(monto=50000)).status_code == 201  # operativo
    assert client.post("/expenses", json=_gasto(monto=9000, tipo="programado")).status_code == 201


def test_sin_umbral_configurado_no_se_exige_nada(client):
    assert client.post("/expenses", json=_gasto(tipo="extraordinario")).status_code == 201


def test_resumen_financiero_da_ingresos_gastos_y_saldo(client):
    client.patch("/tenant/reglamento", json={"acepta_pago_efectivo": True})
    prop = _vivienda(client)
    client.post("/fees", json={"monto": 750, "periodicidad": "mensual", "activa_desde": "2026-01-01"})
    client.post("/fees/generate-charges", params={"periodo": "2026-09-01"})
    client.post("/payments/manual", json={"property_id": prop, "monto": 750})
    client.post("/expenses", json=_gasto(categoria="limpieza", monto=200, tipo="operativo"))
    client.post("/expenses", json=_gasto(categoria="limpieza", monto=100, tipo="operativo"))
    client.post("/expenses", json=_gasto(categoria="jardinería", monto=50, tipo="programado"))

    resumen = client.get("/expenses/summary").json()
    assert resumen["ingresos"] == 750.0
    assert resumen["gastos"] == 350.0
    assert resumen["saldo"] == 400.0  # a favor
    assert resumen["por_cobrar"] == 0.0
    assert resumen["gastos_por_categoria"][0] == {"concepto": "limpieza", "total": 300.0, "cantidad": 2}
    assert {t["concepto"] for t in resumen["gastos_por_tipo"]} == {"operativo", "programado"}


def test_resumen_con_mas_gastos_que_ingresos_da_saldo_en_contra(client):
    client.post("/expenses", json=_gasto(monto=500))
    assert client.get("/expenses/summary").json()["saldo"] == -500.0


def test_resumen_respeta_el_rango_de_fechas(client):
    client.post("/expenses", json=_gasto(monto=100, fecha="2026-01-10"))
    client.post("/expenses", json=_gasto(monto=300, fecha="2026-06-10"))
    assert client.get("/expenses/summary", params={"desde": "2026-06-01"}).json()["gastos"] == 300.0
    assert client.get("/expenses/summary", params={"hasta": "2026-03-01"}).json()["gastos"] == 100.0


def test_un_residente_puede_ver_el_resumen_de_gastos(client):
    _como("residente", property_id=str(uuid.uuid4()))
    assert client.get("/expenses/summary").status_code == 200


# ---------- Bitácora de caseta (Art. 17 V) ----------


def test_la_bitacora_guarda_nombre_acompanantes_identificacion_y_autorizacion(client):
    prop = _vivienda(client)
    respuesta = client.post(
        "/access-log",
        json={
            "property_id": prop, "tipo": "visitante", "placas": ["ABC123"], "nombre_visitante": "Juan Pérez",
            "acompanantes": 2, "identificacion": "INE 1234", "autorizado_por": "telefono",
        },
    )
    assert respuesta.status_code == 201
    creado = respuesta.json()
    assert (creado["nombre_visitante"], creado["acompanantes"], creado["autorizado_por"]) == ("Juan Pérez", 2, "telefono")

    listado = client.get("/access-log", params={"property_id": prop}).json()
    assert listado[0]["identificacion"] == "INE 1234"
    assert client.get(f"/access-log/{creado['id']}").json()["nombre_visitante"] == "Juan Pérez"


def test_la_bitacora_rechaza_una_autorizacion_desconocida_o_acompanantes_negativos(client):
    assert client.post("/access-log", json={"tipo": "visitante", "autorizado_por": "nadie"}).status_code == 422
    assert client.post("/access-log", json={"tipo": "visitante", "acompanantes": -1}).status_code == 422


def test_un_reintento_de_sync_con_otro_nombre_es_conflicto(client):
    cid = str(uuid.uuid4())
    base = {"tipo": "visitante", "client_id": cid, "nombre_visitante": "Ana"}
    assert client.post("/access-log", json=base).status_code == 201
    assert client.post("/access-log", json=base).status_code == 201  # replay idéntico
    assert client.post("/access-log", json={**base, "nombre_visitante": "Beto"}).status_code == 409


def test_los_cajones_de_visitas_libres_descuentan_los_vehiculos_que_siguen_adentro(client):
    client.patch("/tenant/reglamento", json={"cajones_visitas": 7})
    assert client.get("/access-log/estacionamiento-visitas").json()["libres"] == 7

    a = client.post("/access-log", json={"tipo": "visitante", "placas": ["AAA111"]}).json()
    client.post("/access-log", json={"tipo": "proveedor", "placas": ["BBB222"]})
    client.post("/access-log", json={"tipo": "visitante"})  # a pie: no ocupa cajón
    client.post("/access-log", json={"tipo": "residente", "placas": ["RES001"]})  # residente: tampoco

    estado = client.get("/access-log/estacionamiento-visitas").json()
    assert (estado["total_cajones"], estado["ocupados"], estado["libres"]) == (7, 2, 5)

    client.post(f"/access-log/{a['id']}/exit")
    assert client.get("/access-log/estacionamiento-visitas").json()["libres"] == 6


def test_sin_cajones_configurados_no_hay_libres_ni_error(client):
    client.post("/access-log", json={"tipo": "visitante", "placas": ["AAA111"]})
    estado = client.get("/access-log/estacionamiento-visitas").json()
    assert (estado["total_cajones"], estado["libres"]) == (0, 0)


# ---------- Incidencias de caseta (Art. 17 V.2) ----------


def test_la_caseta_levanta_una_incidencia_de_mantenimiento_con_casa_y_persona(client):
    prop = _vivienda(client)
    respuesta = client.post(
        "/incidents",
        json={"descripcion": "Luminaria fundida", "tipo": "mantenimiento", "property_id": prop, "persona_involucrada": "Vecino"},
    )
    assert respuesta.status_code == 201
    creada = respuesta.json()
    assert (creada["tipo"], creada["property_id"], creada["persona_involucrada"]) == ("mantenimiento", prop, "Vecino")

    client.post("/incidents", json={"descripcion": "Ruido"})  # tipo por omisión: seguridad
    assert [i["tipo"] for i in client.get("/incidents", params={"tipo": "mantenimiento"}).json()] == ["mantenimiento"]
    assert len(client.get("/incidents", params={"property_id": prop}).json()) == 1


def test_una_incidencia_sin_tipo_sigue_siendo_de_seguridad(client):
    assert client.post("/incidents", json={"descripcion": "Extraño en la puerta"}).json()["tipo"] == "seguridad"


def test_una_incidencia_rechaza_tipo_invalido_o_vivienda_inexistente(client):
    assert client.post("/incidents", json={"descripcion": "x", "tipo": "chisme"}).status_code == 422
    assert client.post("/incidents", json={"descripcion": "x", "property_id": str(uuid.uuid4())}).status_code == 404


# ---------- Estatus de cobranza (quién pagó, quién falta, quién es moroso) ----------


def test_el_estatus_de_cobranza_separa_morosos_pendientes_y_al_corriente(client):
    client.patch("/tenant/reglamento", json={"acepta_pago_efectivo": True})
    moroso, pagada, sin_cargos = (_vivienda(client, n) for n in ("Casa 1", "Casa 2", "Casa 3"))
    client.post("/fees", json={"monto": 750, "periodicidad": "mensual", "activa_desde": "2020-01-01"})
    client.post("/fees/generate-charges", params={"periodo": "2020-01-01"})
    # una vivienda futura queda con cargo dentro de plazo (mes siguiente)
    proximo = (hoy_local().replace(day=1) + timedelta(days=32)).replace(day=1)
    client.post("/fees/generate-charges", params={"periodo": proximo.isoformat()})
    client.post("/payments/manual", json={"property_id": pagada, "monto": 750})  # paga el más antiguo

    estatus = client.get("/reports/collection-status").json()
    por_casa = {v["identificador"]: v for v in estatus["viviendas"]}
    assert por_casa["Casa 1"]["estatus"] == "moroso" and por_casa["Casa 1"]["cargos_vencidos"] >= 1
    assert estatus["morosas"] >= 1 and estatus["total_viviendas"] == 3
    assert estatus["al_corriente"] + estatus["pendientes"] + estatus["morosas"] == 3
    assert estatus["viviendas"][0]["estatus"] == "moroso"  # los morosos van primero
    assert moroso and sin_cargos


def test_una_vivienda_sin_cargos_esta_al_corriente(client):
    _vivienda(client)
    estatus = client.get("/reports/collection-status").json()
    assert estatus["al_corriente"] == 1 and estatus["viviendas"][0]["periodo_pagado"] is None


def test_el_estatus_de_cobranza_es_solo_para_tesoreria(client):
    _como("residente", property_id=str(uuid.uuid4()))
    assert client.get("/reports/collection-status").status_code == 403


# ---------- Constancia de no adeudo (Art. 16) ----------


def test_constancia_de_no_adeudo_solo_si_la_vivienda_esta_al_corriente(client):
    client.patch("/tenant/reglamento", json={"acepta_pago_efectivo": True})
    (prop,) = _con_cuota_vencida(client, "Casa 1")

    rechazada = client.get(f"/reports/no-debt-certificate/{prop}")
    assert rechazada.status_code == 409

    deuda = client.get(f"/properties/{prop}/statement").json()["deuda_total"]
    client.post("/payments/manual", json={"property_id": prop, "monto": deuda})
    emitida = client.get(f"/reports/no-debt-certificate/{prop}")
    assert emitida.status_code == 200
    assert emitida.headers["content-type"] == "application/pdf"
    assert emitida.content.startswith(b"%PDF")


def test_constancia_de_una_vivienda_inexistente_es_404(client):
    assert client.get(f"/reports/no-debt-certificate/{uuid.uuid4()}").status_code == 404
