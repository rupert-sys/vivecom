"""
Estrategia multi-tenant: un solo servidor PostgreSQL, un schema por condominio (tenant).
La tabla `tenant` vive en el schema de control (público) y mapea tenant_id -> schema_name.
Cada request autenticado fija el `search_path` de Postgres al schema del tenant antes
de ejecutar cualquier query, aislando los datos sin necesidad de bases de datos separadas.
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

engine = create_async_engine(settings.database_url, pool_pre_ping=True, pool_size=10)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@asynccontextmanager
async def tenant_session(schema_name: str) -> AsyncIterator[AsyncSession]:
    """
    Abre una sesión y fija el search_path al schema del tenant para toda la transacción.
    Uso: `async with tenant_session(current_tenant.schema_name) as db: ...`

    LIMITACIÓN IMPORTANTE: el search_path se fija con is_local=true, es decir,
    solo aplica DENTRO de la transacción actual. Si dentro del mismo `with`
    haces un commit() y luego otra consulta (ej. refresh()), esa segunda
    consulta ya NO tiene el search_path del tenant — vuelve al default y
    revienta con "relation does not exist". Por diseño: usar is_local=true
    (en vez de un SET persistente) es lo que evita que el search_path de un
    tenant se filtre a la siguiente request que reutilice la misma conexión
    del pool — eso sí sería un bug de seguridad multi-tenant real. La regla
    práctica: haz todo tu trabajo antes del commit() final, y no vuelvas a
    consultar la sesión después de comitear.
    """
    async with SessionLocal() as session:
        await session.execute(
            text("SELECT set_config('search_path', :schema, true)"),
            {"schema": f"{schema_name},public"},
        )
        yield session


async def control_session() -> AsyncIterator[AsyncSession]:
    """Sesión sobre el schema de control (tabla `tenant`, `clabe_change_log`)."""
    async with SessionLocal() as session:
        yield session
