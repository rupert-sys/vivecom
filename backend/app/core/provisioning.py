"""
Aprovisiona un nuevo condominio: crea su schema de PostgreSQL, todas las
tablas del tenant dentro de él (property, resident, user_account, etc.), el
registro correspondiente en la tabla `tenant` del schema de control, y el
primer usuario administrador (sin esto no hay forma de iniciar sesión).

Uso:
    python -m app.core.provisioning "Residencial Las Fuentes" "012180001547896321" "admin@vivecom.mx" "clave-temporal-123"
"""

import asyncio
import sys
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

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
    payment, poll, property, reservation, resident, user, vehicle, visitor_qr,
)


async def provision_tenant(nombre: str, clabe_destino: str, admin_email: str, admin_password: str) -> Tenant:
    engine = create_async_engine(settings.database_url)
    schema_name = f"tenant_{uuid.uuid4().hex[:8]}"

    async with engine.begin() as conn:
        await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
        await conn.execute(text(f'SET search_path TO "{schema_name}"'))
        await conn.run_sync(TenantBase.metadata.create_all)
        await conn.execute(text("SET search_path TO public"))
        await conn.run_sync(ControlBase.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        tenant = Tenant(
            nombre=nombre, clabe_destino=clabe_destino,
            precio_por_vivienda=25.00, schema_name=schema_name,
        )
        session.add(tenant)
        await session.commit()
        await session.refresh(tenant)

    # El usuario admin vive DENTRO del schema del tenant, así que hay que
    # fijar el search_path otra vez antes de insertarlo.
    async with engine.begin() as conn:
        await conn.execute(text(f'SET search_path TO "{schema_name}"'))
        admin_id = uuid.uuid4()
        await conn.execute(
            UserAccount.__table__.insert().values(
                id=admin_id, resident_id=None, email=admin_email,
                password_hash=hash_password(admin_password), rol=Rol.admin, property_id=None,
            )
        )
        await conn.execute(text("SET search_path TO public"))
        await conn.execute(
            UserLookup.__table__.insert().values(email=admin_email, tenant_id=tenant.id, user_id=admin_id)
        )

    await engine.dispose()
    print(f"Tenant creado: id={tenant.id}, schema='{schema_name}'")
    print(f"Admin creado: {admin_email} — ya puedes hacer login con este email y la contraseña que diste.")
    return tenant


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print('Uso: python -m app.core.provisioning "<nombre>" "<clabe>" "<admin_email>" "<admin_password>"')
        sys.exit(1)
    asyncio.run(provision_tenant(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]))


