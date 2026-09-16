"""
F2-14 / HU-C02, HU-C03, HU-C04: votaciones con quorum, un voto por vivienda,
y reactivación automática si no se alcanza el 51% de participación.
"""

import asyncio
import uuid
from datetime import date

import pytest

from app.api.deps import get_current_user
from app.main import app
from app.schemas.auth import CurrentUser
from app.services.notification_providers.base import NotificationProvider
from app.services.poll_service import VotoInvalido, cast_vote, process_poll_closures


class FakeNotificationProvider(NotificationProvider):
    def __init__(self):
        self.enviados: list[tuple[str, str]] = []

    async def send(self, telefono: str, mensaje: str) -> bool:
        self.enviados.append((telefono, mensaje))
        return True


def _tenant_id() -> str:
    return app.dependency_overrides[get_current_user]().tenant_id


def _como(rol: str, property_id: str | None = None):
    tenant_id = _tenant_id()

    def override():
        return CurrentUser(
            user_id=str(uuid.uuid4()), tenant_id=tenant_id, schema_name="test", rol=rol, property_id=property_id
        )

    app.dependency_overrides[get_current_user] = override


def _crear_votacion(client, fecha_cierre="2026-12-31", resultados_en_vivo=False):
    _como("vocero")
    poll = client.post(
        "/polls",
        json={
            "pregunta": "¿Aprobamos el nuevo reglamento?", "opciones": ["Sí", "No"],
            "fecha_cierre": fecha_cierre, "resultados_en_vivo": resultados_en_vivo,
        },
    ).json()
    _como("admin")
    return poll


def test_vocero_creates_poll(client):
    poll = _crear_votacion(client)
    assert len(poll["opciones"]) == 2
    assert poll["quorum_alcanzado"] is False


def test_non_vocero_cannot_create_poll(client):
    _como("residente", property_id=str(uuid.uuid4()))
    response = client.post("/polls", json={"pregunta": "¿?", "opciones": ["Sí", "No"], "fecha_cierre": "2026-12-31"})
    assert response.status_code == 403


def test_resident_votes_successfully(client):
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()
    poll = _crear_votacion(client)
    opcion = poll["opciones"][0]["id"]

    _como("residente", property_id=prop["id"])
    response = client.post(f"/polls/{poll['id']}/vote", json={"option_id": opcion})
    assert response.status_code == 204


def test_resident_cannot_vote_twice(client):
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()
    poll = _crear_votacion(client)
    opcion = poll["opciones"][0]["id"]

    _como("residente", property_id=prop["id"])
    client.post(f"/polls/{poll['id']}/vote", json={"option_id": opcion})
    segunda_vez = client.post(f"/polls/{poll['id']}/vote", json={"option_id": opcion})
    assert segunda_vez.status_code == 409


def test_vote_with_invalid_option_fails(client):
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()
    poll = _crear_votacion(client)

    _como("residente", property_id=prop["id"])
    response = client.post(f"/polls/{poll['id']}/vote", json={"option_id": str(uuid.uuid4())})
    assert response.status_code == 400


def test_resident_without_property_cannot_vote(client):
    poll = _crear_votacion(client)
    _como("residente")
    response = client.post(f"/polls/{poll['id']}/vote", json={"option_id": poll["opciones"][0]["id"]})
    assert response.status_code == 400


def test_results_hidden_before_close_when_not_live(client):
    poll = _crear_votacion(client, fecha_cierre="2026-12-31", resultados_en_vivo=False)
    response = client.get(f"/polls/{poll['id']}/results")
    assert response.status_code == 409


def test_results_visible_when_live(client):
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()
    poll = _crear_votacion(client, fecha_cierre="2026-12-31", resultados_en_vivo=True)
    opcion = poll["opciones"][0]["id"]

    _como("residente", property_id=prop["id"])
    client.post(f"/polls/{poll['id']}/vote", json={"option_id": opcion})

    _como("admin")
    resultados = client.get(f"/polls/{poll['id']}/results").json()
    assert resultados["total_votos"] == 1
    assert any(r["option_id"] == opcion and r["votos"] == 1 for r in resultados["resultados"])


