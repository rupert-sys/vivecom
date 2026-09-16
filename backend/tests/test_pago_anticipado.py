"""
F1-08 / HU-A05: si, tras saldar todo lo pendiente/vencido de una vivienda,
lo que sobra del depósito es un múltiplo exacto (1-12x) de la cuota mensual
vigente, se crean de inmediato los FeeCharge de esos meses futuros, ya
pagados — así nunca llegan a existir en estado pendiente el día que
correría el recargo del día 6.
"""

from contextlib import asynccontextmanager
from datetime import date, datetime
from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.models.fee_charge import FeeCharge
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


@pytest.mark.asyncio
async def test_advance_payment_creates_future_charges_immediately(client, deposit_env):
    client.post("/properties", json={"identificador": "Casa 1"})
    client.post("/fees", json={"monto": 1500.00, "periodicidad": "mensual", "activa_desde": "2026-09-01"})
    # Sin ningún cargo generado todavía: deposita 3 meses (el depósito llega
    # el 15 de septiembre, así que "el mes" es septiembre).

    async with deposit_env() as control_db:
        payment = await dps.process_incoming_deposit(_deposito(monto=4500.00), control_db)

    cargos = await _cargos_de(client)
    assert [c.periodo for c in cargos] == [date(2026, 9, 1), date(2026, 10, 1), date(2026, 11, 1)]
    assert all(c.estado.value == "pagado" for c in cargos)
    assert all(c.payment_id == payment.id for c in cargos)

    propiedad = await _propiedad(client)
    assert float(propiedad.saldo_a_favor) == 0.00  # nada quedó como crédito genérico

    # Idempotencia con F1-03: generar cargos para septiembre no debe duplicar.
    response = client.post("/fees/generate-charges", params={"periodo": "2026-09-01"})
    assert response.json()["cargos_generados"] == 0


@pytest.mark.asyncio
async def test_advance_payment_pays_current_charge_then_advances(client, deposit_env):
    client.post("/properties", json={"identificador": "Casa 1"})
    client.post("/fees", json={"monto": 1500.00, "periodicidad": "mensual", "activa_desde": "2026-09-01"})
    client.post("/fees/generate-charges", params={"periodo": "2026-09-01"})  # cargo de septiembre ya existe

    # 1500 para septiembre + 3 x 1500 de anticipo (octubre-diciembre).
    async with deposit_env() as control_db:
        payment = await dps.process_incoming_deposit(_deposito(monto=6000.00), control_db)

    cargos = await _cargos_de(client)
    assert [c.periodo for c in cargos] == [
        date(2026, 9, 1), date(2026, 10, 1), date(2026, 11, 1), date(2026, 12, 1),
    ]
    assert all(c.estado.value == "pagado" for c in cargos)
    assert all(c.payment_id == payment.id for c in cargos)


@pytest.mark.asyncio
async def test_advance_payment_caps_at_12_months(client, deposit_env):
    client.post("/properties", json={"identificador": "Casa 1"})
    client.post("/fees", json={"monto": 1500.00, "periodicidad": "mensual", "activa_desde": "2026-09-01"})

    # 13 meses excede el máximo de HU-A05: no se trata como anticipo, todo
    # el monto se queda como saldo a favor genérico (F1-09).
    async with deposit_env() as control_db:
        await dps.process_incoming_deposit(_deposito(monto=19500.00), control_db)

    assert await _cargos_de(client) == []
    propiedad = await _propiedad(client)
    assert float(propiedad.saldo_a_favor) == 19500.00


@pytest.mark.asyncio
async def test_advance_payment_blocked_while_older_charge_unpaid(client, deposit_env):
    client.post("/properties", json={"identificador": "Casa 1"})
    client.post("/fees", json={"monto": 1500.00, "periodicidad": "mensual", "activa_desde": "2026-09-01"})
    client.post("/fees/generate-charges", params={"periodo": "2026-09-01"})
    client.post("/fees/apply-late-surcharges", params={"hoy": "2026-09-06"})  # ahora debe 1500 + 150 = 1650

    # El depósito "parece" exactamente 1 mes de cuota (1500), pero no alcanza
    # a cubrir el cargo vencido (1650) — no debe interpretarse como anticipo.
    async with deposit_env() as control_db:
        await dps.process_incoming_deposit(_deposito(monto=1500.00), control_db)

    [cargo] = await _cargos_de(client)
    assert cargo.estado.value == "vencido"
    assert cargo.payment_id is None

    propiedad = await _propiedad(client)
    assert float(propiedad.saldo_a_favor) == 1500.00  # queda como crédito, no como anticipo


@pytest.mark.asyncio
async def test_advance_payment_continues_from_last_charged_period(client, deposit_env):
    client.post("/properties", json={"identificador": "Casa 1"})
    client.post("/fees", json={"monto": 1500.00, "periodicidad": "mensual", "activa_desde": "2026-09-01"})
    client.post("/fees/generate-charges", params={"periodo": "2026-09-01"})

    async with deposit_env() as control_db:
        await dps.process_incoming_deposit(_deposito(clave="STP-001", monto=1500.00), control_db)  # salda septiembre

    async with deposit_env() as control_db:
        payment = await dps.process_incoming_deposit(_deposito(clave="STP-002", monto=3000.00), control_db)

    cargos = await _cargos_de(client)
    assert [c.periodo for c in cargos] == [date(2026, 9, 1), date(2026, 10, 1), date(2026, 11, 1)]
    assert cargos[0].payment_id != payment.id  # septiembre se pagó con el primer depósito
    assert cargos[1].payment_id == payment.id
    assert cargos[2].payment_id == payment.id
