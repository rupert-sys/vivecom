"""
Prepara una base de datos NUEVA para que el backend arranque: crea las tablas de control (schema público:
tenant, user_lookup, clabe_change_log, vivecom_staff) si faltan.

Hasta ahora esas tablas nacían dentro del primer aprovisionamiento (provision_tenant), pero /signup consulta
user_lookup ANTES de aprovisionar: en una base vacía —un despliegue nuevo, la PC dedicada, un staging— el primer
registro fallaba con «relation "user_lookup" does not exist». Es idempotente (create_all solo crea lo que falta),
así que corre en cada arranque del contenedor, seguido de migrate_schema --all para los tenants existentes
(ver Dockerfile).

Uso:  python -m app.core.init_db
"""

import asyncio

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core.config import settings
from app.core.database_base import ControlBase
from app.models import clabe_change_log, tenant, user_lookup, vivecom_staff  # noqa: F401  (registran sus tablas)


async def init_control_schema(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(ControlBase.metadata.create_all)


async def main() -> None:
    engine = create_async_engine(settings.database_url)
    try:
        await init_control_schema(engine)
    finally:
        await engine.dispose()
    print("Tablas de control listas.")


if __name__ == "__main__":
    asyncio.run(main())
