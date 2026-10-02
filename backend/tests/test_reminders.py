"""
F1-13: recordatorios de pago (mientras un cargo siga pendiente/vencido, una
vez al día) y confirmaciones de pago (una sola vez, cuando el cargo pasa a
pagado, sin importar qué lo pagó).
"""

from datetime import date

import pytest
from sqlalchemy import select

from app.models.fee_charge import FeeCharge
from app.services.notification_providers.base import NotificationProvider
from app.services.reminder_service import send_payment_confirmations, send_payment_reminders


class FakeNotificationProvider(NotificationProvider):
    def __init__(self):
        self.enviados: list[tuple[str, str]] = []

    async def send(self, telefono: str, mensaje: str) -> bool:
        self.enviados.append((telefono, mensaje))
        return True


class FailingNotificationProvider(NotificationProvider):
    """Simula un proveedor cuyo envío siempre falla (ej. Twilio caído)."""

    async def send(self, telefono: str, mensaje: str) -> bool:
        return False


def _crear_residente_y_ligar(client, property_id: str, telefono: str, nombre="Ana Pérez"):
    resident = client.post("/residents", json={"nombre": nombre, "telefono": telefono}).json()
    client.post(f"/properties/{property_id}/residents", json={"resident_id": resident["id"], "rol": "propietario"})
    return resident


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
async def test_reminder_sent_to_resident_of_pending_charge(client):
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()
    _crear_residente_y_ligar(client, prop["id"], "5511112222")
    _como("tesorero")  # F0-12: cuotas y cargos son de tesorería, no del administrador
    client.post("/fees", json={"monto": 1500.00, "periodicidad": "mensual", "activa_desde": "2026-09-01"})
    client.post("/fees/generate-charges", params={"periodo": "2026-09-01"})

    provider = FakeNotificationProvider()
    async with client.db_session_factory() as db:
        enviados = await send_payment_reminders(db, provider, date(2026, 9, 1))

    assert enviados == 1
    assert provider.enviados == [("5511112222", provider.enviados[0][1])]
    assert "1,500.00" in provider.enviados[0][1]

    async with client.db_session_factory() as db:
        cargo = (await db.execute(select(FeeCharge))).scalar_one()
    assert cargo.recordatorio_enviado_en == date(2026, 9, 1)


@pytest.mark.asyncio
async def test_reminder_not_sent_twice_same_day(client):
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()
    _crear_residente_y_ligar(client, prop["id"], "5511112222")
    _como("tesorero")  # F0-12: cuotas y cargos son de tesorería, no del administrador
    client.post("/fees", json={"monto": 1500.00, "periodicidad": "mensual", "activa_desde": "2026-09-01"})
    client.post("/fees/generate-charges", params={"periodo": "2026-09-01"})

    provider = FakeNotificationProvider()
    async with client.db_session_factory() as db:
        await send_payment_reminders(db, provider, date(2026, 9, 1))
    async with client.db_session_factory() as db:
        segunda_corrida = await send_payment_reminders(db, provider, date(2026, 9, 1))

    assert segunda_corrida == 0
    assert len(provider.enviados) == 1


@pytest.mark.asyncio
async def test_reminder_resent_next_day_while_unpaid(client):
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()
    _crear_residente_y_ligar(client, prop["id"], "5511112222")
    _como("tesorero")  # F0-12: cuotas y cargos son de tesorería, no del administrador
    client.post("/fees", json={"monto": 1500.00, "periodicidad": "mensual", "activa_desde": "2026-09-01"})
    client.post("/fees/generate-charges", params={"periodo": "2026-09-01"})

    provider = FakeNotificationProvider()
    async with client.db_session_factory() as db:
        await send_payment_reminders(db, provider, date(2026, 9, 1))
    async with client.db_session_factory() as db:
        siguiente_dia = await send_payment_reminders(db, provider, date(2026, 9, 2))

    assert siguiente_dia == 1
    assert len(provider.enviados) == 2


@pytest.mark.asyncio
async def test_reminder_not_sent_for_future_period(client):
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()
    _crear_residente_y_ligar(client, prop["id"], "5511112222")
    _como("tesorero")  # F0-12: cuotas y cargos son de tesorería, no del administrador
    client.post("/fees", json={"monto": 1500.00, "periodicidad": "mensual", "activa_desde": "2026-09-01"})
    client.post("/fees/generate-charges", params={"periodo": "2026-10-01"})

    provider = FakeNotificationProvider()
    async with client.db_session_factory() as db:
        enviados = await send_payment_reminders(db, provider, date(2026, 9, 15))  # antes de octubre

    assert enviados == 0
    assert provider.enviados == []