def test_results_visible_after_close_even_if_not_live(client):
    poll = _crear_votacion(client, fecha_cierre="2020-01-01", resultados_en_vivo=False)
    response = client.get(f"/polls/{poll['id']}/results")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_process_closures_marks_quorum_reached(client):
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()
    poll = _crear_votacion(client, fecha_cierre="2026-09-01")
    opcion = poll["opciones"][0]["id"]

    _como("residente", property_id=prop["id"])
    client.post(f"/polls/{poll['id']}/vote", json={"option_id": opcion})

    provider = FakeNotificationProvider()
    async with client.db_session_factory() as db:
        resultado = await process_poll_closures(db, provider, date(2026, 9, 5))

    assert resultado == {"quorum_alcanzado": 1, "reactivadas": 0}
    _como("admin")
    assert client.get(f"/polls/{poll['id']}").json()["quorum_alcanzado"] is True


@pytest.mark.asyncio
async def test_process_closures_reactivates_when_quorum_not_reached(client):
    client.post("/properties", json={"identificador": "Casa 1"})
    client.post("/properties", json={"identificador": "Casa 2"})  # 2 viviendas, 0 votos: 0% participación
    poll = _crear_votacion(client, fecha_cierre="2026-09-01")

    provider = FakeNotificationProvider()
    async with client.db_session_factory() as db:
        resultado = await process_poll_closures(db, provider, date(2026, 9, 5))

    assert resultado == {"quorum_alcanzado": 0, "reactivadas": 1}
    assert len(provider.enviados) == 0  # nadie tiene teléfono registrado (no hay residentes ligados)

    actualizada = client.get(f"/polls/{poll['id']}").json()
    assert actualizada["reactivada"] is True
    assert actualizada["fecha_cierre"] == "2026-09-08"  # +7 días
    assert actualizada["quorum_alcanzado"] is False


@pytest.mark.asyncio
async def test_process_closures_does_not_reactivate_a_second_time(client):
    client.post("/properties", json={"identificador": "Casa 1"})
    poll = _crear_votacion(client, fecha_cierre="2026-09-01")

    provider = FakeNotificationProvider()
    async with client.db_session_factory() as db:
        primera = await process_poll_closures(db, provider, date(2026, 9, 5))
    assert primera["reactivadas"] == 1

    async with client.db_session_factory() as db:
        segunda = await process_poll_closures(db, provider, date(2026, 9, 20))  # después de la nueva fecha_cierre

    assert segunda == {"quorum_alcanzado": 0, "reactivadas": 0}  # ya se había reactivado una vez, no se repite

    _como("admin")
    final = client.get(f"/polls/{poll['id']}").json()
    assert final["quorum_alcanzado"] is False
    assert final["reactivada"] is True


def test_get_unknown_poll_404(client):
    response = client.get(f"/polls/{uuid.uuid4()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_concurrent_double_vote_from_same_property_is_rejected_cleanly(client):
    """
    Revisión de code-review (finding #9): cast_vote() ya estaba protegido a
    nivel de base de datos por UniqueConstraint(poll_id, property_id), pero
    el commit no capturaba el IntegrityError que esa restricción lanza bajo
    una carrera real — dos votos simultáneos de la misma vivienda daban un
    500 sin capturar en vez del VotoInvalido("ya_voto") limpio.
    """
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()
    poll = _crear_votacion(client)
    opcion = poll["opciones"][0]["id"]

    async def intentar():
        async with client.db_session_factory() as db:
            try:
                await cast_vote(db, uuid.UUID(poll["id"]), uuid.UUID(prop["id"]), uuid.UUID(opcion))
                return "ok"
            except VotoInvalido as exc:
                return exc.motivo

    resultados = await asyncio.gather(intentar(), intentar())

    assert resultados.count("ok") == 1
    assert resultados.count("ya_voto") == 1
