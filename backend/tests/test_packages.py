"""
F2-04 / HU-S05: paquetería — registro de llegada, cierre al recogerse, y
notificación por WhatsApp/SMS en cada uno de esos dos momentos.
"""

import uuid

import pytest

from app.services.notification_providers.base import NotificationProvider
from app.services.package_notification_service import send_package_notifications


class FakeNotificationProvider(NotificationProvider):
    def __init__(self):
        self.enviados: list[tuple[str, str]] = []

    async def send(self, telefono: str, mensaje: str) -> bool:
        self.enviados.append((telefono, mensaje))
        return True


def _crear_residente_y_ligar(client, property_id: str, telefono="5511112222"):
    resident = client.post("/residents", json={"nombre": "Ana Pérez", "telefono": telefono}).json()
    client.post(f"/properties/{property_id}/residents", json={"resident_id": resident["id"], "rol": "propietario"})


def test_register_package(client):
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()

    response = client.post("/packages", json={"property_id": prop["id"]})
    assert response.status_code == 201
    body = response.json()
    assert body["fecha_recogido"] is None


def test_register_package_unknown_property_404(client):
    response = client.post("/packages", json={"property_id": str(uuid.uuid4())})
    assert response.status_code == 404


def test_mark_package_picked_up(client):
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()
    paquete = client.post("/packages", json={"property_id": prop["id"]}).json()

    response = client.post(f"/packages/{paquete['id']}/pickup")
    assert response.status_code == 200
    assert response.json()["fecha_recogido"] is not None


def test_mark_already_picked_up_package_fails(client):
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()
    paquete = client.post("/packages", json={"property_id": prop["id"]}).json()
    client.post(f"/packages/{paquete['id']}/pickup")

    response = client.post(f"/packages/{paquete['id']}/pickup")
    assert response.status_code == 409


def test_list_packages_filters_pendientes(client):
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()
    pendiente = client.post("/packages", json={"property_id": prop["id"]}).json()
    recogido = client.post("/packages", json={"property_id": prop["id"]}).json()
    client.post(f"/packages/{recogido['id']}/pickup")

    solo_pendientes = client.get("/packages", params={"pendientes": True}).json()
    assert [p["id"] for p in solo_pendientes] == [pendiente["id"]]

    solo_recogidos = client.get("/packages", params={"pendientes": False}).json()
    assert [p["id"] for p in solo_recogidos] == [recogido["id"]]


@pytest.mark.asyncio
async def test_send_notifications_covers_arrival_and_pickup(client):
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()
    _crear_residente_y_ligar(client, prop["id"])
    paquete = client.post("/packages", json={"property_id": prop["id"]}).json()

    provider = FakeNotificationProvider()
    async with client.db_session_factory() as db:
        enviados = await send_package_notifications(db, provider)
    assert enviados == 1
    assert provider.enviados == [("5511112222", "Vivecom: te llegó un paquete. Pásalo a recoger en la caseta.")]

    # segunda corrida: sin recoger todavía, no debe volver a notificar la llegada
    async with client.db_session_factory() as db:
        segunda = await send_package_notifications(db, provider)
    assert segunda == 0
    assert len(provider.enviados) == 1

    client.post(f"/packages/{paquete['id']}/pickup")

    async with client.db_session_factory() as db:
        tercera = await send_package_notifications(db, provider)
    assert tercera == 1
    assert provider.enviados[-1] == ("5511112222", "Vivecom: tu paquete fue recogido. Registro cerrado.")
