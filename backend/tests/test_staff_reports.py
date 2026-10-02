"""
F3-04: dashboard ejecutivo agregado para VivecomStaff. Ver la nota de
alcance en app/models/vivecom_staff.py sobre por qué es un tipo de cuenta
separado, no un tenant más.
"""

import uuid
from contextlib import asynccontextmanager
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.services.executive_report_service as executive_report_service
from app.api.deps import get_current_user, get_tenant_db
from app.core.database import control_session
from app.core.database_base import ControlBase, TenantBase
from app.core.security import hash_password
from app.main import app
from app.models.tenant import Tenant
from app.models.vivecom_staff import VivecomStaff
from app.schemas.auth import CurrentUser

STAFF_EMAIL = "ops@vivecom.mx"
STAFF_PASSWORD = "PasswordDeStaff123"


async def _crear_tablas(client) -> None:
    # Ninguno de los endpoints de /staff/* pasa por Depends(get_tenant_db)
    # (que en el fixture `client` crea las tablas la primera vez que se usa)
    # — hay que crearlas explícitamente antes de sembrar datos. Mismo motivo
    # que test_auth.py.
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


def _preparar_staff_login(client):
    """Habilita /staff/login sobre el mismo SQLite en memoria del fixture `client`."""

    async def override_control_session():
        async with client.db_session_factory() as session:
            yield session

    app.dependency_overrides[control_session] = override_control_session


def _staff_headers(client) -> dict[str, str]:
    response = client.post("/staff/login", json={"email": STAFF_EMAIL, "password": STAFF_PASSWORD})
    assert response.status_code == 200, response.json()
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_staff_login_with_correct_credentials_returns_a_token(client):
    import asyncio

    asyncio.run(_crear_cuenta_staff(client))
    _preparar_staff_login(client)

    headers = _staff_headers(client)
    assert "Authorization" in headers


