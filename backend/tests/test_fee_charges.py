import asyncio
from datetime import date

import pytest
from sqlalchemy import select

from app.models.fee_charge import FeeCharge
from app.services.fee_charge_service import generate_charges_for_period


def _setup_fee_and_properties(client, periodicidad="mensual", activa_desde="2026-09-01"):
    client.post("/properties", json={"identificador": "Casa 1"})
    client.post("/properties", json={"identificador": "Casa 2"})
    fee = client.post(
        "/fees", json={"monto": 1500.00, "periodicidad": periodicidad, "activa_desde": activa_desde}
    ).json()
    return fee


def test_generate_charges_creates_one_per_property(client):
    _setup_fee_and_properties(client)

    response = client.post("/fees/generate-charges", params={"periodo": "2026-09-01"})
    assert response.status_code == 200
    assert response.json()["cargos_generados"] == 2


def test_generate_charges_is_idempotent(client):
    """Correr la generación dos veces para el mismo periodo no debe duplicar cargos."""
    _setup_fee_and_properties(client)

    client.post("/fees/generate-charges", params={"periodo": "2026-09-01"})
    second_run = client.post("/fees/generate-charges", params={"periodo": "2026-09-01"})

    assert second_run.json()["cargos_generados"] == 0


def test_bimestral_fee_skips_intermediate_month(client):
    """
    Una cuota bimestral vigente desde septiembre debe generar cargo en
    septiembre y noviembre, pero NO en octubre (el mes intermedio).
    """
    _setup_fee_and_properties(client, periodicidad="bimestral", activa_desde="2026-09-01")

    sep = client.post("/fees/generate-charges", params={"periodo": "2026-09-01"}).json()
    oct_ = client.post("/fees/generate-charges", params={"periodo": "2026-10-01"}).json()
    nov = client.post("/fees/generate-charges", params={"periodo": "2026-11-01"}).json()

    assert sep["cargos_generados"] == 2
    assert oct_["cargos_generados"] == 0
    assert nov["cargos_generados"] == 2


def test_new_property_gets_charge_on_next_generation(client):
    """Si se agrega una vivienda nueva después de generar cargos, la siguiente
    corrida debe generarle su cargo sin tocar las que ya tenían."""
    _setup_fee_and_properties(client)
    client.post("/fees/generate-charges", params={"periodo": "2026-09-01"})

    client.post("/properties", json={"identificador": "Casa 3 (nueva)"})
    second_run = client.post("/fees/generate-charges", params={"periodo": "2026-09-01"})

    assert second_run.json()["cargos_generados"] == 1


@pytest.mark.asyncio
async def test_concurrent_generation_for_same_period_does_not_double_charge(client):
    """
    Revisión de code-review (finding #4): el chequeo de "ya tiene cargo este
    periodo" era un SELECT sin candado — dos disparos concurrentes (el job
    de Celery y uno manual, por ejemplo) para el mismo periodo podían ambos
    pasar la validación antes de que cualquiera comiteara, cobrando dos
    veces a la misma vivienda. Se prueba con asyncio.gather(), no llamadas
    secuenciales.
    """
    _setup_fee_and_properties(client)
    periodo = date(2026, 9, 1)

    async def intentar():
        async with client.db_session_factory() as db:
            return await generate_charges_for_period(db, periodo)

    resultados = await asyncio.gather(intentar(), intentar())

    total_generados = sum(len(r) for r in resultados)
    assert total_generados == 2  # 2 viviendas, un cargo cada una — nunca 4

    async with client.db_session_factory() as db:
        cargos = (await db.execute(select(FeeCharge).where(FeeCharge.periodo == periodo))).scalars().all()
    assert len(cargos) == 2
    assert len({c.property_id for c in cargos}) == 2  # una vivienda, un solo cargo
