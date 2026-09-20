"""
Acuerdos de pago (prórroga de cuotas): el condómino la solicita por escrito, el comité la acuerda y el sistema le
da seguimiento (reglamento de Arequipa, Art. 1 VIII y Art. 9 VII). Mientras se cumple, la vivienda no cuenta como
morosa (conserva voto y áreas comunes) y, si el comité lo decide, su recargo se congela; si se incumple, vuelve a mora.
"""

import uuid
from datetime import date, datetime, timedelta, timezone

import pytest

from app.api.deps import get_current_user
from app.models.payment import EstadoPago, Payment
from app.models.payment_agreement import PaymentAgreement
from app.main import app
from app.schemas.auth import CurrentUser
from app.services.payment_agreement_service import (
    abonado_al_acuerdo, construir_calendario, evaluar, procesar_acuerdos, proximo_pago, sumar_meses, validar_calendario,
)
from app.services.reglamento_service import hoy_local

CAUSA = "Perdí mi empleo en agosto y hasta ahora regularizo mis ingresos."


def _como(rol: str, property_id: str | None = None, user_id: str | None = None) -> str:
    tenant_id = app.dependency_overrides[get_current_user]().tenant_id
    uid = user_id or str(uuid.uuid4())

    def override():
        return CurrentUser(user_id=uid, tenant_id=tenant_id, schema_name="test", rol=rol, property_id=property_id)

    app.dependency_overrides[get_current_user] = override
    return uid


