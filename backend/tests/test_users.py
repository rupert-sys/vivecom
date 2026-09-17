"""
F2-18: gestión mínima de cuentas de personal — sin esto no había forma de
designar un aprobador de amenidades (F2-17) que no fuera el admin sembrado
al aprovisionar el tenant. Ningún endpoint existía para esto antes.
"""

import uuid

import pytest
from sqlalchemy import select

from app.api.deps import get_current_user
from app.main import app
from app.models.user_lookup import UserLookup
from app.schemas.auth import CurrentUser


def _tenant_id() -> str:
    return app.dependency_overrides[get_current_user]().tenant_id


def _como(rol: str):
    tenant_id = _tenant_id()

    def override():
        return CurrentUser(user_id=str(uuid.uuid4()), tenant_id=tenant_id, schema_name="test", rol=rol, property_id=None)

    app.dependency_overrides[get_current_user] = override


def test_admin_puede_crear_un_usuario_con_rol_comite_aprobador(client):
    response = client.post(
        "/users", json={"email": "aprobador@condo.mx", "password": "clave-temporal-123", "rol": "comite_aprobador"}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "aprobador@condo.mx"
    assert body["rol"] == "comite_aprobador"
    assert "password" not in body
    assert "password_hash" not in body


def test_no_se_puede_repetir_el_email(client):
    client.post("/users", json={"email": "vocero@condo.mx", "password": "clave-123456", "rol": "vocero"})
    response = client.post("/users", json={"email": "vocero@condo.mx", "password": "otra-clave", "rol": "guardia"})
    assert response.status_code == 409


def test_list_users_filtra_por_rol(client):
    client.post("/users", json={"email": "aprobador1@condo.mx", "password": "clave-123456", "rol": "comite_aprobador"})
    client.post("/users", json={"email": "aprobador2@condo.mx", "password": "clave-123456", "rol": "comite_aprobador"})
    client.post("/users", json={"email": "vocero@condo.mx", "password": "clave-123456", "rol": "vocero"})

    response = client.get("/users", params={"rol": "comite_aprobador"})
    assert response.status_code == 200
    emails = {u["email"] for u in response.json()}
    assert emails == {"aprobador1@condo.mx", "aprobador2@condo.mx"}


def test_list_users_sin_filtro_regresa_todos(client):
    client.post("/users", json={"email": "aprobador@condo.mx", "password": "clave-123456", "rol": "comite_aprobador"})
    client.post("/users", json={"email": "vocero@condo.mx", "password": "clave-123456", "rol": "vocero"})

    response = client.get("/users")
    assert len(response.json()) == 2


@pytest.mark.asyncio
async def test_crear_usuario_registra_en_user_lookup(client):
    """
    /auth/login resuelve el tenant de un email consultando user_lookup (schema
    de control) ANTES de siquiera abrir la sesión del tenant — sin ese
    registro, la cuenta nueva jamás podría iniciar sesión aunque exista en
    user_account. No se puede probar /auth/login de punta a punta aquí: usa
    control_session()/tenant_session() directamente (no get_tenant_db), que
    esta suite no sobreescribe — ningún otro test del proyecto lo hace
    tampoco, es un hueco preexistente del fixture, no de este cambio. Se
    verifica en cambio el efecto concreto que sí depende de create_user():
    que el registro en user_lookup exista con el tenant_id y user_id correctos.
    """
    creado = client.post(
        "/users", json={"email": "tesorero@condo.mx", "password": "clave-123456", "rol": "tesorero"}
    ).json()

    async with client.db_session_factory() as db:
        lookup = (await db.execute(select(UserLookup).where(UserLookup.email == "tesorero@condo.mx"))).scalar_one()

    assert str(lookup.user_id) == creado["id"]
    assert str(lookup.tenant_id) == _tenant_id()


def test_no_admin_no_puede_crear_ni_listar_usuarios(client):
    _como("guardia")
    assert client.post("/users", json={"email": "x@x.com", "password": "clave-123456", "rol": "guardia"}).status_code == 403
    assert client.get("/users").status_code == 403
