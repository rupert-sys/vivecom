"""Un despliegue nuevo (base de datos vacía) debe poder registrar su primer condominio."""

import pytest
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.init_db import init_control_schema


@pytest.mark.asyncio
async def test_crea_las_tablas_de_control_en_una_base_vacia_y_es_idempotente():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        await init_control_schema(engine)
        await init_control_schema(engine)  # corre en cada arranque del contenedor: no debe fallar la segunda vez

        async with engine.connect() as conn:
            tablas = set(await conn.run_sync(lambda c: inspect(c).get_table_names()))
        assert {"tenant", "user_lookup", "clabe_change_log", "vivecom_staff"} <= tablas
    finally:
        await engine.dispose()