def _mes(meses_atras: int) -> date:
    indice = hoy_local().year * 12 + hoy_local().month - 1 - meses_atras
    return date(indice // 12, indice % 12 + 1, 1)


def _vivienda_con_deuda(client, nombre="Casa 1", meses_atras=2):
    """Una vivienda con una cuota de $750 vencida (de hace `meses_atras` meses) y el reglamento con el efectivo activo."""
    prop = client.post("/properties", json={"identificador": nombre}).json()["id"]
    if not client.get("/fees").json():
        client.post("/fees", json={"monto": 750, "periodicidad": "mensual", "activa_desde": "2020-01-01"})
    client.patch("/tenant/reglamento", json={"acepta_pago_efectivo": True, "morosos_sin_voto": True, "morosos_sin_areas_comunes": True})
    client.post("/fees/generate-charges", params={"periodo": _mes(meses_atras).isoformat()})
    return prop


def _solicitar(client, prop, pagos=3, dias=10, causa=CAUSA, **extra):
    _como("residente", property_id=prop)
    return client.post("/payment-agreements", json={
        "causa": causa, "numero_de_pagos": pagos, "primer_pago": (hoy_local() + timedelta(days=dias)).isoformat(), **extra,
    })


def _aprobar(client, agreement_id, rol="comite_aprobador", **cuerpo):
    _como(rol)
    return client.post(f"/payment-agreements/{agreement_id}/approve", json=cuerpo)


def _acuerdo_vigente(client, prop, pagos=3, **cuerpo):
    return _aprobar(client, _solicitar(client, prop, pagos).json()["id"], **cuerpo).json()


def _estado(client, prop):
    _como("residente", property_id=prop)
    return client.get(f"/properties/{prop}/statement").json()


def _efectivo(client, prop, monto):
    _como("tesorero")
    return client.post("/payments/manual", json={"property_id": prop, "monto": monto, "metodo": "efectivo"})


# ---------- Reglas puras ----------


def test_el_calendario_se_reparte_al_centavo_y_el_ultimo_pago_absorbe_el_redondeo():
    calendario = construir_calendario(1000.0, 3, date(2026, 10, 5))
    assert [p["monto"] for p in calendario] == [333.33, 333.33, 333.34]
    assert [p["fecha"] for p in calendario] == ["2026-10-05", "2026-11-05", "2026-12-05"]
    assert round(sum(p["monto"] for p in calendario), 2) == 1000.0


def test_sumar_meses_conserva_el_dia_o_usa_el_ultimo_del_mes():
    assert sumar_meses(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert sumar_meses(date(2026, 11, 30), 3) == date(2027, 2, 28)
    assert sumar_meses(date(2026, 10, 5), 12) == date(2027, 10, 5)


@pytest.mark.parametrize(
    "abonado,pendiente,hoy,esperado",
    [
        (0, 750, date(2026, 10, 1), "vigente"),  # todavía no vence ningún pago
        (0, 750, date(2026, 10, 5), "vigente"),  # el día del pago aún cuenta como a tiempo
        (0, 750, date(2026, 10, 6), "incumplido"),  # pasó el primer pago sin abonar
        (250, 500, date(2026, 10, 6), "vigente"),  # cubrió el primero
        (250, 500, date(2026, 11, 6), "incumplido"),  # pasó el segundo y solo lleva un pago
        (500, 250, date(2026, 11, 6), "vigente"),  # va al corriente con el calendario
        (500, 250, date(2026, 12, 6), "incumplido"),  # el último pago exige liquidar todo
        (0, 0, date(2027, 6, 1), "cumplido"),  # liquidó antes o después: cumplido
        (750, 0.004, date(2026, 12, 6), "cumplido"),  # tolerancia de centavos
    ],
)
def test_evaluar_cumplimiento_del_calendario(abonado, pendiente, hoy, esperado):
    calendario = [{"fecha": "2026-10-05", "monto": 250}, {"fecha": "2026-11-05", "monto": 250}, {"fecha": "2026-12-05", "monto": 250}]
    assert evaluar(calendario, abonado, pendiente, hoy) == esperado


def test_el_proximo_pago_dice_cuanto_falta_para_cuando():
    calendario = [{"fecha": "2026-10-05", "monto": 250}, {"fecha": "2026-11-05", "monto": 250}]
    assert proximo_pago(calendario, 0, date(2026, 9, 1)) == {"fecha": "2026-10-05", "monto": 250.0}
    assert proximo_pago(calendario, 300, date(2026, 9, 1)) == {"fecha": "2026-11-05", "monto": 200.0}
    assert proximo_pago(calendario, 500, date(2026, 9, 1)) is None


def test_validar_calendario_rechaza_lo_que_no_cuadra():
    hoy = date(2026, 9, 1)
    ok = [{"fecha": "2026-10-01", "monto": 400.0}, {"fecha": "2026-11-01", "monto": 350.0}]
    assert validar_calendario(ok, 750.0, hoy, 3) is None
    assert "sumar" in validar_calendario(ok, 800.0, hoy, 3)
    assert "orden" in validar_calendario(list(reversed(ok)), 750.0, hoy, 3)
    assert "posterior" in validar_calendario([{"fecha": "2026-09-01", "monto": 750.0}], 750.0, hoy, 3)
    assert "3 meses" in validar_calendario([{"fecha": "2027-02-01", "monto": 750.0}], 750.0, hoy, 3)
    assert "de 1 a 6" in validar_calendario([], 750.0, hoy, 3)


# ---------- Solicitar ----------


def test_el_residente_solicita_un_acuerdo_y_no_cambia_nada_hasta_que_se_apruebe(client):
    prop = _vivienda_con_deuda(client)
    respuesta = _solicitar(client, prop)

    assert respuesta.status_code == 201
    acuerdo = respuesta.json()
    assert (acuerdo["estado"], acuerdo["vivienda"], acuerdo["capturado_por_admin"], acuerdo["calendario"]) == ("solicitado", "Casa 1", False, None)
    estado = _estado(client, prop)
    assert estado["en_mora"] is True and estado["en_acuerdo"] is False  # una solicitud pendiente no suspende la mora


def test_validaciones_de_la_solicitud(client):
    prop = _vivienda_con_deuda(client)
    assert _solicitar(client, prop, causa="Ya no puedo").status_code == 422  # la causa debe ser justificada (≥ 20)
    assert _solicitar(client, prop, dias=0).status_code == 422  # el primer pago debe ser futuro
    lejos = _solicitar(client, prop, pagos=6, dias=1)  # 6 pagos mensuales exceden los 3 meses del reglamento
    assert lejos.status_code == 422 and "3 meses" in lejos.json()["detail"]
    assert _solicitar(client, prop, pagos=7).status_code == 422
    assert _solicitar(client, prop).status_code == 201
    assert _solicitar(client, prop).status_code == 409  # solo un acuerdo abierto por vivienda


def test_sin_adeudo_no_hay_nada_que_acordar(client):
    prop = client.post("/properties", json={"identificador": "Casa 9"}).json()["id"]
    assert _solicitar(client, prop).status_code == 409


def test_el_plazo_maximo_sale_del_reglamento(client):
    prop = _vivienda_con_deuda(client)
    client.patch("/tenant/reglamento", json={"prorroga_max_meses": 6})
    assert _solicitar(client, prop, pagos=6, dias=1).status_code == 201


def test_el_administrador_captura_el_escrito_de_un_vecino_pero_un_residente_no_lo_hace_por_otro(client):
    prop = _vivienda_con_deuda(client)
    _como("admin")
    capturado = client.post("/payment-agreements", json={
        "property_id": prop, "causa": CAUSA, "numero_de_pagos": 2, "primer_pago": (hoy_local() + timedelta(days=5)).isoformat()})
    assert capturado.status_code == 201 and capturado.json()["capturado_por_admin"] is True
    _como("guardia")
    assert client.post("/payment-agreements", json={"causa": CAUSA, "numero_de_pagos": 1, "primer_pago": (hoy_local() + timedelta(days=5)).isoformat()}).status_code == 400


def test_el_documento_de_respaldo_es_propio_y_lo_ve_quien_decide(client):
    prop = _vivienda_con_deuda(client)
    otra = _vivienda_con_deuda(client, "Casa 2")
    _como("residente", property_id=prop)
    archivo = client.post("/files", files={"file": ("carta.pdf", b"%PDF-1.7\n" + b"0" * 50, "application/pdf")}, data={"kind": "acuerdo"}).json()
    solicitud = client.post("/payment-agreements", json={
        "causa": CAUSA, "numero_de_pagos": 1, "primer_pago": (hoy_local() + timedelta(days=5)).isoformat(), "archivo_id": archivo["id"]})
    assert solicitud.status_code == 201 and "/content?t=" in solicitud.json()["archivo_url"]

    for rol, esperado in (("comite_aprobador", 200), ("comite_lectura", 200), ("admin", 200), ("tesorero", 200), ("guardia", 404)):
        _como(rol)
        assert client.get(f"/files/{archivo['id']}/link").status_code == esperado, rol
    _como("residente", property_id=otra)
    assert client.get(f"/files/{archivo['id']}/link").status_code == 404  # otro vecino no lo ve
    ajeno = client.post("/payment-agreements", json={
        "causa": CAUSA, "numero_de_pagos": 1, "primer_pago": (hoy_local() + timedelta(days=5)).isoformat(),
        "archivo_id": archivo["id"]})
    assert ajeno.status_code == 422 and "no es tuyo" in ajeno.json()["detail"]  # ni puede adjuntarlo a su solicitud


# ---------- Decidir ----------


def test_solo_el_comite_aprobador_y_el_administrador_deciden(client):
    prop = _vivienda_con_deuda(client)
    acuerdo = _solicitar(client, prop).json()["id"]
    for rol in ("residente", "comite_lectura", "tesorero", "guardia"):
        assert _aprobar(client, acuerdo, rol).status_code == 403, rol
        assert client.post(f"/payment-agreements/{acuerdo}/reject", json={"motivo": "x"}).status_code == 403, rol
    assert _aprobar(client, acuerdo, "comite_aprobador").status_code == 200


def test_al_aprobar_se_fija_el_calendario_y_la_vivienda_deja_de_ser_morosa(client):
    prop = _vivienda_con_deuda(client)
    aprobado = _acuerdo_vigente(client, prop, pagos=3)

    assert aprobado["estado"] == "vigente" and aprobado["deuda_inicial"] == 750.0 and aprobado["congela_recargo"] is True
    assert [p["monto"] for p in aprobado["calendario"]] == [250.0, 250.0, 250.0]
    assert aprobado["proximo_pago"]["monto"] == 250.0 and aprobado["abonado"] == 0.0 and aprobado["pendiente_cubierto"] == 750.0
    estado = _estado(client, prop)
    assert (estado["en_mora"], estado["en_acuerdo"], estado["deuda_total"]) == (False, True, 750.0)  # sigue debiendo
    assert estado["restricciones_por_mora"] == []


def test_con_un_acuerdo_vigente_conserva_voto_y_areas_comunes(client):
    prop = _vivienda_con_deuda(client)
    _como("vocero")
    poll = client.post("/polls", json={"pregunta": "¿Portón?", "opciones": ["Sí", "No"], "fecha_cierre": "2099-12-31"}).json()
    _como("admin")
    area = client.post("/amenities", json={"nombre": "Salón", "periodo_limite_horas": 24}).json()
    inicio = (datetime.now(timezone.utc) + timedelta(days=3)).replace(microsecond=0)
    reserva = {"amenity_id": area["id"], "fecha_inicio": inicio.isoformat(), "fecha_fin": (inicio + timedelta(hours=2)).isoformat()}

    _como("residente", property_id=prop)
    voto = {"option_id": poll["opciones"][0]["id"]}
    assert client.post(f"/polls/{poll['id']}/vote", json=voto).status_code == 403  # moroso: sin voto
    assert client.post("/reservations", json=reserva).status_code == 403  # y sin áreas comunes

    _acuerdo_vigente(client, prop)
    _como("residente", property_id=prop)
    assert client.post(f"/polls/{poll['id']}/vote", json=voto).status_code == 204
    assert client.post("/reservations", json=reserva).status_code == 201


def test_la_cobranza_distingue_con_acuerdo_de_moroso(client):
    con = _vivienda_con_deuda(client, "Casa 1")
    _vivienda_con_deuda(client, "Casa 2")
    _acuerdo_vigente(client, con)

    _como("tesorero")
    cobranza = client.get("/reports/collection-status").json()
    estatus = {v["identificador"]: v["estatus"] for v in cobranza["viviendas"]}
    assert estatus == {"Casa 1": "con_acuerdo", "Casa 2": "moroso"}
    assert (cobranza["con_acuerdo"], cobranza["morosas"]) == (1, 1)
    assert cobranza["viviendas"][0]["estatus"] == "moroso"  # los morosos primero, luego los que tienen acuerdo


def test_con_acuerdo_no_se_emite_constancia_de_no_adeudo(client):
    prop = _vivienda_con_deuda(client)
    _acuerdo_vigente(client, prop)
    _como("tesorero")
    assert client.get(f"/reports/no-debt-certificate/{prop}").status_code == 409  # todavía debe


def test_el_comite_aprueba_con_un_calendario_propio_que_debe_sumar_la_deuda(client):
    prop = _vivienda_con_deuda(client)
    acuerdo = _solicitar(client, prop).json()["id"]
    f = lambda d: (hoy_local() + timedelta(days=d)).isoformat()  # noqa: E731

    assert _aprobar(client, acuerdo, pagos=[{"fecha": f(10), "monto": 100}]).status_code == 422  # no suma $750
    assert _aprobar(client, acuerdo, pagos=[{"fecha": f(20), "monto": 400}, {"fecha": f(10), "monto": 350}]).status_code == 422  # desordenado
    propio = _aprobar(client, acuerdo, pagos=[{"fecha": f(10), "monto": 500}, {"fecha": f(40), "monto": 250}])
    assert propio.status_code == 200 and [p["monto"] for p in propio.json()["calendario"]] == [500.0, 250.0]


def test_un_acuerdo_se_resuelve_una_sola_vez(client):
    prop = _vivienda_con_deuda(client)
    acuerdo = _solicitar(client, prop).json()["id"]
    assert _aprobar(client, acuerdo).status_code == 200
    assert _aprobar(client, acuerdo).status_code == 409
    assert client.post(f"/payment-agreements/{acuerdo}/reject", json={"motivo": "tarde"}).status_code == 409
    assert _aprobar(client, str(uuid.uuid4())).status_code == 404


def test_rechazar_pide_motivo_y_no_cambia_la_mora(client):
    prop = _vivienda_con_deuda(client)
    acuerdo = _solicitar(client, prop).json()["id"]
    _como("comite_aprobador")
    assert client.post(f"/payment-agreements/{acuerdo}/reject", json={"motivo": ""}).status_code == 422
    rechazado = client.post(f"/payment-agreements/{acuerdo}/reject", json={"motivo": "No se acreditó la causa"})
    assert rechazado.status_code == 200 and rechazado.json()["estado"] == "rechazado"
    assert _estado(client, prop)["en_mora"] is True
    _como("residente", property_id=prop)
    visto = client.get("/payment-agreements").json()[0]
    assert (visto["estado"], visto["motivo_rechazo"]) == ("rechazado", "No se acreditó la causa")
    assert _solicitar(client, prop).status_code == 201  # puede volver a solicitar


@pytest.mark.asyncio
async def test_aprobar_con_una_fecha_propuesta_que_ya_paso_pide_un_calendario_nuevo(client):
    from app.models.payment_agreement import PaymentAgreement

    prop = _vivienda_con_deuda(client)
    acuerdo = _solicitar(client, prop).json()["id"]
    async with client.db_session_factory() as db:  # el comité tardó: la fecha propuesta ya pasó
        fila = await db.get(PaymentAgreement, uuid.UUID(acuerdo))
        fila.propuesta_primer_pago = hoy_local() - timedelta(days=1)
        await db.commit()

    respuesta = _aprobar(client, acuerdo)
    assert respuesta.status_code == 422 and "calendario nuevo" in respuesta.json()["detail"]


# ---------- Cancelar ----------


def test_el_residente_retira_su_solicitud_pero_no_cancela_un_acuerdo_vigente(client):
    prop = _vivienda_con_deuda(client)
    pendiente = _solicitar(client, prop).json()["id"]
    assert client.post(f"/payment-agreements/{pendiente}/cancel").json()["estado"] == "cancelado"

    vigente = _acuerdo_vigente(client, prop)
    _como("residente", property_id=prop)
    assert client.post(f"/payment-agreements/{vigente['id']}/cancel").status_code == 403


def test_cancelar_un_acuerdo_vigente_devuelve_la_mora(client):
    prop = _vivienda_con_deuda(client)
    vigente = _acuerdo_vigente(client, prop)
    _como("tesorero")
    assert client.post(f"/payment-agreements/{vigente['id']}/cancel").status_code == 403  # tesorería no decide
    _como("comite_aprobador")
    assert client.post(f"/payment-agreements/{vigente['id']}/cancel").json()["estado"] == "cancelado"
    assert _estado(client, prop)["en_mora"] is True


# ---------- Recargo ----------


def _recargo_de(client, prop):
    _como("tesorero")
    return client.get(f"/properties/{prop}/statement").json()["cargos"][0]["recargo_aplicado"]


def test_con_el_recargo_congelado_no_crece_mientras_se_cumple(client):
    client.patch("/tenant/reglamento", json={"recargo_modalidad": "mensual_sobre_saldo", "recargo_porcentaje": 0.05})
    congelada = _vivienda_con_deuda(client, "Casa 1")
    _como("admin")
    client.post("/fees/apply-late-surcharges")  # el recargo de hoy
    inicial = _recargo_de(client, congelada)
    assert inicial > 0

    _acuerdo_vigente(client, congelada, congela_recargo=True)
    futuro = (hoy_local() + timedelta(days=65)).isoformat()
    _como("admin")
    client.post("/fees/apply-late-surcharges", params={"hoy": futuro})
    assert _recargo_de(client, congelada) == inicial  # congelado mientras el acuerdo se cumple


def test_sin_congelar_el_recargo_sigue_corriendo(client):
    client.patch("/tenant/reglamento", json={"recargo_modalidad": "mensual_sobre_saldo", "recargo_porcentaje": 0.05})
    prop = _vivienda_con_deuda(client)
    _como("admin")
    client.post("/fees/apply-late-surcharges")
    inicial = _recargo_de(client, prop)
    _acuerdo_vigente(client, prop, congela_recargo=False)
    _como("admin")
    client.post("/fees/apply-late-surcharges", params={"hoy": (hoy_local() + timedelta(days=65)).isoformat()})
    assert _recargo_de(client, prop) > inicial


@pytest.mark.asyncio
async def test_al_incumplirse_el_recargo_vuelve_a_correr(client):
    client.patch("/tenant/reglamento", json={"recargo_modalidad": "mensual_sobre_saldo", "recargo_porcentaje": 0.05})
    prop = _vivienda_con_deuda(client)
    _como("admin")
    client.post("/fees/apply-late-surcharges")
    inicial = _recargo_de(client, prop)
    _acuerdo_vigente(client, prop, pagos=1)

    futuro = hoy_local() + timedelta(days=65)
    async with client.db_session_factory() as db:
        assert (await procesar_acuerdos(db, futuro)) == {"cumplidos": 0, "incumplidos": 1}
    _como("admin")
    client.post("/fees/apply-late-surcharges", params={"hoy": futuro.isoformat()})
    assert _recargo_de(client, prop) > inicial  # ya no está congelado
    assert _estado(client, prop)["en_mora"] is True


@pytest.mark.asyncio
async def test_un_spei_con_fecha_del_banco_anterior_a_la_aprobacion_si_abona_al_acuerdo(client):
    """
    fecha_deteccion de un SPEI la pone el banco (hora local o solo el día): puede ser anterior al instante en que se
    aprobó el acuerdo aunque el depósito llegó después. Lo abonado se mide contra los pagos que ya existían, no por fecha.
    """
    prop = _vivienda_con_deuda(client)
    vigente = _acuerdo_vigente(client, prop, pagos=3)

    async with client.db_session_factory() as db:
        acuerdo = await db.get(PaymentAgreement, uuid.UUID(vigente["id"]))
        db.add(Payment(
            property_id=uuid.UUID(prop), monto=250, estado=EstadoPago.confirmado, referencia_recibida="1234567",
            clave_rastreo="SPEI-HORA-LOCAL", fecha_deteccion=acuerdo.vigente_desde - timedelta(hours=6),
        ))
        await db.commit()
        assert await abonado_al_acuerdo(db, acuerdo) == 250.0


@pytest.mark.asyncio
async def test_lo_pagado_antes_de_aprobar_no_abona_al_acuerdo(client):
    prop = _vivienda_con_deuda(client)
    _como("tesorero")
    client.post("/payments/manual", json={"property_id": prop, "monto": 100, "metodo": "efectivo"})  # antes del acuerdo
    vigente = _acuerdo_vigente(client, prop, pagos=3)
    assert vigente["abonado"] == 0.0
    async with client.db_session_factory() as db:
        assert await abonado_al_acuerdo(db, await db.get(PaymentAgreement, uuid.UUID(vigente["id"]))) == 0.0


# ---------- Seguimiento: parcialidades ----------


def test_las_parcialidades_se_juntan_en_saldo_a_favor_hasta_saldar_el_cargo(client):
    prop = _vivienda_con_deuda(client)
    _acuerdo_vigente(client, prop, pagos=3)  # 3 pagos de $250 para una cuota de $750

    _efectivo(client, prop, 250)
    _efectivo(client, prop, 250)
    e = _estado(client, prop)
    assert (e["deuda_total"], e["saldo_a_favor"]) == (750.0, 500.0)  # todavía no salda el cargo completo

    _efectivo(client, prop, 250)
    e = _estado(client, prop)
    assert (e["deuda_total"], e["saldo_a_favor"]) == (0.0, 0.0)  # el tercero completa los $750


@pytest.mark.asyncio
async def test_pagar_el_calendario_cumple_el_acuerdo_y_el_avance_se_ve(client):
    prop = _vivienda_con_deuda(client)
    vigente = _acuerdo_vigente(client, prop, pagos=3)
    _efectivo(client, prop, 250)

    _como("comite_lectura")
    avance = client.get(f"/payment-agreements/{vigente['id']}").json()
    assert (avance["abonado"], avance["pendiente_cubierto"]) == (250.0, 750.0)
    assert avance["proximo_pago"]["monto"] == 250.0  # ya cubrió el primero; falta el segundo

    _efectivo(client, prop, 250)
    _efectivo(client, prop, 250)
    async with client.db_session_factory() as db:
        assert (await procesar_acuerdos(db, hoy_local())) == {"cumplidos": 1, "incumplidos": 0}
    _como("residente", property_id=prop)
    assert client.get("/payment-agreements").json()[0]["estado"] == "cumplido"
    assert _estado(client, prop)["en_acuerdo"] is False


@pytest.mark.asyncio
async def test_se_incumple_si_vence_un_pago_sin_el_acumulado_y_la_vivienda_vuelve_a_ser_morosa(client):
    prop = _vivienda_con_deuda(client)
    _acuerdo_vigente(client, prop, pagos=3)
    primer_pago = hoy_local() + timedelta(days=10)

    async with client.db_session_factory() as db:  # antes de que venza el primer pago no pasa nada
        assert (await procesar_acuerdos(db, primer_pago)) == {"cumplidos": 0, "incumplidos": 0}
    async with client.db_session_factory() as db:
        assert (await procesar_acuerdos(db, primer_pago + timedelta(days=1))) == {"cumplidos": 0, "incumplidos": 1}

    e = _estado(client, prop)
    assert (e["en_mora"], e["en_acuerdo"]) == (True, False)
    _como("comite_aprobador")
    assert client.get("/payment-agreements").json()[0]["estado"] == "incumplido"


@pytest.mark.asyncio
async def test_quien_va_al_corriente_con_el_calendario_sigue_vigente_y_un_incumplimiento_previo_se_le_marca_al_comite(client):
    prop = _vivienda_con_deuda(client)
    _acuerdo_vigente(client, prop, pagos=3)
    _efectivo(client, prop, 250)
    async with client.db_session_factory() as db:  # venció el primer pago, pero ya lo cubrió
        assert (await procesar_acuerdos(db, hoy_local() + timedelta(days=11))) == {"cumplidos": 0, "incumplidos": 0}
    async with client.db_session_factory() as db:  # venció el segundo y solo lleva uno
        assert (await procesar_acuerdos(db, hoy_local() + timedelta(days=42)))["incumplidos"] == 1

    nuevo = _solicitar(client, prop)  # puede volver a pedir, pero el comité ve que ya incumplió uno
    assert nuevo.status_code == 201
    _como("comite_aprobador")
    assert client.get(f"/payment-agreements/{nuevo.json()['id']}").json()["incumplimientos_previos"] == 1
    _como("residente", property_id=prop)
    assert client.get(f"/payment-agreements/{nuevo.json()['id']}").json()["incumplimientos_previos"] == 0  # el vecino no lo ve


def test_pagar_la_cuota_corriente_no_se_va_a_la_deuda_del_acuerdo(client):
    prop = _vivienda_con_deuda(client)
    vigente = _acuerdo_vigente(client, prop, pagos=3)
    _como("admin")
    client.post("/fees/generate-charges", params={"periodo": _mes(0).isoformat()})  # la cuota del mes actual

    _efectivo(client, prop, 750)
    cargos = _estado(client, prop)
    _como("tesorero")
    por_periodo = {c["periodo"]: c["estado"] for c in client.get(f"/properties/{prop}/statement").json()["cargos"]}
    assert por_periodo[_mes(0).isoformat()] == "pagado"  # la corriente se pagó primero
    assert por_periodo[_mes(2).isoformat()] != "pagado"  # la deuda del acuerdo sigue
    assert cargos["en_acuerdo"] is True

    _como("comite_aprobador")
    assert client.get(f"/payment-agreements/{vigente['id']}").json()["abonado"] == 0.0  # esa plata no abonó al acuerdo


# ---------- Quién ve qué ----------


def test_cada_residente_ve_solo_sus_acuerdos_y_el_staff_todos(client):
    una = _vivienda_con_deuda(client, "Casa 1")
    otra = _vivienda_con_deuda(client, "Casa 2")
    a1 = _solicitar(client, una).json()["id"]
    _solicitar(client, otra)

    _como("residente", property_id=una)
    assert [a["id"] for a in client.get("/payment-agreements").json()] == [a1]
    _como("residente", property_id=otra)
    assert client.get(f"/payment-agreements/{a1}").status_code == 404
    for rol in ("admin", "comite_aprobador", "comite_lectura", "tesorero"):
        _como(rol)
        assert len(client.get("/payment-agreements").json()) == 2, rol
    _como("guardia")
    assert client.get("/payment-agreements").json() == []


def test_la_lista_pone_primero_las_solicitudes_pendientes(client):
    una = _vivienda_con_deuda(client, "Casa 1")
    otra = _vivienda_con_deuda(client, "Casa 2")
    _acuerdo_vigente(client, una)
    _solicitar(client, otra)
    _como("comite_aprobador")
    assert [a["estado"] for a in client.get("/payment-agreements").json()] == ["solicitado", "vigente"]
    assert [a["estado"] for a in client.get("/payment-agreements", params={"estado": "vigente"}).json()] == ["vigente"]


def test_el_seguimiento_manual_es_solo_del_administrador(client):
    _como("comite_aprobador")
    assert client.post("/payment-agreements/process").status_code == 403
    _como("admin")
    assert client.post("/payment-agreements/process").json() == {"cumplidos": 0, "incumplidos": 0}