@pytest.mark.asyncio
async def test_reminder_sent_for_overdue_charge(client):
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()
    _crear_residente_y_ligar(client, prop["id"], "5511112222")
    _como("tesorero")  # F0-12: cuotas y cargos son de tesorería, no del administrador
    client.post("/fees", json={"monto": 1500.00, "periodicidad": "mensual", "activa_desde": "2026-09-01"})
    client.post("/fees/generate-charges", params={"periodo": "2026-09-01"})
    client.post("/fees/apply-late-surcharges", params={"hoy": "2026-09-06"})

    provider = FakeNotificationProvider()
    async with client.db_session_factory() as db:
        enviados = await send_payment_reminders(db, provider, date(2026, 9, 10))

    assert enviados == 1
    assert "1,650.00" in provider.enviados[0][1]  # incluye el recargo


@pytest.mark.asyncio
async def test_reminder_reaches_every_resident_of_the_property(client):
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()
    _crear_residente_y_ligar(client, prop["id"], "5511112222", nombre="Ana Pérez")
    _crear_residente_y_ligar(client, prop["id"], "5533334444", nombre="Luis Gómez")
    _como("tesorero")  # F0-12: cuotas y cargos son de tesorería, no del administrador
    client.post("/fees", json={"monto": 1500.00, "periodicidad": "mensual", "activa_desde": "2026-09-01"})
    client.post("/fees/generate-charges", params={"periodo": "2026-09-01"})

    provider = FakeNotificationProvider()
    async with client.db_session_factory() as db:
        await send_payment_reminders(db, provider, date(2026, 9, 1))

    telefonos = {telefono for telefono, _ in provider.enviados}
    assert telefonos == {"5511112222", "5533334444"}


@pytest.mark.asyncio
async def test_confirmation_sent_once_when_charge_is_paid(client):
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()
    _crear_residente_y_ligar(client, prop["id"], "5511112222")
    _como("tesorero")  # F0-12: cuotas y cargos son de tesorería, no del administrador
    client.post("/fees", json={"monto": 1500.00, "periodicidad": "mensual", "activa_desde": "2026-09-01"})
    client.post("/fees/generate-charges", params={"periodo": "2026-09-01"})

    async with client.db_session_factory() as db:
        cargo = (await db.execute(select(FeeCharge))).scalar_one()
        from app.models.fee_charge import EstadoCargo

        cargo.estado = EstadoCargo.pagado
        await db.commit()

    provider = FakeNotificationProvider()
    async with client.db_session_factory() as db:
        primera = await send_payment_confirmations(db, provider)
    async with client.db_session_factory() as db:
        segunda = await send_payment_confirmations(db, provider)

    assert primera == 1
    assert segunda == 0
    assert len(provider.enviados) == 1
    assert "recibimos tu pago" in provider.enviados[0][1]


@pytest.mark.asyncio
async def test_confirmation_not_marked_sent_when_delivery_fails(client):
    """
    Revisión de code-review (finding #5): antes se marcaba
    confirmacion_enviada=True sin fijarse si el envío realmente tuvo éxito
    — un fallo de Twilio dejaba el cargo "confirmado" para siempre sin que
    el residente se hubiera enterado. Ahora debe quedarse sin marcar para
    reintentarse en la siguiente corrida.
    """
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()
    _crear_residente_y_ligar(client, prop["id"], "5511112222")
    _como("tesorero")  # F0-12: cuotas y cargos son de tesorería, no del administrador
    client.post("/fees", json={"monto": 1500.00, "periodicidad": "mensual", "activa_desde": "2026-09-01"})
    client.post("/fees/generate-charges", params={"periodo": "2026-09-01"})

    async with client.db_session_factory() as db:
        cargo = (await db.execute(select(FeeCharge))).scalar_one()
        from app.models.fee_charge import EstadoCargo

        cargo.estado = EstadoCargo.pagado
        await db.commit()

    provider = FailingNotificationProvider()
    async with client.db_session_factory() as db:
        enviados = await send_payment_confirmations(db, provider)

    assert enviados == 0
    async with client.db_session_factory() as db:
        cargo = (await db.execute(select(FeeCharge))).scalar_one()
    assert cargo.confirmacion_enviada is False  # sigue pendiente de reintentar, no se dio por enviada
