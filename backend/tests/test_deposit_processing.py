"""
process_incoming_deposit() abre su propia conexión a la base de datos real
(no usa el sistema de dependencias de FastAPI, porque también lo usa el
worker de Celery). Para probarlo sin depender de Postgres real, se sustituye
`tenant_session` y `control_session` por versiones que usan la misma base
SQLite en memoria del resto de las pruebas.
"""

from contextlib import asynccontextmanager
from datetime import datetime
from unittest.mock import patch

import pytest

from app.services import deposit_processing_service as dps
from app.services.payment_providers.base import DepositoRecibido


@pytest.fixture()
def deposit_env(client):
    """Parchea tenant_session/control_session del servicio para usar la BD de prueba."""

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


def _deposito(referencia="0000014", clave="STP-001", monto=1500.00):
    return DepositoRecibido(
        monto=monto,
        referencia_numerica=referencia,
        clave_rastreo=clave,
        fecha=datetime(2026, 9, 15, 10, 0, 0),
        cuenta_beneficiaria="012180001547896321",  # coincide con el tenant sembrado en conftest.py
    )


@pytest.mark.asyncio
async def test_deposit_matches_property_by_reference(client, deposit_env):
    client.post("/properties", json={"identificador": "Casa 14"})

    async with deposit_env() as control_db:
        payment = await dps.process_incoming_deposit(_deposito(), control_db)

    assert payment.estado.value == "confirmado"
    assert payment.property_id is not None


@pytest.mark.asyncio
async def test_deposit_with_unknown_reference_stays_pending(client, deposit_env):
    client.post("/properties", json={"identificador": "Casa 14"})  # referencia 0000014, no coincide

    async with deposit_env() as control_db:
        payment = await dps.process_incoming_deposit(_deposito(referencia="9999999"), control_db)

    assert payment.estado.value == "pendiente"
    assert payment.property_id is None


@pytest.mark.asyncio
async def test_deposit_is_idempotent_by_clave_rastreo(client, deposit_env):
    client.post("/properties", json={"identificador": "Casa 14"})

    async with deposit_env() as control_db:
        first = await dps.process_incoming_deposit(_deposito(clave="STP-DUPLICADO"), control_db)
    async with deposit_env() as control_db:
        second = await dps.process_incoming_deposit(_deposito(clave="STP-DUPLICADO"), control_db)

    assert first.id == second.id


@pytest.mark.asyncio
async def test_deposit_to_unrecognized_clabe_raises(client, deposit_env):
    # Sin esta llamada, las tablas de la BD de prueba nunca se crean (se
    # crean de forma perezosa en el primer request real) y process_incoming_deposit
    # truena con "no such table" en vez de con el error que sí queremos probar.
    client.get("/tenant/clabe")

    deposito = _deposito()
    deposito.cuenta_beneficiaria = "999999999999999999"  # ninguna tenant tiene esta CLABE

    async with deposit_env() as control_db:
        with pytest.raises(dps.TenantNoEncontrado):
            await dps.process_incoming_deposit(deposito, control_db)
