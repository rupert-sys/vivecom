"""
Portal de administrador principal (staff Vivecom): listar/ver/activar-desactivar/editar condominios desde
un solo lugar (ver api/staff_tenants.py y la nota de alcance en app/models/vivecom_staff.py).

POST /staff/tenants no se prueba de punta a punta aquí, por el mismo motivo documentado en test_signup.py:
usa provision_tenant_con_casas(), que ejecuta CREATE SCHEMA / SET search_path (sintaxis específica de
Postgres que SQLite no entiende). Se prueba en cambio la validación de TenantCreateRequest — el flujo real
(mismo provision_tenant_con_casas que /signup) ya se verificó a mano contra Postgres real.

Por el mismo motivo, el camino FELIZ de DELETE /staff/tenants/{id} (que sí borra, con DROP SCHEMA) tampoco
se prueba aquí — se probaron a mano contra Postgres real los dos candados (contraseña correcta y que ya
esté en la papelera) y que después de eso el schema y el registro de verdad desaparecen. Lo que SÍ se
prueba con SQLite son los candados mismos (400 si no está en la papelera, 403 si la contraseña es
incorrecta) — ninguno de los dos llega a ejecutar el DROP SCHEMA.
"""

import asyncio
import uuid
from contextlib import asynccontextmanager
from unittest.mock import patch

import pytest
from pydantic import ValidationError

import app.api.staff_tenants as staff_tenants_module
from app.core.database import control_session
from app.core.database_base import ControlBase, TenantBase
from app.core.security import hash_password
from app.main import app
from app.models.property import Property
from app.models.tenant import Tenant
from app.models.user import UserAccount
from app.models.user_lookup import UserLookup
from app.models.vivecom_staff import VivecomStaff
from app.schemas.staff_tenant import MAX_CASAS_POR_SIGNUP, TenantCreateRequest

STAFF_EMAIL = "ops@vivecom.mx"
STAFF_PASSWORD = "PasswordDeStaff123"


async def _crear_tablas(client) -> None:
    async with client.db_session_factory() as session:
        conn = await session.connection()
        await conn.run_sync(TenantBase.metadata.create_all)
        await conn.run_sync(ControlBase.metadata.create_all)
        await session.commit()


async def _crear_cuenta_staff(client) -> None:
    await _crear_tablas(client)
    async with client.db_session_factory() as db:
        db.add(VivecomStaff(email=STAFF_EMAIL, password_hash=hash_password(STAFF_PASSWORD)))
        await db.commit()


def _preparar_staff(client):
    """Habilita /staff/* sobre el mismo SQLite en memoria del fixture `client`."""

    async def override_control_session():
        async with client.db_session_factory() as session:
            yield session

    app.dependency_overrides[control_session] = override_control_session

    @asynccontextmanager
    async def fake_tenant_session(schema_name):
        async with client.db_session_factory() as session:
            yield session

    return fake_tenant_session


def _staff_headers(client) -> dict[str, str]:
    response = client.post("/staff/login", json={"email": STAFF_EMAIL, "password": STAFF_PASSWORD})
    assert response.status_code == 200, response.json()
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _sembrar_tenant(client, *, nombre="Condominio de prueba", schema_name="test", activo=True) -> uuid.UUID:
    tenant_id = uuid.uuid4()
    async with client.db_session_factory() as db:
        db.add(
            Tenant(
                id=tenant_id, nombre=nombre, precio_por_vivienda=25.00, schema_name=schema_name, activo=activo,
            )
        )
        db.add(Property(identificador="Casa 1", referencia_pago="REF001"))
        db.add(
            UserAccount(
                email=f"administracion@{schema_name}.mx", password_hash=hash_password("lo-que-sea"), rol="admin",
            )
        )
        await db.commit()
    return tenant_id


def test_listar_tenants_requiere_token_de_staff(client):
    response = client.get("/staff/tenants")
    assert response.status_code == 403


