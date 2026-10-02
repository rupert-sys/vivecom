"""
Reglas de reservación que salen del reglamento interior del condominio
(Condominio Arequipa, modificado el 18-ene-2026, Art. 2): 8 días de
anticipación, uso hasta la 01:00 am, cuota de $1,000 por el área adoquinada,
capacidad limitada (cajones), y viviendas morosas sin acceso a áreas comunes.
"""

import uuid
from datetime import datetime, time, timedelta, timezone

from app.api.deps import get_current_user
from app.main import app
from app.schemas.auth import CurrentUser
from app.services.reglamento_service import TZ_CONDOMINIO, hoy_local


def _como(rol: str, property_id: str | None = None):
    tenant_id = app.dependency_overrides[get_current_user]().tenant_id

    def override():
        return CurrentUser(
            user_id=str(uuid.uuid4()), tenant_id=tenant_id, schema_name="test", rol=rol, property_id=property_id
        )

    app.dependency_overrides[get_current_user] = override


def _local(dias_adelante: int, hora: int, minuto: int = 0, extra_dias: int = 0) -> str:
    """ISO en UTC ('Z') de una hora LOCAL del condominio, `dias_adelante` días después de hoy."""
    dia = hoy_local() + timedelta(days=dias_adelante + extra_dias)
    local = datetime.combine(dia, time(hora, minuto), tzinfo=TZ_CONDOMINIO)
    return local.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _proximo_dia_de_la_semana(weekday: int, minimo_dias: int = 10) -> int:
    """Días a partir de hoy hasta el siguiente `weekday` (0=lunes) que esté al menos `minimo_dias` adelante."""
    d = minimo_dias
    while (hoy_local() + timedelta(days=d)).weekday() != weekday:
        d += 1
    return d


def _area_adoquinada(client, **extra):
    campos = {
        "nombre": "Área adoquinada", "periodo_limite_horas": 48, "dias_anticipacion_minimos": 8,
        "hora_fin_maxima": "01:00:00", "cuota": 1000, "notas_reglamento": "Reglamento Art. 2 III-VII",
    }
    campos.update(extra)
    return client.post("/amenities", json=campos).json()


def _vivienda(client, nombre="Casa 1") -> str:
    return client.post("/properties", json={"identificador": nombre}).json()["id"]


def _reservar(client, amenidad, prop, inicio, fin):
    _como("residente", property_id=prop)
    return client.post("/reservations", json={"amenity_id": amenidad["id"], "fecha_inicio": inicio, "fecha_fin": fin})


# ---------- Anticipación, horario y cuota (Art. 2 III, V, VI) ----------


def test_la_amenidad_expone_sus_reglas_en_lenguaje_llano(client):
    area = _area_adoquinada(client, dias_semana_permitidos=[4, 5, 6])
    assert "8 días de anticipación" in " ".join(area["reglas"])
    assert any("viernes, sábado, domingo" in r for r in area["reglas"])
    assert any("01:00" in r for r in area["reglas"])
    assert any("$1,000.00" in r for r in area["reglas"])
    assert area["dias_semana_permitidos"] == [4, 5, 6]


def test_no_se_puede_reservar_con_menos_de_8_dias_de_anticipacion(client):
    area, prop = _area_adoquinada(client), _vivienda(client)
    respuesta = _reservar(client, area, prop, _local(3, 15), _local(3, 23))
    assert respuesta.status_code == 422
    assert "8 días" in respuesta.json()["detail"]


def test_con_8_dias_o_mas_de_anticipacion_si_se_puede(client):
    area, prop = _area_adoquinada(client), _vivienda(client)
    respuesta = _reservar(client, area, prop, _local(8, 15), _local(8, 23))
    assert respuesta.status_code == 201
    assert respuesta.json()["cuota"] == 1000.0
    assert respuesta.json()["cuota_pagada"] is False


def test_el_evento_puede_terminar_a_la_1am_del_dia_siguiente_pero_no_despues(client):
    area, prop = _area_adoquinada(client), _vivienda(client)
    assert _reservar(client, area, prop, _local(10, 15), _local(10, 1, extra_dias=1)).status_code == 201

    tarde = _reservar(client, area, prop, _local(12, 15), _local(12, 2, extra_dias=1))
    assert tarde.status_code == 422
    assert "01:00" in tarde.json()["detail"]


