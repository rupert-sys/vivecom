"""
F1-10 / HU-A06: panel del tesorero. Un pago con referencia_recibida que no
coincidió con ninguna vivienda queda "pendiente" (property_id=None). El
tesorero lo ve en la lista y lo resuelve a mano: lo asigna a la vivienda
correcta (y se concilia igual que un pago automático) o lo rechaza.
"""

import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.models.fee_charge import FeeCharge
from app.services import deposit_processing_service as dps
from app.services.payment_providers.base import DepositoRecibido


@pytest.fixture()
def deposit_env(client):
    @asynccontextmanager
    async def fake_tenant_session(schema_name):
        async with client.db_session_factory() as session:
            yield session

    @asynccontextmanager
    async def fake_control_session():
        async with client.db_session_factory() as session:
            yield session

    with patch.object(dps, "tenant_session", fake_tenant_session):
        yield fake_control_session


def _deposito(referencia="9999999", clave="STP-001", monto=1500.00):
    return DepositoRecibido(
        monto=monto,
        referencia_numerica=referencia,
        clave_rastreo=clave,
        fecha=datetime(2026, 9, 15, 10, 0, 0),
        cuenta_beneficiaria="012180001547896321",
    )


@pytest.mark.asyncio
async def test_list_payments_shows_pending_case(client, deposit_env):
    client.get("/tenant/clabe")  # fuerza la creación perezosa de las tablas (ver test_deposit_processing.py)

    async with deposit_env() as control_db:
        await dps.process_incoming_deposit(_deposito(), control_db)

    response = client.get("/payments")
    assert response.status_code == 200
    [pago] = response.json()
    assert pago["estado"] == "pendiente"
    assert pago["property_id"] is None


@pytest.mark.asyncio
async def test_list_payments_filters_by_estado(client, deposit_env):
    client.post("/properties", json={"identificador": "Casa 1"})  # referencia 0000001

    async with deposit_env() as control_db:
        await dps.process_incoming_deposit(_deposito(clave="STP-001"), control_db)
        await dps.process_incoming_deposit(_deposito(referencia="0000001", clave="STP-002"), control_db)

    pendientes = client.get("/payments", params={"estado": "pendiente"}).json()
    assert len(pendientes) == 1
    assert pendientes[0]["clave_rastreo"] == "STP-001"


@pytest.mark.asyncio
async def test_resolve_pending_payment_assigns_property_and_reconciles(client, deposit_env):
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()
    client.post("/fees", json={"monto": 1500.00, "periodicidad": "mensual", "activa_desde": "2026-09-01"})
    client.post("/fees/generate-charges", params={"periodo": "2026-09-01"})

    async with deposit_env() as control_db:
        payment = await dps.process_incoming_deposit(_deposito(monto=1500.00), control_db)

    response = client.post(f"/payments/{payment.id}/resolve", json={"property_id": prop["id"]})
    assert response.status_code == 200
    body = response.json()
    assert body["estado"] == "confirmado"
    assert body["property_id"] == prop["id"]

    async with client.db_session_factory() as db:
        cargo = (await db.execute(select(FeeCharge))).scalar_one()
    assert cargo.estado.value == "pagado"
    assert cargo.payment_id == payment.id


@pytest.mark.asyncio
async def test_resolve_already_confirmed_payment_fails(client, deposit_env):
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()

    async with deposit_env() as control_db:
        payment = await dps.process_incoming_deposit(_deposito(referencia="0000001"), control_db)

    response = client.post(f"/payments/{payment.id}/resolve", json={"property_id": prop["id"]})
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_resolve_with_unknown_property_fails(client, deposit_env):
    client.get("/tenant/clabe")

    async with deposit_env() as control_db:
        payment = await dps.process_incoming_deposit(_deposito(), control_db)

    response = client.post(f"/payments/{payment.id}/resolve", json={"property_id": str(uuid.uuid4())})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_reject_pending_payment(client, deposit_env):
    client.get("/tenant/clabe")

    async with deposit_env() as control_db:
        payment = await dps.process_incoming_deposit(_deposito(), control_db)

    response = client.post(f"/payments/{payment.id}/reject")
    assert response.status_code == 200
    assert response.json()["estado"] == "rechazado"


@pytest.mark.asyncio
async def test_reject_already_confirmed_payment_fails(client, deposit_env):
    client.post("/properties", json={"identificador": "Casa 1"})

    async with deposit_env() as control_db:
        payment = await dps.process_incoming_deposit(_deposito(referencia="0000001"), control_db)

    response = client.post(f"/payments/{payment.id}/reject")
    assert response.status_code == 409
