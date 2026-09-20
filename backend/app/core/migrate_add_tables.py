"""
Agrega cualquier tabla nueva definida en TenantBase.metadata a un schema de
tenant que ya existe, y cualquier tabla nueva de ControlBase (schema
público, ej. clabe_change_log), sin tocar las tablas/datos que ya existen
(create_all es idempotente: solo crea lo que falta).

Uso:
    python -m app.core.migrate_add_tables tenant_1ee8c5bd
"""

import asyncio
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.core.database_base import ControlBase, TenantBase
from app.models import (  # noqa: F401
    access_log, amenity, announcement, budget, expense, fee, fee_charge, incident, lost_found_item, package,
    payment, payment_agreement, payment_proof, poll, property, reglamento, reservation, resident, stored_file, user, vehicle,
    visitor_qr,
)
from app.models.clabe_change_log import ClabeChangeLog  # noqa: F401
from app.models.tenant import Tenant  # noqa: F401
from app.models.vivecom_staff import VivecomStaff  # noqa: F401


async def add_missing_tables(schema_name: str) -> None:
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.execute(text(f'SET search_path TO "{schema_name}"'))
        await conn.run_sync(TenantBase.metadata.create_all)
        await conn.execute(text("SET search_path TO public"))
        await conn.run_sync(ControlBase.metadata.create_all)
    await engine.dispose()
    print(f"Tablas actualizadas en el schema '{schema_name}' y en el schema de control (public).")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python -m app.core.migrate_add_tables <schema_name>")
        print('Tu schema_name lo viste al aprovisionar, algo como "tenant_1ee8c5bd".')
        sys.exit(1)
    asyncio.run(add_missing_tables(sys.argv[1]))
