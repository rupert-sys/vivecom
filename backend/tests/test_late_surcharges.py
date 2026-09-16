

def _setup_charge(client, periodo="2026-09-01"):
    client.post("/properties", json={"identificador": "Casa 1"})
    client.post("/fees", json={"monto": 1500.00, "periodicidad": "mensual", "activa_desde": "2026-09-01"})
    client.post("/fees/generate-charges", params={"periodo": periodo})


def test_no_surcharge_before_day_6(client):
    """Antes del día 6 del mes, un cargo pendiente NO debe recibir recargo."""
    _setup_charge(client)

    response = client.post("/fees/apply-late-surcharges", params={"hoy": "2026-09-05"})
    assert response.json()["cargos_marcados_vencidos"] == 0


def test_surcharge_applies_exactly_on_day_6(client):
    """El recargo aplica desde el día 6 (regla: 'minuto 1 del día 6')."""
    _setup_charge(client)

    response = client.post("/fees/apply-late-surcharges", params={"hoy": "2026-09-06"})
    assert response.json()["cargos_marcados_vencidos"] == 1


def test_surcharge_amount_is_exactly_10_percent(client):
    import asyncio

    from sqlalchemy import select

    from app.models.fee_charge import FeeCharge

    _setup_charge(client)
    client.post("/fees/apply-late-surcharges", params={"hoy": "2026-09-06"})

    async def _read_charge():
        async with client.db_session_factory() as db:
            result = await db.execute(select(FeeCharge))
            return result.scalar_one()

    charge = asyncio.run(_read_charge())
    assert float(charge.recargo_aplicado) == 150.00  # 10% de 1500.00
    assert charge.estado.value == "vencido"


def test_surcharge_is_idempotent(client):
    """Correr el job de recargos dos veces el mismo día no debe duplicar el recargo."""
    _setup_charge(client)

    client.post("/fees/apply-late-surcharges", params={"hoy": "2026-09-06"})
    second_run = client.post("/fees/apply-late-surcharges", params={"hoy": "2026-09-06"})

    assert second_run.json()["cargos_marcados_vencidos"] == 0


def test_surcharge_respects_month_boundary(client):
    """Un cargo de octubre no debe recibir recargo el día 6 de septiembre."""
    _setup_charge(client, periodo="2026-10-01")

    response = client.post("/fees/apply-late-surcharges", params={"hoy": "2026-09-06"})
    assert response.json()["cargos_marcados_vencidos"] == 0