def test_listar_tenants_incluye_viviendas_y_estado(client):
    async def _preparar():
        await _crear_cuenta_staff(client)
        return await _sembrar_tenant(client)

    tenant_id = asyncio.run(_preparar())
    fake_tenant_session = _preparar_staff(client)
    headers = _staff_headers(client)

    with patch.object(staff_tenants_module, "tenant_session", fake_tenant_session):
        response = client.get("/staff/tenants", headers=headers)

    assert response.status_code == 200, response.json()
    tenants = response.json()
    assert len(tenants) == 1
    assert tenants[0]["tenant_id"] == str(tenant_id)
    assert tenants[0]["viviendas"] == 1
    assert tenants[0]["activo"] is True


def test_obtener_tenant_incluye_el_email_del_admin(client):
    async def _preparar():
        await _crear_cuenta_staff(client)
        return await _sembrar_tenant(client, schema_name="arequipa")

    tenant_id = asyncio.run(_preparar())
    fake_tenant_session = _preparar_staff(client)
    headers = _staff_headers(client)

    with patch.object(staff_tenants_module, "tenant_session", fake_tenant_session):
        response = client.get(f"/staff/tenants/{tenant_id}", headers=headers)

    assert response.status_code == 200, response.json()
    assert response.json()["email_admin"] == "administracion@arequipa.mx"


def test_obtener_un_tenant_inexistente_da_404(client):
    asyncio.run(_crear_cuenta_staff(client))
    _preparar_staff(client)
    headers = _staff_headers(client)

    response = client.get(f"/staff/tenants/{uuid.uuid4()}", headers=headers)
    assert response.status_code == 404


def test_desactivar_un_tenant_bloquea_su_login(client):
    """La razón de ser de `activo`: un condominio suspendido desde el portal no puede iniciar sesión (ver
    api/auth.py). Se prueba el efecto completo — PATCH lo desactiva, /auth/login del propio tenant lo rechaza."""
    import app.api.auth as auth_module
    from app.api.deps import get_current_user

    async def _preparar():
        await _crear_cuenta_staff(client)
        tenant_id = await _sembrar_tenant(client)
        # /auth/login resuelve el tenant vía UserLookup (tabla de control) antes de tocar el UserAccount —
        # el email debe coincidir con el que _sembrar_tenant ya usó al crear el admin ("administracion@test.mx").
        async with client.db_session_factory() as db:
            db.add(UserLookup(email="administracion@test.mx", tenant_id=tenant_id, user_id=uuid.uuid4()))
            await db.commit()
        return tenant_id

    tenant_id = asyncio.run(_preparar())
    fake_tenant_session = _preparar_staff(client)
    headers = _staff_headers(client)

    with patch.object(staff_tenants_module, "tenant_session", fake_tenant_session):
        response = client.patch(f"/staff/tenants/{tenant_id}", json={"activo": False}, headers=headers)
    assert response.status_code == 200, response.json()
    assert response.json()["activo"] is False

    # /auth/login usa su propio control_session/tenant_session — se preparan igual que en test_auth.py.
    del app.dependency_overrides[get_current_user]

    with patch.object(auth_module, "tenant_session", fake_tenant_session):
        login_response = client.post(
            "/auth/login", json={"email": "administracion@test.mx", "password": "lo-que-sea"}
        )
    assert login_response.status_code == 403
    assert "suspendido" in login_response.json()["detail"]


def test_editar_nombre_y_cuota(client):
    async def _preparar():
        await _crear_cuenta_staff(client)
        return await _sembrar_tenant(client)

    tenant_id = asyncio.run(_preparar())
    fake_tenant_session = _preparar_staff(client)
    headers = _staff_headers(client)

    with patch.object(staff_tenants_module, "tenant_session", fake_tenant_session):
        response = client.patch(
            f"/staff/tenants/{tenant_id}",
            json={"nombre": "Residencial Renombrado", "precio_por_vivienda": 40.0},
            headers=headers,
        )

    assert response.status_code == 200, response.json()
    body = response.json()
    assert body["nombre"] == "Residencial Renombrado"
    assert body["precio_por_vivienda"] == 40.0


