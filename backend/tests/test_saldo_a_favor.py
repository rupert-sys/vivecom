"""
F1-09: si un depósito conciliado (F1-07) excede lo debido, el sobrante se
guarda como saldo a favor de la vivienda y se aplica automáticamente al
siguiente FeeCharge que se genere para ella.

Nota: si el sobrante es un múltiplo EXACTO de la cuota mensual (1-12x), F1-08
lo intercepta antes de llegar aquí y crea de una vez los cargos futuros
correspondientes (ver test_pago_anticipado.py) — por eso las pruebas de este
archivo usan montos que NO son un múltiplo exacto, para ejercitar el camino
genérico de "saldo a favor" y no el de "pago anticipado".
"""

import asyncio
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.models.fee_charge import FeeCharge
from app.models.payment import EstadoPago, Payment
from app.services.payment_reconciliation_service import reconcile_payment
from app.models.property import Property
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


async def _propiedad(client) -> Property:
    async with client.db_session_factory() as db:
        result = await db.execute(select(Property))
        return result.scalar_one()


async def _cargos_de(client) -> list[FeeCharge]:
    async with client.db_session_factory() as db:
        result = await db.execute(select(FeeCharge).order_by(FeeCharge.periodo))
        return result.scalars().all()


def _como(rol: str) -> None:
    from app.api.deps import get_current_user
    from app.main import app
    from app.schemas.auth import CurrentUser

    tenant_id = app.dependency_overrides[get_current_user]().tenant_id

    def override():
        return CurrentUser(user_id=str(uuid.uuid4()), tenant_id=tenant_id, schema_name="test", rol=rol, property_id=None)

    app.dependency_overrides[get_current_user] = override


@pytest.mark.asyncio
async def test_excess_deposit_becomes_credit(client, deposit_env):
    client.post("/properties", json={"identificador": "Casa 1"})
    _como("tesorero")  # F0-12: cuotas y cargos son de tesorería, no del administrador
    client.post("/fees", json={"monto": 1500.00, "periodicidad": "mensual", "activa_desde": "2026-09-01"})
    client.post("/fees/generate-charges", params={"periodo": "2026-09-01"})

    async with deposit_env() as control_db:
        payment = await dps.process_incoming_deposit(_deposito(monto=2000.00), control_db)

    [cargo] = await _cargos_de(client)
    assert cargo.estado.value == "pagado"
    assert cargo.payment_id == payment.id

    propiedad = await _propiedad(client)
    assert float(propiedad.saldo_a_favor) == 500.00


@pytest.mark.asyncio
async def test_credit_settles_next_generated_charge(client, deposit_env):
    client.post("/properties", json={"identificador": "Casa 1"})
    _como("tesorero")  # F0-12: cuotas y cargos son de tesorería, no del administrador
    client.post("/fees", json={"monto": 1500.00, "periodicidad": "mensual", "activa_desde": "2026-09-01"})
    # Deposita antes de que exista ningún cargo, con un monto que NO es un
    # múltiplo exacto de la cuota (1.5x) para que F1-08 no lo intercepte:
    # todo el monto queda como crédito genérico.

    async with deposit_env() as control_db:
        await dps.process_incoming_deposit(_deposito(monto=2250.00), control_db)

    propiedad = await _propiedad(client)
    assert float(propiedad.saldo_a_favor) == 2250.00

    response = client.post("/fees/generate-charges", params={"periodo": "2026-09-01"})
    assert response.json()["cargos_generados"] == 1

    [cargo] = await _cargos_de(client)
    assert cargo.estado.value == "pagado"
    assert cargo.payment_id is None  # se saldó con crédito, no con un pago directo

    propiedad = await _propiedad(client)
    assert float(propiedad.saldo_a_favor) == 750.00  # 2250 - 1500 del cargo que sí se saldó


@pytest.mark.asyncio
async def test_insufficient_credit_leaves_new_charge_pending(client, deposit_env):
    client.post("/properties", json={"identificador": "Casa 1"})
    _como("tesorero")  # F0-12: cuotas y cargos son de tesorería, no del administrador
    client.post("/fees", json={"monto": 1500.00, "periodicidad": "mensual", "activa_desde": "2026-09-01"})

    async with deposit_env() as control_db:
        await dps.process_incoming_deposit(_deposito(monto=500.00), control_db)

    propiedad = await _propiedad(client)
    assert float(propiedad.saldo_a_favor) == 500.00

    client.post("/fees/generate-charges", params={"periodo": "2026-09-01"})

    [cargo] = await _cargos_de(client)
    assert cargo.estado.value == "pendiente"

    propiedad = await _propiedad(client)
    assert float(propiedad.saldo_a_favor) == 500.00  # sin tocar: no alcanzó para el cargo completo


@pytest.mark.asyncio
async def test_concurrent_deposits_do_not_lose_credit_updates(client):
    """
    Revisión de code-review (finding #3): reconcile_payment() actualizaba
    Property.saldo_a_favor con un read-modify-write sin candado — dos
    depósitos conciliados a la vez para la misma vivienda podían pisarse y
    perder uno de los dos incrementos. Se prueba con asyncio.gather(), no
    llamadas secuenciales, para ejercitar la carrera real.
    """
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()
    property_id = uuid.UUID(prop["id"])

    def _pago(monto: float, clave: str) -> Payment:
        return Payment(
            property_id=property_id, monto=monto, estado=EstadoPago.confirmado, referencia_recibida="0000001",
            clave_rastreo=clave, proveedor="stp", fecha_deteccion=datetime(2026, 9, 15, 10, 0, 0),
        )

    async def conciliar(monto: float, clave: str):
        async with client.db_session_factory() as db:
            pago = _pago(monto, clave)
            db.add(pago)
            await db.flush()
            await reconcile_payment(db, pago)
            await db.commit()

    # Montos que NO son múltiplos exactos de ninguna cuota (no hay Fee
    # configurado siquiera), así que todo va directo a saldo_a_favor.
    await asyncio.gather(conciliar(321.00, "STP-A"), conciliar(654.00, "STP-B"))

    propiedad = await _propiedad(client)
    assert float(propiedad.saldo_a_favor) == 975.00  # 321 + 654 — ninguno de los dos incrementos se debe perder