def test_el_tesorero_marca_que_ya_recibio_la_cuota(client):
    area, prop = _area_adoquinada(client), _vivienda(client)
    reserva = _reservar(client, area, prop, _local(9, 15), _local(9, 23)).json()

    _como("residente", property_id=prop)
    assert client.post(f"/reservations/{reserva['id']}/cuota-pagada").status_code == 403

    _como("tesorero")
    pagada = client.post(f"/reservations/{reserva['id']}/cuota-pagada")
    assert pagada.status_code == 200
    assert pagada.json()["cuota_pagada"] is True


def test_una_amenidad_sin_reglas_configuradas_se_comporta_como_antes(client):
    area = client.post("/amenities", json={"nombre": "Alberca", "periodo_limite_horas": 24}).json()
    assert area["reglas"] == []
    prop = _vivienda(client)
    # reservar para mañana, sin 8 días de anticipación, sigue permitido
    assert _reservar(client, area, prop, _local(1, 10), _local(1, 12)).status_code == 201


# ---------- Días permitidos ----------


def test_una_amenidad_solo_de_lunes_a_viernes_rechaza_el_fin_de_semana(client):
    area = client.post(
        "/amenities", json={"nombre": "Sala de juntas", "periodo_limite_horas": 24, "dias_semana_permitidos": [0, 1, 2, 3, 4]}
    ).json()
    prop = _vivienda(client)

    sabado = _proximo_dia_de_la_semana(5)
    rechazada = _reservar(client, area, prop, _local(sabado, 10), _local(sabado, 12))
    assert rechazada.status_code == 422
    assert "lunes" in rechazada.json()["detail"]

    lunes = _proximo_dia_de_la_semana(0)
    assert _reservar(client, area, prop, _local(lunes, 10), _local(lunes, 12)).status_code == 201


# ---------- Capacidad (ej. cajones de estacionamiento) ----------


def test_con_capacidad_2_caben_dos_reservaciones_al_mismo_horario_y_la_tercera_no(client):
    area = client.post("/amenities", json={"nombre": "Cajones", "periodo_limite_horas": 24, "capacidad": 2}).json()
    casas = [_vivienda(client, f"Casa {i}") for i in range(3)]
    inicio, fin = _local(5, 10), _local(5, 14)

    assert _reservar(client, area, casas[0], inicio, fin).status_code == 201
    assert _reservar(client, area, casas[1], inicio, fin).status_code == 201
    tercera = _reservar(client, area, casas[2], inicio, fin)
    assert tercera.status_code == 409
    assert "ocupado" in tercera.json()["detail"]


def test_reservaciones_consecutivas_no_cuentan_como_simultaneas(client):
    area = client.post("/amenities", json={"nombre": "Cajón", "periodo_limite_horas": 24}).json()
    casas = [_vivienda(client, f"Casa {i}") for i in range(2)]
    assert _reservar(client, area, casas[0], _local(5, 10), _local(5, 12)).status_code == 201
    assert _reservar(client, area, casas[1], _local(5, 12), _local(5, 14)).status_code == 201


def test_la_disponibilidad_del_dia_dice_cuantos_lugares_quedan(client):
    area = client.post("/amenities", json={"nombre": "Cajones", "periodo_limite_horas": 24, "capacidad": 3}).json()
    casas = [_vivienda(client, f"Casa {i}") for i in range(2)]
    _reservar(client, area, casas[0], _local(5, 10), _local(5, 14))
    _reservar(client, area, casas[1], _local(5, 12), _local(5, 16))

    dia = (hoy_local() + timedelta(days=5)).isoformat()
    ocupado = client.get(f"/amenities/{area['id']}/disponibilidad", params={"fecha": dia}).json()
    assert ocupado["capacidad"] == 3
    assert ocupado["cupos_libres_todo_el_dia"] == 1  # entre las 12 y las 14 hay 2 ocupados
    assert len(ocupado["reservaciones"]) == 2

    libre = client.get(
        f"/amenities/{area['id']}/disponibilidad", params={"fecha": (hoy_local() + timedelta(days=6)).isoformat()}
    ).json()
    assert libre["cupos_libres_todo_el_dia"] == 3
    assert libre["reservaciones"] == []