def test_enviar_a_papelera_lo_saca_del_listado_y_lo_desactiva(client):
    async def _preparar():
        await _crear_cuenta_staff(client)
        return await _sembrar_tenant(client)

    tenant_id = asyncio.run(_preparar())
    fake_tenant_session = _preparar_staff(client)
    headers = _staff_headers(client)

    with patch.object(staff_tenants_module, "tenant_session", fake_tenant_session):
        response = client.post(f"/staff/tenants/{tenant_id}/papelera", headers=headers)
        assert response.status_code == 200, response.json()
        body = response.json()
        assert body["en_papelera"] is True
        assert body["activo"] is False
        assert body["papelera_en"] is not None

        assert client.get("/staff/tenants", headers=headers).json() == []

        papelera = client.get("/staff/tenants/papelera", headers=headers).json()
        assert len(papelera) == 1
        assert papelera[0]["tenant_id"] == str(tenant_id)


def test_restaurar_de_papelera_lo_regresa_al_listado_y_lo_reactiva(client):
    async def _preparar():
        await _crear_cuenta_staff(client)
        return await _sembrar_tenant(client, activo=False)

    tenant_id = asyncio.run(_preparar())
    fake_tenant_session = _preparar_staff(client)
    headers = _staff_headers(client)

    with patch.object(staff_tenants_module, "tenant_session", fake_tenant_session):
        enviado = client.post(f"/staff/tenants/{tenant_id}/papelera", headers=headers)
        assert enviado.status_code == 200, enviado.json()

        restaurado = client.post(f"/staff/tenants/{tenant_id}/restaurar", headers=headers)
        assert restaurado.status_code == 200, restaurado.json()
        body = restaurado.json()
        assert body["en_papelera"] is False
        assert body["papelera_en"] is None
        assert body["activo"] is True

        assert client.get("/staff/tenants/papelera", headers=headers).json() == []
        listado = client.get("/staff/tenants", headers=headers).json()
        assert len(listado) == 1


def test_borrar_permanentemente_exige_que_ya_este_en_la_papelera(client):
    async def _preparar():
        await _crear_cuenta_staff(client)
        return await _sembrar_tenant(client)

    tenant_id = asyncio.run(_preparar())
    _preparar_staff(client)
    headers = _staff_headers(client)

    response = client.request(
        "DELETE", f"/staff/tenants/{tenant_id}", json={"password": STAFF_PASSWORD}, headers=headers
    )
    assert response.status_code == 400
    assert "papelera" in response.json()["detail"]


def test_borrar_permanentemente_exige_la_contrasena_correcta_del_staff(client):
    async def _preparar():
        await _crear_cuenta_staff(client)
        return await _sembrar_tenant(client)

    tenant_id = asyncio.run(_preparar())
    fake_tenant_session = _preparar_staff(client)
    headers = _staff_headers(client)

    with patch.object(staff_tenants_module, "tenant_session", fake_tenant_session):
        enviado = client.post(f"/staff/tenants/{tenant_id}/papelera", headers=headers)
        assert enviado.status_code == 200, enviado.json()

    response = client.request(
        "DELETE", f"/staff/tenants/{tenant_id}", json={"password": "esta-no-es"}, headers=headers
    )
    assert response.status_code == 403
    assert "incorrecta" in response.json()["detail"]


def test_payload_de_creacion_valido_no_lanza_error():
    TenantCreateRequest(
        nombre_condominio="Residencial Las Fuentes", cantidad_casas=60, nombre_admin="Ruperto Villalobos",
        telefono_admin="5555555555",
    )


def test_payload_de_creacion_rechaza_cantidad_de_casas_fuera_de_rango():
    with pytest.raises(ValidationError):
        TenantCreateRequest(
            nombre_condominio="Residencial Las Fuentes", cantidad_casas=0, nombre_admin="Ruperto Villalobos",
            telefono_admin="5555555555",
        )
    with pytest.raises(ValidationError):
        TenantCreateRequest(
            nombre_condominio="Residencial Las Fuentes", cantidad_casas=MAX_CASAS_POR_SIGNUP + 1,
            nombre_admin="Ruperto Villalobos", telefono_admin="5555555555",
        )
