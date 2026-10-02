"""
F1-21: dashboard financiero (cobrado vs. pendiente, filtrable por vivienda y
periodo). GET /reports/collections-summary agrega FeeCharge con una sola
consulta agrupada — antes no existía ningún endpoint que sumara cobrado/
pendiente entre viviendas (F1-14 es por-vivienda, F1-17 solo exporta filas
crudas a Excel).
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.api.deps import get_current_user
from app.main import app
from app.models.fee_charge import EstadoCargo, FeeCharge
from app.schemas.auth import CurrentUser


def _tenant_id() -> str:
    return app.dependency_overrides[get_current_user]().tenant_id


def _como(rol: str, property_id: str | None = None):
    tenant_id = _tenant_id()

    def override():
        return CurrentUser(user_id=str(uuid.uuid4()), tenant_id=tenant_id, schema_name="test", rol=rol, property_id=property_id)

    app.dependency_overrides[get_current_user] = override


def _setup_dos_viviendas_con_cargos(client):
    casa1 = client.post("/properties", json={"identificador": "Casa 1"}).json()
    casa2 = client.post("/properties", json={"identificador": "Casa 2"}).json()
    _como("tesorero")  # F0-12: cuotas y cargos son de tesorería, no del administrador
    client.post("/fees", json={"monto": 1500.00, "periodicidad": "mensual", "activa_desde": "2026-09-01"})
    client.post("/fees/generate-charges", params={"periodo": "2026-09-01"})
    return casa1, casa2


async def _marcar_pagado(client, property_id: str):
    async with client.db_session_factory() as db:
        cargo = (
            await db.execute(select(FeeCharge).where(FeeCharge.property_id == uuid.UUID(property_id)))
        ).scalar_one()
        cargo.estado = EstadoCargo.pagado
        await db.commit()


@pytest.mark.asyncio
async def test_summary_splits_cobrado_y_pendiente_entre_viviendas(client):
    casa1, casa2 = _setup_dos_viviendas_con_cargos(client)
    await _marcar_pagado(client, casa1["id"])

    response = client.get("/reports/collections-summary")
    assert response.status_code == 200
    body = response.json()

    assert body["cobrado_total"] == 1500.00
    assert body["pendiente_total"] == 1500.00
    por_id = {fila["property_id"]: fila for fila in body["por_vivienda"]}
    assert por_id[casa1["id"]]["cobrado"] == 1500.00
    assert por_id[casa1["id"]]["pendiente"] == 0.00
    assert por_id[casa2["id"]]["cobrado"] == 0.00
    assert por_id[casa2["id"]]["pendiente"] == 1500.00


@pytest.mark.asyncio
async def test_summary_filtra_por_vivienda(client):
    casa1, casa2 = _setup_dos_viviendas_con_cargos(client)
    await _marcar_pagado(client, casa1["id"])

    response = client.get("/reports/collections-summary", params={"property_id": casa2["id"]})
    body = response.json()

    assert len(body["por_vivienda"]) == 1
    assert body["por_vivienda"][0]["property_id"] == casa2["id"]
    assert body["cobrado_total"] == 0.00
    assert body["pendiente_total"] == 1500.00


def test_summary_filtra_por_periodo(client):
    _setup_dos_viviendas_con_cargos(client)
    client.post("/fees/generate-charges", params={"periodo": "2026-10-01"})

    respuesta_septiembre = client.get("/reports/collections-summary", params={"periodo": "2026-09-01"})
    respuesta_octubre = client.get("/reports/collections-summary", params={"periodo": "2026-10-01"})

    # 2 viviendas x $1500 pendientes en cada periodo por separado, nunca sumados.
    assert respuesta_septiembre.json()["pendiente_total"] == 3000.00
    assert respuesta_octubre.json()["pendiente_total"] == 3000.00


def test_summary_sin_cargos_regresa_ceros(client):
    client.post("/properties", json={"identificador": "Casa 1"})

    response = client.get("/reports/collections-summary")
    body = response.json()

    assert body["cobrado_total"] == 0.00
    assert body["pendiente_total"] == 0.00
    assert body["por_vivienda"] == []


def test_summary_requiere_rol_tesorero_o_admin(client):
    _como("guardia")
    response = client.get("/reports/collections-summary")
    assert response.status_code == 403


def _por_concepto(body, concepto: str) -> dict:
    return next(fila for fila in body["por_origen"] if fila["concepto"] == concepto)


def test_por_origen_separa_mantenimiento_de_proyecto(client):
    casa1 = client.post("/properties", json={"identificador": "Casa 1"}).json()
    _como("tesorero")
    client.post("/fees", json={"monto": 1500.00, "periodicidad": "mensual", "activa_desde": "2026-09-01"})
    client.post("/fees", json={"monto": 5000.00, "periodicidad": "unica", "activa_desde": "2026-09-01"})
    client.post("/fees/generate-charges", params={"periodo": "2026-09-01"})

    response = client.get("/reports/collections-summary", params={"periodo": "2026-09-01"})
    body = response.json()

    mantenimiento = _por_concepto(body, "Mantenimiento")
    proyecto = _por_concepto(body, "Proyecto")
    amenidades = _por_concepto(body, "Amenidades")
    assert (mantenimiento["cobrado"], mantenimiento["pendiente"]) == (0.0, 1500.0)
    assert (proyecto["cobrado"], proyecto["pendiente"]) == (0.0, 5000.0)
    assert (amenidades["cobrado"], amenidades["pendiente"]) == (0.0, 0.0)  # sin ninguna reservación
    assert casa1["identificador"] == "Casa 1"


def test_por_origen_incluye_la_cuota_de_amenidades_pagada_y_pendiente(client):
    casa1 = client.post("/properties", json={"identificador": "Casa 1"}).json()
    _como("admin")
    amenidad = client.post("/amenities", json={"nombre": "Salón", "periodo_limite_horas": 24, "cuota": 300}).json()
    _como("residente", property_id=casa1["id"])
    inicio = (datetime.now(timezone.utc) + timedelta(days=5)).replace(tzinfo=None, microsecond=0)
    reserva_pagada = client.post(
        "/reservations",
        json={"amenity_id": amenidad["id"], "fecha_inicio": inicio.isoformat(), "fecha_fin": (inicio + timedelta(hours=1)).isoformat()},
    ).json()
    reserva_pendiente = client.post(
        "/reservations",
        json={
            "amenity_id": amenidad["id"],
            "fecha_inicio": (inicio + timedelta(hours=2)).isoformat(),
            "fecha_fin": (inicio + timedelta(hours=3)).isoformat(),
        },
    ).json()
    _como("tesorero")
    client.post(f"/reservations/{reserva_pagada['id']}/cuota-pagada")

    response = client.get("/reports/collections-summary")
    amenidades = _por_concepto(response.json(), "Amenidades")

    assert amenidades["cobrado"] == 300.0
    assert amenidades["pendiente"] == 300.0
    assert reserva_pendiente["estado"] == "pendiente"


def test_por_origen_siempre_trae_los_3_conceptos_aunque_esten_en_cero(client):
    client.post("/properties", json={"identificador": "Casa 1"})

    response = client.get("/reports/collections-summary")
    conceptos = {fila["concepto"] for fila in response.json()["por_origen"]}

    assert conceptos == {"Mantenimiento", "Amenidades", "Proyecto"}