# ---------- Morosos sin áreas comunes (Art. 2 VIII, Art. 21 II) ----------


def _vivienda_con_cuota_vencida(client) -> str:
    prop = _vivienda(client)
    _como("tesorero")  # F0-12: cuotas y cargos son de tesorería, no del administrador
    client.post("/fees", json={"monto": 750, "periodicidad": "mensual", "activa_desde": "2020-01-01"})
    client.post("/fees/generate-charges", params={"periodo": "2020-01-01"})
    return prop


def test_una_vivienda_con_adeudo_no_puede_reservar_areas_comunes_si_el_reglamento_lo_dice(client):
    client.patch("/tenant/reglamento", json={"morosos_sin_areas_comunes": True})
    area = client.post("/amenities", json={"nombre": "Área", "periodo_limite_horas": 24}).json()
    prop = _vivienda_con_cuota_vencida(client)

    respuesta = _reservar(client, area, prop, _local(10, 10), _local(10, 12))
    assert respuesta.status_code == 403
    assert "cuotas vencidas" in respuesta.json()["detail"]


def test_al_ponerse_al_corriente_la_vivienda_vuelve_a_poder_reservar(client):
    client.patch("/tenant/reglamento", json={"morosos_sin_areas_comunes": True, "acepta_pago_efectivo": True})
    area = client.post("/amenities", json={"nombre": "Área", "periodo_limite_horas": 24}).json()
    prop = _vivienda_con_cuota_vencida(client)
    assert _reservar(client, area, prop, _local(10, 10), _local(10, 12)).status_code == 403

    _como("tesorero")
    deuda = client.get(f"/properties/{prop}/statement").json()["deuda_total"]
    client.post("/payments/manual", json={"property_id": prop, "monto": deuda})
    assert _reservar(client, area, prop, _local(10, 10), _local(10, 12)).status_code == 201


def test_sin_la_regla_activada_un_moroso_puede_reservar_como_siempre(client):
    area = client.post("/amenities", json={"nombre": "Área", "periodo_limite_horas": 24}).json()
    prop = _vivienda_con_cuota_vencida(client)
    assert _reservar(client, area, prop, _local(10, 10), _local(10, 12)).status_code == 201


# ---------- Admin ajusta las reglas de una amenidad existente ----------


def test_el_admin_ajusta_las_reglas_de_una_amenidad_existente(client):
    area = client.post("/amenities", json={"nombre": "Área", "periodo_limite_horas": 24}).json()
    actualizada = client.patch(
        f"/amenities/{area['id']}", json={"dias_anticipacion_minimos": 8, "cuota": 1000, "dias_semana_permitidos": [5, 6]}
    )
    assert actualizada.status_code == 200
    assert actualizada.json()["dias_anticipacion_minimos"] == 8
    assert actualizada.json()["dias_semana_permitidos"] == [5, 6]
    assert client.patch(f"/amenities/{uuid.uuid4()}", json={"cuota": 1}).status_code == 404

    _como("residente", property_id=str(uuid.uuid4()))
    assert client.patch(f"/amenities/{area['id']}", json={"cuota": 1}).status_code == 403


def test_rechaza_dias_de_la_semana_invalidos(client):
    respuesta = client.post(
        "/amenities", json={"nombre": "X", "periodo_limite_horas": 1, "dias_semana_permitidos": [9]}
    )
    assert respuesta.status_code == 422


def test_el_tesorero_ve_todas_las_reservaciones_para_marcar_las_cuotas(client):
    area, prop = _area_adoquinada(client), _vivienda(client)
    _reservar(client, area, prop, _local(9, 15), _local(9, 23))

    _como("tesorero")
    assert len(client.get("/reservations").json()) == 1

    _como("guardia")  # otros roles de staff sin vivienda no ven nada
    assert client.get("/reservations").json() == []
