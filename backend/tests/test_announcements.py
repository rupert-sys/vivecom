"""
F1-30/F1-31/F1-32 / HU-C01: avisos y circulares, confirmación de lectura por
vivienda, y notificación por WhatsApp/SMS cuando se publican.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.api.deps import get_current_user
from app.main import app
from app.schemas.auth import CurrentUser
from app.services.announcement_service import send_announcement_notifications
from app.services.notification_providers.base import NotificationProvider


class FakeNotificationProvider(NotificationProvider):
    def __init__(self):
        self.enviados: list[tuple[str, str]] = []

    async def send(self, telefono: str, mensaje: str) -> bool:
        self.enviados.append((telefono, mensaje))
        return True


def _como_residente(property_id: str):
    tenant_id = app.dependency_overrides[get_current_user]().tenant_id

    def override():
        return CurrentUser(
            user_id=str(uuid.uuid4()), tenant_id=tenant_id, schema_name="test", rol="residente",
            property_id=property_id,
        )

    app.dependency_overrides[get_current_user] = override


def test_create_announcement_publishes_immediately_by_default(client):
    created = client.post("/announcements", json={"titulo": "Corte de agua", "contenido": "Mañana 9am-1pm."})
    assert created.status_code == 201

    listado = client.get("/announcements").json()
    assert len(listado) == 1
    assert listado[0]["titulo"] == "Corte de agua"


def test_scheduled_announcement_hidden_from_non_admin(client):
    futuro = (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=3)).isoformat()
    created = client.post(
        "/announcements", json={"titulo": "Asamblea", "contenido": "Próxima semana.", "fecha_publicacion": futuro}
    ).json()

    # admin (el fixture `client` por defecto) sí lo ve, para poder gestionarlo.
    assert len(client.get("/announcements").json()) == 1
    assert client.get(f"/announcements/{created['id']}").status_code == 200

    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()
    _como_residente(prop["id"])
    assert client.get("/announcements").json() == []
    assert client.get(f"/announcements/{created['id']}").status_code == 404


def test_update_announcement(client):
    created = client.post("/announcements", json={"titulo": "Original", "contenido": "Texto"}).json()

    response = client.patch(f"/announcements/{created['id']}", json={"titulo": "Editado"})
    assert response.status_code == 200
    assert response.json()["titulo"] == "Editado"
    assert response.json()["contenido"] == "Texto"


def test_mark_read_is_idempotent(client):
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()
    aviso = client.post("/announcements", json={"titulo": "Aviso", "contenido": "Texto"}).json()

    _como_residente(prop["id"])
    assert client.post(f"/announcements/{aviso['id']}/read").status_code == 204
    assert client.post(f"/announcements/{aviso['id']}/read").status_code == 204  # no debe duplicar

    tenant_id = app.dependency_overrides[get_current_user]().tenant_id

    def como_admin():
        return CurrentUser(user_id=str(uuid.uuid4()), tenant_id=tenant_id, schema_name="test", rol="admin", property_id=None)

    app.dependency_overrides[get_current_user] = como_admin
    estatus = client.get(f"/announcements/{aviso['id']}/read-status").json()
    [entrada] = [e for e in estatus if e["property_id"] == prop["id"]]
    assert entrada["leido"] is True


def test_mark_read_requires_a_property(client):
    aviso = client.post("/announcements", json={"titulo": "Aviso", "contenido": "Texto"}).json()

    response = client.post(f"/announcements/{aviso['id']}/read")  # admin del fixture, sin property_id
    assert response.status_code == 400


def test_read_status_lists_every_property(client):
    prop_a = client.post("/properties", json={"identificador": "Casa 1"}).json()
    prop_b = client.post("/properties", json={"identificador": "Casa 2"}).json()
    aviso = client.post("/announcements", json={"titulo": "Aviso", "contenido": "Texto"}).json()

    _como_residente(prop_a["id"])
    client.post(f"/announcements/{aviso['id']}/read")

    tenant_id = app.dependency_overrides[get_current_user]().tenant_id

    def como_admin():
        return CurrentUser(user_id=str(uuid.uuid4()), tenant_id=tenant_id, schema_name="test", rol="admin", property_id=None)

    app.dependency_overrides[get_current_user] = como_admin
    estatus = {e["property_id"]: e["leido"] for e in client.get(f"/announcements/{aviso['id']}/read-status").json()}
    assert estatus[prop_a["id"]] is True
    assert estatus[prop_b["id"]] is False


@pytest.mark.asyncio
async def test_send_notifications_reaches_all_residents_once(client):
    client.get("/tenant/clabe")  # crea las tablas de prueba
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()
    resident = client.post("/residents", json={"nombre": "Ana Pérez", "telefono": "5511112222"}).json()
    client.post(f"/properties/{prop['id']}/residents", json={"resident_id": resident["id"], "rol": "propietario"})
    client.post("/announcements", json={"titulo": "Aviso", "contenido": "Texto"})

    provider = FakeNotificationProvider()
    async with client.db_session_factory() as db:
        enviados = await send_announcement_notifications(db, provider, datetime.now(timezone.utc).replace(tzinfo=None))
    assert enviados == 1
    assert provider.enviados == [("5511112222", "Vivecom: nuevo aviso — Aviso")]

    async with client.db_session_factory() as db:
        segunda_corrida = await send_announcement_notifications(db, provider, datetime.now(timezone.utc).replace(tzinfo=None))
    assert segunda_corrida == 0
    assert len(provider.enviados) == 1


@pytest.mark.asyncio
async def test_scheduled_announcement_not_notified_before_its_time(client):
    client.get("/tenant/clabe")
    futuro = (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=3)).isoformat()
    client.post("/announcements", json={"titulo": "Asamblea", "contenido": "Texto", "fecha_publicacion": futuro})

    provider = FakeNotificationProvider()
    async with client.db_session_factory() as db:
        enviados = await send_announcement_notifications(db, provider, datetime.now(timezone.utc).replace(tzinfo=None))
    assert enviados == 0
    assert provider.enviados == []


def test_get_unknown_announcement_404(client):
    client.get("/tenant/clabe")
    response = client.get(f"/announcements/{uuid.uuid4()}")
    assert response.status_code == 404
