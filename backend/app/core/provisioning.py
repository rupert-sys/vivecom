"""
Aprovisiona un nuevo condominio: crea su schema de PostgreSQL, todas las
tablas del tenant dentro de él (property, resident, user_account, etc.), el
registro correspondiente en la tabla `tenant` del schema de control, y el
primer usuario administrador (sin esto no hay forma de iniciar sesión).

Uso:
    python -m app.core.provisioning "Residencial Las Fuentes" "012180001547896321" "admin@vivecom.mx" "clave-temporal-123"

provision_tenant_con_casas() es el camino que usa /signup (la landing de
bienvenida): además del admin, crea de una vez las viviendas y una cuenta de
residente SIN activar por cada una (ver UserAccount.activada) — el residente
la reclama desde la app con sus propios datos (POST /residents/activar).
"""

import asyncio
import secrets
import sys
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database_base import ControlBase, TenantBase
from app.core.security import hash_password
from app.models.clabe_change_log import ClabeChangeLog  # noqa: F401 — registra en ControlBase
from app.models.tenant import Tenant
from app.models.user import Rol, UserAccount
from app.models.user_lookup import UserLookup
from app.models.vivecom_staff import VivecomStaff  # noqa: F401 — registra en ControlBase (F3-04)
# Importar TODOS los modelos de tenant para que TenantBase.metadata los conozca
# antes de create_all() — si un modelo nuevo no se agrega aquí, TenantBase.metadata
# nunca se entera de que existe y create_all() no crea su tabla, sin ningún error
# visible hasta que un endpoint la use ("relation ... does not exist"). Revisión:
# esta lista se quedó fija en 6 módulos desde que se escribió (época de F1-07) y
# nunca se actualizó según crecía el proyecto — todo tenant aprovisionado con
# este script le faltaban budget, expense, announcement, incident, poll, amenity,
# access_log, package, visitor_qr, vehicle, lost_found_item y reservation (Fases 1
# y 2 casi completas). migrate_add_tables.py sí se había mantenido al día con la
# lista completa; se copia de ahí en vez de mantener dos listas por separado.
from app.models import (  # noqa: F401
    access_log, amenity, announcement, budget, expense, fee, fee_charge, incident, lost_found_item, package,
    payment, payment_agreement, payment_proof, poll, property, reglamento, reservation, resident, stored_file, user, vehicle,
    visitor_qr,
)
from app.services.payment_reference import generate_payment_reference

# Nadie puede haber escrito este password: 32 bytes al azar, jamás comunicados a nadie, con hash calculado una
# sola vez por proceso (bcrypt es caro a propósito) — es el password_hash de TODA cuenta de vivienda sin activar.
_HASH_CENTINELA_SIN_ACTIVAR = hash_password(secrets.token_hex(32))