def test_staff_login_with_wrong_password_is_rejected(client):
    import asyncio

    asyncio.run(_crear_cuenta_staff(client))
    _preparar_staff_login(client)

    response = client.post("/staff/login", json={"email": STAFF_EMAIL, "password": "incorrecta"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Credenciales inválidas"


def test_staff_login_with_nonexistent_email_is_rejected(client):
    import asyncio

    asyncio.run(_crear_tablas(client))
    _preparar_staff_login(client)

    response = client.post("/staff/login", json={"email": "no-existe@vivecom.mx", "password": "loquesea"})
    assert response.status_code == 401


def test_a_tenant_token_cannot_reach_the_executive_dashboard(client):
    """Un admin de un condominio normal (JWT sin claim `staff: true`) no debe poder ver el resumen agregado."""
    # El fixture `client` normalmente usa get_current_user overridden (sin JWT
    # real) — para esta prueba interesa el rechazo de get_current_staff ante
    # CUALQUIER cosa que no traiga `staff: true`, así que se prueba
    # directamente contra un token de tenant real generado con create_access_token.
    from app.core.security import create_access_token

    token = create_access_token(
        subject=str(uuid.uuid4()), tenant_id=str(uuid.uuid4()), schema_name="test", rol="admin", property_id=None
    )
    response = client.get("/staff/reportes/resumen-ejecutivo", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_executive_summary_requires_a_staff_token(client):
    response = client.get("/staff/reportes/resumen-ejecutivo")
    assert response.status_code == 403  # HTTPBearer sin credenciales


@pytest.mark.asyncio
async def test_executive_summary_aggregates_across_multiple_tenants(client):
    """
    Siembra dos tenants con datos distintos (cada uno en su propio motor
    SQLite aislado, ya que a diferencia de Postgres real, SQLite no tiene
    schemas de verdad para aislarlos dentro de la misma base) y verifica que
    el resumen ejecutivo trae el desglose correcto por tenant Y los totales
    agregados correctos.
    """
    await _crear_cuenta_staff(client)
    _preparar_staff_login(client)
    staff_headers = _staff_headers(client)

    # --- Tenant A (el del fixture `client`, schema "test"): 1 vivienda,
    # 1 cargo pagado de $1000, 1 incidencia abierta.
    client.post("/properties", json={"identificador": "Casa A1"})
    # F0-12: cuotas y cargos son de tesorería, no del administrador.
    tenant_id_a = app.dependency_overrides[get_current_user]().tenant_id
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id=str(uuid.uuid4()), tenant_id=tenant_id_a, schema_name="test", rol="tesorero", property_id=None
    )
    client.post("/fees", json={"monto": 1000.00, "periodicidad": "mensual", "activa_desde": "2026-01-01"})
    client.post("/fees/generate-charges", params={"periodo": "2026-01-01"})
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id=str(uuid.uuid4()), tenant_id=tenant_id_a, schema_name="test", rol="admin", property_id=None
    )  # las incidencias no las gestiona tesorería
    client.post("/incidents", json={"descripcion": "Fuga de agua"})

    # --- Tenant B: engine SQLite propio, sembrado reutilizando los mismos
    # endpoints HTTP pero apuntando get_tenant_db a su motor.
    engine_b = create_async_engine(
        "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    session_factory_b = async_sessionmaker(engine_b, expire_on_commit=False, class_=AsyncSession)
    async with engine_b.begin() as conn:
        await conn.run_sync(TenantBase.metadata.create_all)

    tenant_b_id = uuid.uuid4()
    async with client.db_session_factory() as db:
        db.add(
            Tenant(
                id=tenant_b_id, nombre="Condominio B", clabe_destino="012180009999999999",
                precio_por_vivienda=25.00, schema_name="test-b",
            )
        )
        await db.commit()

    async def override_get_tenant_db_b():
        async with session_factory_b() as session:
            yield session

    app.dependency_overrides[get_tenant_db] = override_get_tenant_db_b
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id=str(uuid.uuid4()), tenant_id=str(tenant_b_id), schema_name="test-b", rol="admin", property_id=None
    )

    # 2 viviendas, 2 cargos de $2000 c/u (uno pagado vía depósito directo no
    # se hace aquí — se deja pendiente/vencido a propósito para que la deuda
    # y la tasa de morosidad de tenant B aporten algo distinto de tenant A).
    client.post("/properties", json={"identificador": "Casa B1"})
    client.post("/properties", json={"identificador": "Casa B2"})
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id=str(uuid.uuid4()), tenant_id=str(tenant_b_id), schema_name="test-b", rol="tesorero", property_id=None
    )  # F0-12: cuotas y cargos son de tesorería, no del administrador
    client.post("/fees", json={"monto": 2000.00, "periodicidad": "mensual", "activa_desde": "2026-01-01"})
    client.post("/fees/generate-charges", params={"periodo": "2026-01-01"})
    client.post("/fees/apply-late-surcharges", params={"hoy": "2026-02-01"})

    # --- Restaura el fixture original (tenant A) y arma el resumen ejecutivo,
    # con tenant_session() enrutando cada schema a su propio motor.
    async def override_get_current_admin_a():
        from tests.conftest import TEST_TENANT_ID

        return CurrentUser(user_id=str(uuid.uuid4()), tenant_id=TEST_TENANT_ID, schema_name="test", rol="admin", property_id=None)

    app.dependency_overrides[get_tenant_db] = client.db_session_factory  # type: ignore[assignment]
    app.dependency_overrides[get_current_user] = override_get_current_admin_a

    @asynccontextmanager
    async def fake_tenant_session(schema_name: str):
        factory = session_factory_b if schema_name == "test-b" else client.db_session_factory
        async with factory() as session:
            yield session

    with patch.object(executive_report_service, "tenant_session", fake_tenant_session):
        response = client.get(
            "/staff/reportes/resumen-ejecutivo", params={"hoy": "2026-01-15"}, headers=staff_headers
        )

    assert response.status_code == 200, response.json()
    body = response.json()

    por_tenant = {t["nombre"]: t for t in body["tenants"]}
    assert por_tenant["Condominio de prueba"]["viviendas"] == 1
    assert por_tenant["Condominio de prueba"]["ingresos_mes_actual"] == 0.0  # no hubo depósito, solo se generó el cargo
    assert por_tenant["Condominio de prueba"]["deuda_pendiente"] == 1000.0
    assert por_tenant["Condominio de prueba"]["incidencias_abiertas"] == 1

    assert por_tenant["Condominio B"]["viviendas"] == 2
    assert por_tenant["Condominio B"]["cargos_vencidos"] == 2
    assert por_tenant["Condominio B"]["deuda_pendiente"] > 4000.0  # 2 cargos de 2000 + recargo por mora

    totales = body["totales"]
    assert totales["total_condominios"] == 2
    assert totales["total_viviendas"] == 3
    assert totales["incidencias_abiertas"] == 1
    assert totales["tasa_morosidad"] == pytest.approx(2 / 3)  # 2 de los 3 cargos totales (1 A + 2 B) están vencidos

    await engine_b.dispose()
