"""
Fixture compartido para las pruebas: simula un usuario admin autenticado y
una base de datos SQLite en memoria en vez de Postgres real (más rápido para
CI). Las pruebas de integración contra Postgres real viven aparte.
"""

import tempfile
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user, get_link_tenant_db, get_tenant_db
from app.core.database_base import ControlBase, TenantBase
from app.main import app
from app.models.tenant import Tenant
from app.schemas.auth import CurrentUser
from app.services.file_storage import LocalFileStorage, set_storage

TEST_TENANT_ID = str(uuid.uuid4())


@pytest.fixture(autouse=True)
def almacenamiento_temporal():
    """Ninguna prueba escribe en ./storage: cada una tiene su propio directorio temporal."""
    with tempfile.TemporaryDirectory() as directorio:
        set_storage(LocalFileStorage(directorio))
        yield
        set_storage(None)


@pytest.fixture()
def client():
    # StaticPool es necesario: sin él, cada conexión nueva a ":memory:" crea
    # una base de datos vacía distinta, y los datos "desaparecen" entre requests.
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    tables_created = False

    async def override_get_tenant_db():
        nonlocal tables_created
        if not tables_created:
            async with engine.begin() as conn:
                # En Postgres real, TenantBase vive en el schema del tenant y
                # ControlBase en `public` — aquí, para simplificar, ambas
                # conviven en la misma base SQLite (el código de la app no
                # distingue entre schemas al hacer queries, solo Postgres sí).
                await conn.run_sync(TenantBase.metadata.create_all)
                await conn.run_sync(ControlBase.metadata.create_all)
            async with session_factory() as seed_session:
                seed_session.add(
                    Tenant(
                        id=uuid.UUID(TEST_TENANT_ID),
                        nombre="Condominio de prueba",
                        clabe_destino="012180001547896321",
                        precio_por_vivienda=25.00,
                        schema_name="test",
                    )
                )
                await seed_session.commit()
            tables_created = True
        async with session_factory() as session:
            yield session

    def override_get_current_admin():
        return CurrentUser(
            user_id=str(uuid.uuid4()), tenant_id=TEST_TENANT_ID,
            schema_name="test", rol="admin", property_id=None,
        )

    app.dependency_overrides[get_tenant_db] = override_get_tenant_db
    app.dependency_overrides[get_link_tenant_db] = override_get_tenant_db
    app.dependency_overrides[get_current_user] = override_get_current_admin

    with TestClient(app) as c:
        # Se expone el session_factory en el propio cliente de pruebas para
        # que las pruebas que lo necesiten (ej. verificar un monto exacto en
        # la base de datos) puedan consultarla directamente sin depender de
        # que exista un endpoint de lectura todavía.
        c.db_session_factory = session_factory
        yield c

    app.dependency_overrides.clear()
