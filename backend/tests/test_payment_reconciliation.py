"""
F1-07: al procesar un depósito que sí se emparejó con una vivienda, debe
aplicarse automáticamente contra los FeeCharge pendientes/vencidos de esa
vivienda. Reusa el patrón de fixtures de test_deposit_processing.py (mismo
motivo: process_incoming_deposit abre su propia sesión, no la de FastAPI).
"""

from contextlib import asynccontextmanager
from datetime import date, datetime
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


def _deposito(referencia="0000001", clave="STP-001", monto=1500.00):
    return DepositoRecibido(
        monto=monto,
        referencia_numerica=referencia,
        clave_rastreo=clave,
        fecha=datetime(2026, 9, 15, 10, 0, 0),
        cuenta_beneficiaria="012180001547896321",
    )


async def _cargos_de(client) -> list[FeeCharge]:
    async with client.db_session_factory() as db:
        result = await db.execute(select(FeeCharge).order_by(FeeCharge.periodo))
        return result.scalars().all()


def _como(rol: str) -> None:
    import uuid

    from app.api.deps import get_current_user
    from app.main import app
    from app.schemas.auth import CurrentUser

    tenant_id = app.dependency_overrides[get_current_user]().tenant_id

    def override():
        return CurrentUser(user_id=str(uuid.uuid4()), tenant_id=tenant_id, schema_name="test", rol=rol, property_id=None)

    app.dependency_overrides[get_current_user] = override


@pytest.mark.asyncio
async def test_matching_deposit_pays_pending_charge(client, deposit_env):
    client.post("/properties", json={"identificador": "Casa 1"})
    _como("tesorero")  # F0-12: cuotas y cargos son de tesorería, no del administrador
    client.post("/fees", json={"monto": 1500.00, "periodicidad": "mensual", "activa_desde": "2026-09-01"})
    client.post("/fees/generate-charges", params={"periodo": "2026-09-01"})

    async with deposit_env() as control_db:
        payment = await dps.process_incoming_deposit(_deposito(monto=1500.00), control_db)

    [cargo] = await _cargos_de(client)
    assert cargo.estado.value == "pagado"
    assert cargo.payment_id == payment.id


@pytest.mark.asyncio
async def test_insufficient_deposit_leaves_charge_pending(client, deposit_env):
    client.post("/properties", json={"identificador": "Casa 1"})
    _como("tesorero")  # F0-12: cuotas y cargos son de tesorería, no del administrador
    client.post("/fees", json={"monto": 1500.00, "periodicidad": "mensual", "activa_desde": "2026-09-01"})
    client.post("/fees/generate-charges", params={"periodo": "2026-09-01"})

    async with deposit_env() as control_db:
        await dps.process_incoming_deposit(_deposito(monto=800.00), control_db)

    [cargo] = await _cargos_de(client)
    assert cargo.estado.value == "pendiente"
    assert cargo.payment_id is None


@pytest.mark.asyncio
async def test_deposit_pays_oldest_charge_first(client, deposit_env):
    client.post("/properties", json={"identificador": "Casa 1"})
    _como("tesorero")  # F0-12: cuotas y cargos son de tesorería, no del administrador
    client.post("/fees", json={"monto": 1500.00, "periodicidad": "mensual", "activa_desde": "2026-08-01"})
    client.post("/fees/generate-charges", params={"periodo": "2026-08-01"})
    client.post("/fees/generate-charges", params={"periodo": "2026-09-01"})

    async with deposit_env() as control_db:
        payment = await dps.process_incoming_deposit(_deposito(monto=3000.00), control_db)

    cargos = await _cargos_de(client)
    assert all(c.estado.value == "pagado" for c in cargos)
    assert all(c.payment_id == payment.id for c in cargos)
    assert cargos[0].periodo == date(2026, 8, 1)
    assert cargos[1].periodo == date(2026, 9, 1)


@pytest.mark.asyncio
async def test_deposit_must_cover_recargo_to_settle_overdue_charge(client, deposit_env):
    client.post("/properties", json={"identificador": "Casa 1"})
    _como("tesorero")  # F0-12: cuotas y cargos son de tesorería, no del administrador
    client.post("/fees", json={"monto": 1500.00, "periodicidad": "mensual", "activa_desde": "2026-09-01"})
    client.post("/fees/generate-charges", params={"periodo": "2026-09-01"})
    client.post("/fees/apply-late-surcharges", params={"hoy": "2026-09-06"})  # +10% = 1650.00 total

    async with deposit_env() as control_db:
        await dps.process_incoming_deposit(_deposito(monto=1500.00), control_db)

    [cargo] = await _cargos_de(client)
    assert cargo.estado.value == "vencido"  # el depósito no alcanzó a cubrir el recargo
    assert cargo.payment_id is None

    async with deposit_env() as control_db:
        await dps.process_incoming_deposit(_deposito(clave="STP-002", monto=150.00), control_db)

    [cargo] = await _cargos_de(client)
    assert cargo.estado.value == "vencido"  # sigue sin conciliarse: llegó en un depósito separado


@pytest.mark.asyncio
async def test_deposit_without_matching_property_does_not_touch_charges(client, deposit_env):
    client.post("/properties", json={"identificador": "Casa 1"})
    _como("tesorero")  # F0-12: cuotas y cargos son de tesorería, no del administrador
    client.post("/fees", json={"monto": 1500.00, "periodicidad": "mensual", "activa_desde": "2026-09-01"})
    client.post("/fees/generate-charges", params={"periodo": "2026-09-01"})

    async with deposit_env() as control_db:
        payment = await dps.process_incoming_deposit(_deposito(referencia="9999999", monto=1500.00), control_db)

    assert payment.estado.value == "pendiente"
    [cargo] = await _cargos_de(client)
    assert cargo.estado.value == "pendiente"
    assert cargo.payment_id is None


@pytest.mark.asyncio
async def test_retrying_same_webhook_does_not_reconcile_twice(client, deposit_env):
    """
    Reintentar el mismo depósito (mismo clave_rastreo) es idempotente a nivel
    Payment (ver test_deposit_processing.py); aquí se confirma que tampoco
    duplica el efecto de la conciliación sobre el FeeCharge.
    """
    client.post("/properties", json={"identificador": "Casa 1"})
    _como("tesorero")  # F0-12: cuotas y cargos son de tesorería, no del administrador
    client.post("/fees", json={"monto": 1500.00, "periodicidad": "mensual", "activa_desde": "2026-09-01"})
    client.post("/fees/generate-charges", params={"periodo": "2026-09-01"})

    async with deposit_env() as control_db:
        first = await dps.process_incoming_deposit(_deposito(clave="STP-DUP", monto=1500.00), control_db)
    async with deposit_env() as control_db:
        second = await dps.process_incoming_deposit(_deposito(clave="STP-DUP", monto=1500.00), control_db)

    assert first.id == second.id
    [cargo] = await _cargos_de(client)
    assert cargo.estado.value == "pagado"
    assert cargo.payment_id == first.id
