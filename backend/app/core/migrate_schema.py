"""
Pone al día el schema de tenants que YA existen cuando el código agrega tablas
o columnas nuevas.

migrate_add_tables.py solo crea tablas nuevas (create_all no altera las que ya
existen), y hasta ahora no había ninguna forma de agregar una columna a un
tenant existente — F2-07 agregó columnas a access_log e incident y quedaron
sin aplicar en los tenants ya creados (un POST /access-log contra uno de ellos
reventaría con "column does not exist"). Este módulo cierra ese hueco:

- Las tablas nuevas se crean con create_all (idempotente).
- Las columnas nuevas se agregan con ALTER TABLE ... ADD COLUMN IF NOT EXISTS
  (Postgres), listadas explícitamente en COLUMNAS_NUEVAS. Un tenant nuevo no lo
  necesita: provision_tenant() ya crea todo con create_all.

Uso:
    python -m app.core.migrate_schema --all            # todos los tenants
    python -m app.core.migrate_schema tenant_1ee8c5bd  # uno solo

Al agregar una columna a un modelo de tenant que ya existía en producción,
agrégala también aquí — tests/test_migrate_schema.py verifica que cada entrada
corresponda a una columna real del modelo.
"""

import argparse
import asyncio
import re

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.core.migrate_add_tables import add_missing_tables

# (tabla, columna, definición SQL sin el nombre de la columna; {schema} se
# reemplaza por el schema del tenant, para las llaves foráneas)
COLUMNAS_NUEVAS: list[tuple[str, str, str]] = [
    # F2-07/F2-11: idempotencia de la sincronización de la app caseta.
    ("access_log", "client_id", "UUID"),
    ("incident", "client_id", "UUID"),
    ("incident", "foto_url", "VARCHAR"),
    # Reglamento (Condominio Arequipa, 18-ene-2026): datos de la bitácora de acceso.
    ("access_log", "nombre_visitante", "VARCHAR"),
    ("access_log", "acompanantes", "INTEGER NOT NULL DEFAULT 0"),
    ("access_log", "identificacion", "VARCHAR"),
    ("access_log", "autorizado_por", "VARCHAR"),
    # Reglamento: bitácora de incidencias (tipo, casa y persona involucradas).
    ("incident", "tipo", "VARCHAR NOT NULL DEFAULT 'seguridad'"),
    ("incident", "property_id", "UUID REFERENCES {schema}.property(id)"),
    ("incident", "persona_involucrada", "VARCHAR"),
    # Reglamento: reglas por amenidad y cuota de uso.
    ("amenity", "dias_anticipacion_minimos", "INTEGER NOT NULL DEFAULT 0"),
    ("amenity", "hora_inicio_permitida", "TIME"),
    ("amenity", "hora_fin_maxima", "TIME"),
    ("amenity", "dias_semana_permitidos", "VARCHAR"),
    ("amenity", "capacidad", "INTEGER NOT NULL DEFAULT 1"),
    ("amenity", "cuota", "NUMERIC(10, 2) NOT NULL DEFAULT 0"),
    ("amenity", "max_duracion_horas", "INTEGER"),
    ("amenity", "notas_reglamento", "TEXT"),
    ("reservation", "cuota_pagada", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("reservation", "cuota", "NUMERIC(10, 2) NOT NULL DEFAULT 0"),
    # Reglamento: pagos capturados a mano (efectivo).
    ("payment", "registrado_por", "UUID"),
    # Reglamento Art. 8: tipo de gasto, aprobación de asamblea y cotizaciones.
    ("expense", "tipo", "VARCHAR NOT NULL DEFAULT 'operativo'"),
    ("expense", "aprobado_en_asamblea", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("expense", "acta_referencia", "VARCHAR"),
    ("expense", "cotizaciones", "JSON"),
    ("expense", "tipo_comprobante", "VARCHAR"),
    # App caseta: paquetes registrados sin conexión (idempotencia) y códigos de
    # proveedor que emite el guardia.
    ("package", "client_id", "UUID"),
    ("visitor_qr", "tipo", "VARCHAR NOT NULL DEFAULT 'visitante'"),
    ("visitor_qr", "descripcion", "VARCHAR"),
    # Dudas en avisos (la tabla announcement_question la crea create_all).
    ("announcement", "permite_dudas", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("announcement", "dudas_hasta", "DATE"),
    ("reglamento_config", "dudas_en_avisos_por_defecto", "BOOLEAN NOT NULL DEFAULT FALSE"),
]

# Cambios a columnas que ya existían (idempotentes en Postgres).
ALTERACIONES: list[str] = [
    # Un código de proveedor puede no tener vivienda asociada.
    "ALTER TABLE {schema}.visitor_qr ALTER COLUMN property_id DROP NOT NULL",
]

INDICES_NUEVOS: list[str] = [
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_access_log_client_id ON {schema}.access_log (client_id)",
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_incident_client_id ON {schema}.incident (client_id)",
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_package_client_id ON {schema}.package (client_id)",
]

_PATRON_SCHEMA = re.compile(r"^tenant_[0-9a-f]{8}$")


def sentencias_para(schema_name: str) -> list[str]:
    # schema_name se interpola en SQL crudo (ALTER TABLE no admite parámetros
    # para identificadores): siempre lo genera provision_tenant() como
    # tenant_<8 hex>, pero se valida aquí de todos modos para que este módulo
    # nunca dependa de que quien lo llama lo haya sanitizado.
    if not _PATRON_SCHEMA.match(schema_name):
        raise ValueError(f"Nombre de schema inválido: {schema_name!r}")
    q = f'"{schema_name}"'
    sentencias = [
        f"ALTER TABLE {q}.{tabla} ADD COLUMN IF NOT EXISTS {columna} {definicion.format(schema=q)}"
        for tabla, columna, definicion in COLUMNAS_NUEVAS
    ]
    sentencias += [alteracion.format(schema=q) for alteracion in ALTERACIONES]
    sentencias += [indice.format(schema=q) for indice in INDICES_NUEVOS]
    return sentencias


async def migrar_schema(schema_name: str) -> None:
    sentencias = sentencias_para(schema_name)  # valida el nombre ANTES de tocar nada
    await add_missing_tables(schema_name)  # tablas nuevas (create_all)
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        for sentencia in sentencias:
            await conn.execute(text(sentencia))
    await engine.dispose()
    print(f"Columnas al día en '{schema_name}'.")


async def migrar_todos() -> None:
    engine = create_async_engine(settings.database_url)
    async with engine.connect() as conn:
        schemas = (await conn.execute(text("SELECT schema_name FROM tenant ORDER BY schema_name"))).scalars().all()
    await engine.dispose()
    for schema in schemas:
        await migrar_schema(schema)
    print(f"{len(schemas)} tenant(s) actualizados.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("schema", nargs="?", help="schema de un tenant, ej. tenant_1ee8c5bd")
    parser.add_argument("--all", action="store_true", help="todos los tenants registrados")
    args = parser.parse_args()
    if args.all:
        asyncio.run(migrar_todos())
    elif args.schema:
        asyncio.run(migrar_schema(args.schema))
    else:
        parser.error("indica un schema o --all")
