"""
F1-11 / HU-A08: recibo simple (no fiscal) en PDF, descargable por el
residente dueño de la vivienda o por admin/tesorero, solo para pagos ya
confirmados.
"""

import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from unittest.mock import patch

import pytest

from app.api.deps import get_current_user
from app.main import app
from app.schemas.auth import CurrentUser
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


def _como_residente(property_id: str):
    """
    Sustituye temporalmente al admin de conftest.py por un residente de una
    vivienda específica. Se revierte solo al terminar el test (el fixture
    `client` limpia dependency_overrides al final).

    El tenant_id se toma del override de admin ya activo (no de la constante
    TEST_TENANT_ID de conftest.py): tests/ no tiene __init__.py, así que un
    `import tests.conftest` aquí ejecutaría el módulo una segunda vez con un
    TEST_TENANT_ID aleatorio distinto al que realmente sembró la base de
    prueba en este test.
    """
    tenant_id = app.dependency_overrides[get_current_user]().tenant_id

    def override():
        return CurrentUser(
            user_id=str(uuid.uuid4()), tenant_id=tenant_id, schema_name="test", rol="residente",
            property_id=property_id,
        )

    app.dependency_overrides[get_current_user] = override


@pytest.mark.asyncio
async def test_receipt_pdf_for_confirmed_payment(client, deposit_env):
    client.post("/properties", json={"identificador": "Casa 1"})

    async with deposit_env() as control_db:
        payment = await dps.process_incoming_deposit(_deposito(), control_db)

    response = client.get(f"/payments/{payment.id}/receipt")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


@pytest.mark.asyncio
async def test_receipt_not_available_for_pending_payment(client, deposit_env):
    client.get("/tenant/clabe")  # crea las tablas de prueba

    async with deposit_env() as control_db:
        payment = await dps.process_incoming_deposit(_deposito(referencia="9999999"), control_db)

    response = client.get(f"/payments/{payment.id}/receipt")
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_receipt_404_for_unknown_payment(client):
    client.get("/tenant/clabe")  # crea las tablas de prueba
    response = client.get(f"/payments/{uuid.uuid4()}/receipt")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_resident_can_download_own_receipt(client, deposit_env):
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()

    async with deposit_env() as control_db:
        payment = await dps.process_incoming_deposit(_deposito(), control_db)

    _como_residente(prop["id"])
    response = client.get(f"/payments/{payment.id}/receipt")
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")


@pytest.mark.asyncio
async def test_resident_cannot_download_others_receipt(client, deposit_env):
    client.post("/properties", json={"identificador": "Casa 1"})

    async with deposit_env() as control_db:
        payment = await dps.process_incoming_deposit(_deposito(), control_db)

    _como_residente(str(uuid.uuid4()))  # otra vivienda
    response = client.get(f"/payments/{payment.id}/receipt")
    assert response.status_code == 403
