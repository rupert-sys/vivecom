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

# statement_cache_size=0: asyncpg cachea planes de consulta preparados POR
# CONEXIÓN, sin que la caché se entere de que el search_path (y por lo
# tanto A QUÉ TABLA apunta "user_account", etc.) cambia en cada request vía
# SET LOCAL search_path (ver tenant_session() abajo). Cuando una conexión
# del pool reutiliza un plan cacheado después de que OTRA sesión hizo DDL
# sobre una tabla con el mismo nombre en otro schema (ej. /signup creando
# un tenant nuevo, F1-29), Postgres invalida el plan y asyncpg lo reporta
# como InvalidCachedStatementError — un 500 real, encontrado al construir
# la prueba de punta a punta del flujo de cobro. Es el patrón de mitigación
# oficial de asyncpg para escenarios con schemas dinámicos o pooling
# externo (PgBouncer): sin esto, además del error visible, existe un
# riesgo teórico más serio de que un plan cacheado bajo el search_path de
# UN tenant se reutilice para la consulta de OTRO — deshabilitar el caché
# de sentencias preparadas por conexión elimina esa clase de bug de raíz,
# a costa de perder el pequeño ahorro de no re-preparar cada consulta.
engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    # F1-37 (QA de carga): con el default de SQLAlchemy (pool_size=5,
    # max_overflow=10 quedaba en 10+10 con el pool_size explícito de abajo)
    # una ráfaga real de ~100 depósitos concurrentes (fin de mes, muchos
    # residentes pagando casi a la vez) agotaba el pool y Postgres real
    # respondía con 500 (QueuePool limit... connection timed out) en vez de
    # simplemente encolar. El servidor de Postgres permite hasta 100
    # conexiones — 20 usadas normalmente por esta app deja poco margen, así
    # que se sube a 20+20 (40 total), muy por debajo del límite del server y
    # con margen para otras conexiones (herramientas, otra instancia, etc.).
    # Esto empuja el techo más arriba, no lo elimina — una ráfaga aún más
    # grande necesitaría planeación de capacidad real (PgBouncer, más de un
    # proceso de la app, etc.), fuera del alcance de esta prueba de carga.
    pool_size=20,
    max_overflow=20,
    # Dos cachés distintas hay que apagar: prepared_statement_cache_size es
    # la capa que administra el dialecto asyncpg de SQLAlchemy (encima de
    # asyncpg mismo); statement_cache_size es la del propio driver asyncpg.
    # Con solo la primera apagada, el problema seguía reproduciéndose — se
    # verificó a mano matando y recreando un tenant vía /signup seguido de
    # /auth/login antes de encontrar que hacían falta las dos.
    connect_args={"prepared_statement_cache_size": 0, "statement_cache_size": 0},
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@asynccontextmanager
async def tenant_session(
    schema_name: str, session_factory: async_sessionmaker[AsyncSession] | None = None
) -> AsyncIterator[AsyncSession]:
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

    `session_factory`: por default usa el `SessionLocal` de este módulo (el engine de por vida del
    proceso, pensado para el event loop único y persistente de uvicorn). Los workers de Celery
    (app/workers/tasks.py) pasan aquí su propio session_factory, creado y desechado DENTRO del mismo
    asyncio.run() de cada tarea — cada tarea corre en un event loop nuevo, y una conexión asyncpg
    creada en un loop no se puede reusar ni cerrar limpiamente desde otro: reusar el engine global ahí
    producía "RuntimeError: Event loop is closed" / "attached to a different loop" de forma intermitente.
    """
    async with (session_factory or SessionLocal)() as session:
        await session.execute(
            text("SELECT set_config('search_path', :schema, true)"),
            {"schema": f"{schema_name},public"},
        )
        yield session


async def control_session() -> AsyncIterator[AsyncSession]:
    """Sesión sobre el schema de control (tabla `tenant`, `clabe_change_log`)."""
    async with SessionLocal() as session:
        yield session
