"""
migrate_schema.py agrega columnas y valores de ENUM a tenants ya existentes con
SQL crudo de Postgres (ADD COLUMN IF NOT EXISTS / ADD VALUE IF NOT EXISTS) — no
se puede correr contra SQLite, pero sí se puede verificar que cada entrada
corresponda a una columna o a un valor de Enum real del modelo, que es el error
más fácil de cometer (typo en el nombre, o quedarse fuera de sincronía con el
modelo).
"""

import pytest

import app.models  # noqa: F401
from app.core.database_base import TenantBase
from app.core.migrate_schema import ALTERACIONES, COLUMNAS_NUEVAS, INDICES_NUEVOS, VALORES_ENUM_NUEVOS, sentencias_para
from app.main import app  # noqa: F401 — registra todos los modelos en TenantBase.metadata


@pytest.mark.parametrize("tabla,columna,definicion", COLUMNAS_NUEVAS)
def test_cada_columna_migrada_existe_en_el_modelo(tabla, columna, definicion):
    assert tabla in TenantBase.metadata.tables, f"la tabla {tabla} no existe en TenantBase.metadata"
    assert columna in TenantBase.metadata.tables[tabla].columns, f"{tabla}.{columna} no existe en el modelo"


@pytest.mark.parametrize("tipo,valor", VALORES_ENUM_NUEVOS)
def test_cada_valor_de_enum_migrado_existe_en_algun_modelo(tipo, valor):
    """
    Busca una columna en TenantBase cuyo tipo nativo de Postgres se llame
    `tipo` y cuyo Enum de Python contenga `valor` — así un typo aquí, o quedarse
    fuera de sincronía tras quitar un valor del modelo, se detecta sin Postgres.
    """
    encontrada = False
    for tabla in TenantBase.metadata.tables.values():
        for columna in tabla.columns:
            nombre_tipo = getattr(columna.type, "name", None)
            valores = getattr(columna.type, "enums", None)
            if nombre_tipo == tipo and valores is not None:
                encontrada = True
                assert valor in valores, f"{tipo}.{valor} no está en el Enum de {tabla.name}.{columna.name}: {valores}"
    assert encontrada, f"ningún modelo usa un ENUM de Postgres llamado {tipo!r}"


def test_las_columnas_not_null_traen_default_para_no_romper_filas_existentes():
    for tabla, columna, definicion in COLUMNAS_NUEVAS:
        if "NOT NULL" in definicion:
            assert "DEFAULT" in definicion, f"{tabla}.{columna} es NOT NULL sin DEFAULT: falla con filas existentes"


def test_rechaza_un_nombre_de_schema_que_no_sea_de_tenant():
    with pytest.raises(ValueError):
        sentencias_para('tenant_x"; DROP SCHEMA public; --')
    with pytest.raises(ValueError):
        sentencias_para("public")


def test_genera_una_sentencia_por_columna_alteracion_indice_y_valor_de_enum():
    sentencias = sentencias_para("tenant_1ee8c5bd")
    assert all('"tenant_1ee8c5bd".' in s for s in sentencias)
    assert len(sentencias) == len(VALORES_ENUM_NUEVOS) + len(COLUMNAS_NUEVAS) + len(ALTERACIONES) + len(
        INDICES_NUEVOS
    )
