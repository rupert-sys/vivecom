"""
F3-02 / LFPDPPP: aviso de privacidad, consentimiento, y derechos ARCO de
acceso (exportar) y cancelación (anonimizar).
"""

import uuid

import pytest

from app.api.deps import get_current_user
from app.main import app
from app.models.user import UserAccount
from app.schemas.auth import CurrentUser


def _tenant_id() -> str:
    return app.dependency_overrides[get_current_user]().tenant_id


def _como(rol: str, user_id: str, property_id: str | None = None):
    tenant_id = _tenant_id()

    def override():
        return CurrentUser(user_id=user_id, tenant_id=tenant_id, schema_name="test", rol=rol, property_id=property_id)

    app.dependency_overrides[get_current_user] = override


async def _crear_residente_con_cuenta(client, nombre="Ana Pérez", telefono="5511112222"):
    resident = client.post("/residents", json={"nombre": nombre, "telefono": telefono, "email": "ana@example.com"}).json()
    user_id = uuid.uuid4()
    async with client.db_session_factory() as db:
        db.add(
            UserAccount(
                id=user_id, resident_id=uuid.UUID(resident["id"]), email=f"{user_id}@test.com", password_hash="x",
                rol="residente",
            )
        )
        await db.commit()
    return resident, str(user_id)


def test_privacy_notice_is_public_and_flags_it_needs_legal_review(client):
    response = client.get("/privacy-notice")
    assert response.status_code == 200
    assert "REQUIERE REVISIÓN LEGAL" in response.json()["texto"]


def test_account_without_resident_profile_cannot_use_arco_endpoints(client):
    # el fixture `client` usa un admin sin resident_id
    assert client.post("/me/privacy-notice/accept").status_code == 400
    assert client.get("/me/data-export").status_code == 400
    assert client.post("/me/request-erasure").status_code == 400


@pytest.mark.asyncio
async def test_accept_privacy_notice(client):
    _resident, user_id = await _crear_residente_con_cuenta(client)
    _como("residente", user_id)

    response = client.post("/me/privacy-notice/accept")
    assert response.status_code == 200
    assert response.json()["aviso_privacidad_aceptado_en"] is not None


@pytest.mark.asyncio
async def test_data_export_includes_properties_and_votes(client):
    resident, user_id = await _crear_residente_con_cuenta(client)
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()
    client.post(f"/properties/{prop['id']}/residents", json={"resident_id": resident["id"], "rol": "propietario"})

    _como("vocero", str(uuid.uuid4()))
    poll = client.post(
        "/polls", json={"pregunta": "¿?", "opciones": ["Sí", "No"], "fecha_cierre": "2026-12-31"}
    ).json()

    _como("residente", user_id, property_id=prop["id"])
    client.post(f"/polls/{poll['id']}/vote", json={"option_id": poll["opciones"][0]["id"]})

    export = client.get("/me/data-export").json()
    assert export["residente"]["nombre"] == "Ana Pérez"
    assert len(export["viviendas"]) == 1
    assert len(export["votos_emitidos"]) == 1


@pytest.mark.asyncio
async def test_erasure_anonymizes_resident_but_keeps_the_row(client):
    resident, user_id = await _crear_residente_con_cuenta(client)
    _como("residente", user_id)

    response = client.post("/me/request-erasure")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == resident["id"]
    assert body["nombre"] != "Ana Pérez"
    assert body["telefono"] == ""
    assert body["email"] is None

    # el residente sigue existiendo (se conserva por integridad de ResidentProperty/incidencias).
    # GET /residents/{id} es staff-only desde F2-21 (antes cualquier residente
    # podía leer el registro de CUALQUIER OTRO residente por este mismo
    # endpoint, un IDOR real) — se verifica como admin, no como el propio
    # residente, ya que esa ya no es una ruta de acceso legítima para él.
    _como("admin", user_id)
    assert client.get(f"/residents/{resident['id']}").status_code == 200
