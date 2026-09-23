"""
POST /auth/login. Ver también F2-21 (auditoría OWASP): timing side-channel
en el intento de enumerar emails registrados por el tiempo de respuesta.
"""

import asyncio
import uuid
from contextlib import asynccontextmanager
from unittest.mock import patch

import app.api.auth as auth_module
from app.api.deps import get_current_user
from app.core.database import control_session
from app.core.database_base import ControlBase, TenantBase
from app.core.security import hash_password
from app.main import app
from app.models.tenant import Tenant
from app.models.user import UserAccount
from app.models.user_lookup import UserLookup

TEST_EMAIL = "admin@condominio-test.mx"
TEST_PASSWORD = "SuperSecreta123"


async def _crear_tablas(client):
    # Ninguno de los endpoints de /auth/login pasa por Depends(get_tenant_db)
    # (que en el fixture `client` crea las tablas la primera vez que se usa)
    # — aquí se necesita crearlas explícitamente antes de sembrar datos.
    async with client.db_session_factory() as session:
        conn = await session.connection()
        await conn.run_sync(TenantBase.metadata.create_all)
        await conn.run_sync(ControlBase.metadata.create_all)
        await session.commit()


async def _seed_login(client):
    from tests.conftest import TEST_TENANT_ID

    await _crear_tablas(client)
    user_id = uuid.uuid4()
    async with client.db_session_factory() as db:
        db.add(
            Tenant(
                id=uuid.UUID(TEST_TENANT_ID), nombre="Condominio de prueba", clabe_destino="012180001547896321",
                precio_por_vivienda=25.00, schema_name="test",
            )
        )
        db.add(UserLookup(email=TEST_EMAIL, tenant_id=uuid.UUID(TEST_TENANT_ID), user_id=user_id))
        db.add(
            UserAccount(
                id=user_id, email=TEST_EMAIL, password_hash=hash_password(TEST_PASSWORD), rol="admin", property_id=None
            )
        )
        await db.commit()


def _preparar_login(client):
    """Habilita /auth/login sobre el mismo SQLite en memoria del fixture `client`."""

    async def override_control_session():
        async with client.db_session_factory() as session:
            yield session

    app.dependency_overrides[control_session] = override_control_session
    # /auth/login corre ANTES de que exista una sesión autenticada — se
    # necesita quitar el override de admin del fixture `client` para que la
    # ruta real (sin JWT) decida qué hacer, no el override de pruebas.
    del app.dependency_overrides[get_current_user]

    @asynccontextmanager
    async def fake_tenant_session(schema_name):
        async with client.db_session_factory() as session:
            yield session

    return fake_tenant_session


def test_login_with_correct_credentials_returns_a_token(client):
    asyncio.run(_seed_login(client))
    fake_tenant_session = _preparar_login(client)

    with patch.object(auth_module, "tenant_session", fake_tenant_session):
        response = client.post("/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})

    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_with_wrong_password_is_rejected(client):
    asyncio.run(_seed_login(client))
    fake_tenant_session = _preparar_login(client)

    with patch.object(auth_module, "tenant_session", fake_tenant_session):
        response = client.post("/auth/login", json={"email": TEST_EMAIL, "password": "incorrecta"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Credenciales inválidas"


def test_login_with_nonexistent_email_is_rejected_with_the_same_message(client):
    asyncio.run(_crear_tablas(client))
    _preparar_login(client)

    response = client.post("/auth/login", json={"email": "no-existe@condominio-test.mx", "password": "loquesea"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Credenciales inválidas"


async def _seed_login_sin_activar(client):
    """Cuenta de vivienda creada en bloque por /signup, sin reclamar todavía (ver UserAccount.activada)."""
    from tests.conftest import TEST_TENANT_ID

    await _crear_tablas(client)
    user_id = uuid.uuid4()
    async with client.db_session_factory() as db:
        db.add(
            Tenant(
                id=uuid.UUID(TEST_TENANT_ID), nombre="Condominio de prueba", clabe_destino="012180001547896321",
                precio_por_vivienda=25.00, schema_name="test",
            )
        )
        db.add(UserLookup(email="casa1@arequipa.com.mx", tenant_id=uuid.UUID(TEST_TENANT_ID), user_id=user_id))
        db.add(
            UserAccount(
                id=user_id, email="casa1@arequipa.com.mx", password_hash=hash_password("lo-que-sea"),
                rol="residente", activada=False,
            )
        )
        await db.commit()


def test_login_a_una_cuenta_sin_activar_da_un_mensaje_claro(client):
    asyncio.run(_seed_login_sin_activar(client))
    fake_tenant_session = _preparar_login(client)

    with patch.object(auth_module, "tenant_session", fake_tenant_session):
        response = client.post("/auth/login", json={"email": "casa1@arequipa.com.mx", "password": "lo-que-sea"})

    assert response.status_code == 403
    assert "no se activó" in response.json()["detail"]


def test_login_incluye_debe_cambiar_password_en_el_token(client):
    """
    Alta por /signup: el admin nace con debe_cambiar_password=True (contraseña temporal = nombre del
    condominio) — el panel lo lee del JWT para forzar la pantalla de cambio en el primer login.
    """
    import base64
    import json

    from tests.conftest import TEST_TENANT_ID

    asyncio.run(_crear_tablas(client))
    user_id = uuid.uuid4()

    async def _seed():
        async with client.db_session_factory() as db:
            db.add(
                Tenant(
                    id=uuid.UUID(TEST_TENANT_ID), nombre="Condominio de prueba", clabe_destino="012180001547896321",
                    precio_por_vivienda=25.00, schema_name="test",
                )
            )
            db.add(UserLookup(email=TEST_EMAIL, tenant_id=uuid.UUID(TEST_TENANT_ID), user_id=user_id))
            db.add(
                UserAccount(
                    id=user_id, email=TEST_EMAIL, password_hash=hash_password(TEST_PASSWORD), rol="admin",
                    debe_cambiar_password=True,
                )
            )
            await db.commit()

    asyncio.run(_seed())
    fake_tenant_session = _preparar_login(client)

    with patch.object(auth_module, "tenant_session", fake_tenant_session):
        response = client.post("/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})

    token = response.json()["access_token"]
    payload_b64 = token.split(".")[1]
    payload_b64 += "=" * (-len(payload_b64) % 4)  # padding que JWT omite y base64 exige
    payload = json.loads(base64.urlsafe_b64decode(payload_b64))
    assert payload["debe_cambiar_password"] is True


def test_a_nonexistent_email_still_runs_a_bcrypt_verification(client):
    """
    F2-21: antes, un email inexistente respondía 401 de inmediato SIN correr
    verify_password() (sin bcrypt), mientras un email real siempre lo corría
    — una diferencia de tiempo de respuesta que permite enumerar cuentas
    registradas pese a que el mensaje de error es idéntico en ambos casos.
    Ahora se corre verify_password() contra un hash señuelo también en la
    rama de "no existe", para igualar el tiempo de respuesta.
    """
    asyncio.run(_crear_tablas(client))
    _preparar_login(client)

    with patch.object(auth_module, "verify_password", wraps=auth_module.verify_password) as spy:
        response = client.post("/auth/login", json={"email": "no-existe@condominio-test.mx", "password": "loquesea"})

    assert response.status_code == 401
    assert spy.call_count == 1
