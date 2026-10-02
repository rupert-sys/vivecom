"""
F1-14: estado de cuenta por vivienda — historial de cargos y pagos, más el
saldo actual (a favor o en contra).
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


def _como(rol: str) -> None:
    tenant_id = app.dependency_overrides[get_current_user]().tenant_id

    def override():
        return CurrentUser(user_id=str(uuid.uuid4()), tenant_id=tenant_id, schema_name="test", rol=rol, property_id=None)

    app.dependency_overrides[get_current_user] = override


def _como_residente(property_id: str):
    tenant_id = app.dependency_overrides[get_current_user]().tenant_id

    def override():
        return CurrentUser(
            user_id=str(uuid.uuid4()), tenant_id=tenant_id, schema_name="test", rol="residente",
            property_id=property_id,
        )

    app.dependency_overrides[get_current_user] = override


@pytest.mark.asyncio
async def test_statement_shows_paid_charge_and_payment(client, deposit_env):
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()
    _como("tesorero")  # F0-12: cuotas y cargos son de tesorería, no del administrador
    client.post("/fees", json={"monto": 1500.00, "periodicidad": "mensual", "activa_desde": "2026-09-01"})
    client.post("/fees/generate-charges", params={"periodo": "2026-09-01"})

    async with deposit_env() as control_db:
        await dps.process_incoming_deposit(_deposito(), control_db)

    response = client.get(f"/properties/{prop['id']}/statement")
    assert response.status_code == 200
    body = response.json()
    assert body["deuda_total"] == 0.0
    assert body["saldo_a_favor"] == 0.0
    [cargo] = body["cargos"]
    assert cargo["estado"] == "pagado"
    [pago] = body["pagos"]
    assert pago["estado"] == "confirmado"


@pytest.mark.asyncio
async def test_statement_reports_debt_for_pending_charge(client):
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()
    _como("tesorero")
    client.post("/fees", json={"monto": 1500.00, "periodicidad": "mensual", "activa_desde": "2026-09-01"})
    client.post("/fees/generate-charges", params={"periodo": "2026-09-01"})

    response = client.get(f"/properties/{prop['id']}/statement")
    body = response.json()
    assert body["deuda_total"] == 1500.00
    assert body["cargos"][0]["estado"] == "pendiente"
    assert body["pagos"] == []


@pytest.mark.asyncio
async def test_statement_debt_includes_recargo(client):
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()
    _como("tesorero")
    client.post("/fees", json={"monto": 1500.00, "periodicidad": "mensual", "activa_desde": "2026-09-01"})
    client.post("/fees/generate-charges", params={"periodo": "2026-09-01"})
    client.post("/fees/apply-late-surcharges", params={"hoy": "2026-09-06"})

    response = client.get(f"/properties/{prop['id']}/statement")
    body = response.json()
    assert body["deuda_total"] == 1650.00  # 1500 + 10%
    assert body["cargos"][0]["estado"] == "vencido"


@pytest.mark.asyncio
async def test_statement_404_for_unknown_property(client):
    client.get("/tenant/clabe")  # crea las tablas de prueba
    response = client.get(f"/properties/{uuid.uuid4()}/statement")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_resident_can_view_own_statement(client):
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()

    _como_residente(prop["id"])
    response = client.get(f"/properties/{prop['id']}/statement")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_resident_cannot_view_others_statement(client):
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()

    _como_residente(str(uuid.uuid4()))
    response = client.get(f"/properties/{prop['id']}/statement")
    assert response.status_code == 403
