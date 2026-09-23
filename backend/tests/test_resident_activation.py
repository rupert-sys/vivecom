"""
POST /residents/activar y GET /residents/activar/preview: un residente reclama la cuenta de vivienda que
provision_tenant_con_casas() creó en bloque (sin activar, ver UserAccount.activada) con sus propios datos.
Igual que /auth/login (ver test_auth.py), corren contra la BD real sin pasar por get_tenant_db — se les aplica
el mismo truco: parchar tenant_session para que reutilice el SQLite en memoria del fixture `client`.
"""

import asyncio
import uuid
from contextlib import asynccontextmanager
from unittest.mock import patch

from sqlalchemy import select

import app.api.residents as residents_module
from app.api.deps import get_current_user
from app.core.database import control_session
from app.core.database_base import ControlBase, TenantBase
from app.main import app
from app.models.property import Property
from app.models.resident import Resident, ResidentProperty
from app.models.tenant import Tenant
from app.models.user import UserAccount
from app.models.user_lookup import UserLookup
from app.services.payment_reference import generate_payment_reference

TEST_TENANT_ID = str(uuid.uuid4())
NOMBRE_CONDOMINIO = "Condominio Arequipa"


async def _crear_tablas(client):
    async with client.db_session_factory() as session:
        conn = await session.connection()
        await conn.run_sync(TenantBase.metadata.create_all)
        await conn.run_sync(ControlBase.metadata.create_all)
        await session.commit()


async def _seed_casa_sin_activar(client, numero: int = 1) -> uuid.UUID:
    """Reproduce lo que provision_tenant_con_casas() deja para una vivienda: Property + cuenta sin activar."""
    from app.core.provisioning import _HASH_CENTINELA_SIN_ACTIVAR
    from app.models.user import Rol

    await _crear_tablas(client)
    user_id = uuid.uuid4()
    async with client.db_session_factory() as db:
        db.add(
            Tenant(
                id=uuid.UUID(TEST_TENANT_ID), nombre=NOMBRE_CONDOMINIO, clabe_destino=None,
                precio_por_vivienda=25.00, schema_name="test",
            )
        )
        identificador = f"Casa {numero}"
        referencia = await generate_payment_reference(identificador, db)
        casa = Property(identificador=identificador, referencia_pago=referencia)
        db.add(casa)
        await db.flush()
        email = f"casa{numero}@arequipa.com.mx"
        db.add(UserLookup(email=email, tenant_id=uuid.UUID(TEST_TENANT_ID), user_id=user_id))
        db.add(
            UserAccount(
                id=user_id, email=email, password_hash=_HASH_CENTINELA_SIN_ACTIVAR, rol=Rol.residente,
                property_id=casa.id, activada=False,
            )
        )
        await db.commit()
    return casa.id


def _preparar(client):
    """Habilita las rutas públicas de activación sobre el mismo SQLite en memoria del fixture `client`."""

    async def override_control_session():
        async with client.db_session_factory() as session:
            yield session

    app.dependency_overrides[control_session] = override_control_session
    del app.dependency_overrides[get_current_user]  # son rutas públicas, sin sesión

    @asynccontextmanager
    async def fake_tenant_session(schema_name):
        async with client.db_session_factory() as session:
            yield session

    return patch.object(residents_module, "tenant_session", fake_tenant_session)


def test_preview_regresa_el_email_de_la_vivienda(client):
    asyncio.run(_seed_casa_sin_activar(client))

    with _preparar(client):
        response = client.get(
            "/residents/activar/preview", params={"nombre_condominio": NOMBRE_CONDOMINIO, "numero_de_casa": 1}
        )

    assert response.status_code == 200
    assert response.json() == {"email": "casa1@arequipa.com.mx", "identificador": "Casa 1"}


def test_preview_de_un_condominio_que_no_existe_es_404(client):
    asyncio.run(_crear_tablas(client))

    with _preparar(client):
        response = client.get(
            "/residents/activar/preview", params={"nombre_condominio": "No existe", "numero_de_casa": 1}
        )

    assert response.status_code == 404


def test_preview_de_un_numero_de_casa_que_no_existe_es_404(client):
    asyncio.run(_seed_casa_sin_activar(client))

    with _preparar(client):
        response = client.get(
            "/residents/activar/preview", params={"nombre_condominio": NOMBRE_CONDOMINIO, "numero_de_casa": 99}
        )

    assert response.status_code == 404


def test_activar_crea_el_residente_lo_liga_a_la_vivienda_y_regresa_un_token(client):
    casa_id = asyncio.run(_seed_casa_sin_activar(client))

    with _preparar(client):
        response = client.post(
            "/residents/activar",
            json={
                "nombre_condominio": NOMBRE_CONDOMINIO, "numero_de_casa": 1, "nombre_completo": "Ana Torres",
                "rol": "propietario", "telefono": "5551234567", "password": "clave-de-ana-1",
            },
        )

    assert response.status_code == 200
    assert "access_token" in response.json()

    async def _verificar():
        async with client.db_session_factory() as db:
            cuenta = (
                await db.execute(select(UserAccount).where(UserAccount.email == "casa1@arequipa.com.mx"))
            ).scalar_one()
            assert cuenta.activada is True
            assert cuenta.resident_id is not None

            residente = await db.get(Resident, cuenta.resident_id)
            assert residente.nombre == "Ana Torres"
            assert residente.telefono == "5551234567"

            vinculo = (
                await db.execute(
                    select(ResidentProperty).where(
                        ResidentProperty.resident_id == residente.id, ResidentProperty.property_id == casa_id
                    )
                )
            ).scalar_one()
            assert vinculo.rol.value == "propietario"

    asyncio.run(_verificar())


def test_activar_una_vivienda_ya_activada_es_404(client):
    asyncio.run(_seed_casa_sin_activar(client))
    payload = {
        "nombre_condominio": NOMBRE_CONDOMINIO, "numero_de_casa": 1, "nombre_completo": "Ana Torres",
        "rol": "propietario", "telefono": "5551234567", "password": "clave-de-ana-1",
    }

    with _preparar(client):
        primera = client.post("/residents/activar", json=payload)
        segunda = client.post("/residents/activar", json={**payload, "password": "otra-clave-2"})

    assert primera.status_code == 200
    assert segunda.status_code == 404


def test_dos_condominios_con_el_mismo_nombre_dan_409_en_vez_de_adivinar(client):
    asyncio.run(_seed_casa_sin_activar(client))

    async def _duplicar():
        async with client.db_session_factory() as db:
            db.add(
                Tenant(
                    id=uuid.uuid4(), nombre=NOMBRE_CONDOMINIO, clabe_destino=None, precio_por_vivienda=25.00,
                    schema_name="test-2",
                )
            )
            await db.commit()

    asyncio.run(_duplicar())

    with _preparar(client):
        response = client.get(
            "/residents/activar/preview", params={"nombre_condominio": NOMBRE_CONDOMINIO, "numero_de_casa": 1}
        )

    assert response.status_code == 409