async def _crear_schema_y_tenant(engine: AsyncEngine, nombre: str, clabe_destino: str | None) -> Tenant:
    schema_name = f"tenant_{uuid.uuid4().hex[:8]}"
    async with engine.begin() as conn:
        await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
        await conn.execute(text(f'SET search_path TO "{schema_name}"'))
        await conn.run_sync(TenantBase.metadata.create_all)
        await conn.execute(text("SET search_path TO public"))
        await conn.run_sync(ControlBase.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        tenant = Tenant(nombre=nombre, clabe_destino=clabe_destino, precio_por_vivienda=25.00, schema_name=schema_name)
        session.add(tenant)
        await session.commit()
        await session.refresh(tenant)
    return tenant


async def _insertar_cuenta(
    engine: AsyncEngine, schema_name: str, tenant_id: uuid.UUID, *, email: str, password_hash: str, rol: Rol,
    property_id: uuid.UUID | None = None, activada: bool = True, debe_cambiar_password: bool = False,
    nombre: str | None = None, telefono: str | None = None,
) -> uuid.UUID:
    # El usuario vive DENTRO del schema del tenant, así que hay que fijar el search_path otra vez antes de insertarlo.
    async with engine.begin() as conn:
        await conn.execute(text(f'SET search_path TO "{schema_name}"'))
        user_id = uuid.uuid4()
        await conn.execute(
            UserAccount.__table__.insert().values(
                id=user_id, resident_id=None, email=email, password_hash=password_hash, rol=rol,
                property_id=property_id, activada=activada, debe_cambiar_password=debe_cambiar_password,
                nombre=nombre, telefono=telefono,
            )
        )
        await conn.execute(text("SET search_path TO public"))
        await conn.execute(UserLookup.__table__.insert().values(email=email, tenant_id=tenant_id, user_id=user_id))
    return user_id


async def provision_tenant(nombre: str, clabe_destino: str, admin_email: str, admin_password: str) -> Tenant:
    engine = create_async_engine(settings.database_url)
    tenant = await _crear_schema_y_tenant(engine, nombre, clabe_destino)
    await _insertar_cuenta(
        engine, tenant.schema_name, tenant.id, email=admin_email, password_hash=hash_password(admin_password),
        rol=Rol.admin,
    )
    await engine.dispose()
    print(f"Tenant creado: id={tenant.id}, schema='{tenant.schema_name}'")
    print(f"Admin creado: {admin_email} — ya puedes hacer login con este email y la contraseña que diste.")
    return tenant


async def provision_tenant_con_casas(
    nombre_condominio: str, cantidad_casas: int, dominio: str, nombre_admin: str, telefono_admin: str,
) -> tuple[Tenant, list[str]]:
    """
    Landing de bienvenida (/signup): crea el condominio SIN CLABE (se configura después, desde /clabe — ver
    Tenant.clabe_destino), `cantidad_casas` viviendas ("Casa 1".."Casa N") y, por cada una, una cuenta de
    residente sin activar en casa<n>@dominio (el residente la reclama desde la app: POST /residents/activar).

    El admin (administracion@dominio) SÍ queda utilizable de inmediato — su contraseña inicial es el propio
    nombre del condominio (decisión explícita del producto: fácil de recordar para arrancar), con
    debe_cambiar_password=True para que la cambie en cuanto entra. `dominio` ya viene resuelto y único
    (ver tenant_domain.generar_dominio_unico) — provisioning no vuelve a comprobarlo.

    Regresa el tenant y la lista de emails de vivienda generados (casa1@dominio, casa2@dominio, ...) para que
    el panel se los muestre al admin recién registrado: es la única forma que tiene de dárselos a sus residentes.
    """
    engine = create_async_engine(settings.database_url)
    tenant = await _crear_schema_y_tenant(engine, nombre_condominio, None)

    await _insertar_cuenta(
        engine, tenant.schema_name, tenant.id, email=f"administracion@{dominio}",
        password_hash=hash_password(nombre_condominio), rol=Rol.admin, debe_cambiar_password=True,
        nombre=nombre_admin, telefono=telefono_admin,
    )

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    emails_viviendas: list[str] = []
    cuentas_para_lookup: list[tuple[uuid.UUID, str]] = []
    async with session_factory() as session:
        # is_local=true (transaction-scoped, no un SET persistente): se resetea solo al comitear, así esta
        # conexión no vuelve al pool con el search_path del tenant pegado — bug real: sin esto, la sesión de
        # abajo (user_lookup, en `public`) podía reusar esta misma conexión y tronar con "relation
        # user_lookup does not exist" (mismo motivo documentado en tenant_session(), core/database.py).
        await session.execute(
            text("SELECT set_config('search_path', :schema, true)"), {"schema": f"{tenant.schema_name},public"}
        )
        for n in range(1, cantidad_casas + 1):
            identificador = f"Casa {n}"
            referencia = await generate_payment_reference(identificador, session)
            casa = property.Property(identificador=identificador, referencia_pago=referencia)
            session.add(casa)
            await session.flush()  # necesitamos casa.id antes de crear su cuenta

            email_casa = f"casa{n}@{dominio}"
            emails_viviendas.append(email_casa)
            # id se genera aquí mismo (no se deja al default de la columna): ese default solo lo aplica
            # SQLAlchemy AL HACER FLUSH, no al construir el objeto en Python — leerlo antes (como se hacía)
            # daba cuenta.id=None, y el INSERT a user_lookup de abajo tronaba con NotNullViolationError.
            cuenta_id = uuid.uuid4()
            session.add(
                UserAccount(
                    id=cuenta_id, email=email_casa, password_hash=_HASH_CENTINELA_SIN_ACTIVAR, rol=Rol.residente,
                    property_id=casa.id, activada=False,
                )
            )
            cuentas_para_lookup.append((cuenta_id, email_casa))
        await session.commit()

    # user_lookup vive en el schema de control (public) — sesión aparte para no reabrir el search_path del
    # tenant sobre la misma conexión ya comiteada (mismo patrón que _insertar_cuenta).
    async with session_factory() as session:
        for user_id, email in cuentas_para_lookup:
            session.add(UserLookup(email=email, tenant_id=tenant.id, user_id=user_id))
        await session.commit()

    await engine.dispose()
    print(f"Tenant creado: id={tenant.id}, schema='{tenant.schema_name}', {cantidad_casas} vivienda(s).")
    print(f"Admin: administracion@{dominio} — contraseña inicial: el nombre del condominio (debe cambiarla al entrar).")
    return tenant, emails_viviendas


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print('Uso: python -m app.core.provisioning "<nombre>" "<clabe>" "<admin_email>" "<admin_password>"')
        sys.exit(1)
    asyncio.run(provision_tenant(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]))
