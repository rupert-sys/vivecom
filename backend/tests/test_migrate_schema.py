"""
migrate_schema.py agrega columnas a tenants ya existentes con SQL crudo de
Postgres (ADD COLUMN IF NOT EXISTS) — no se puede correr contra SQLite, pero sí
se puede verificar que cada entrada corresponda a una columna real del modelo,
que es el error más fácil de cometer (typo en el nombre, o quedarse fuera de
sincronía con el modelo).
"""

import pytest

import app.models  # noqa: F401
from app.core.database_base import TenantBase
from app.core.migrate_schema import COLUMNAS_NUEVAS, sentencias_para
from app.main import app  # noqa: F401 — registra todos los modelos en TenantBase.metadata


@pytest.mark.parametrize("tabla,columna,definicion", COLUMNAS_NUEVAS)
def test_cada_columna_migrada_existe_en_el_modelo(tabla, columna, definicion):
    assert tabla in TenantBase.metadata.tables, f"la tabla {tabla} no existe en TenantBase.metadata"
    assert columna in TenantBase.metadata.tables[tabla].columns, f"{tabla}.{columna} no existe en el modelo"


def test_las_columnas_not_null_traen_default_para_no_romper_filas_existentes():
    for tabla, columna, definicion in COLUMNAS_NUEVAS:
        if "NOT NULL" in definicion:
            assert "DEFAULT" in definicion, f"{tabla}.{columna} es NOT NULL sin DEFAULT: falla con filas existentes"


def test_rechaza_un_nombre_de_schema_que_no_sea_de_tenant():
    with pytest.raises(ValueError):
        sentencias_para('tenant_x"; DROP SCHEMA public; --')
    with pytest.raises(ValueError):
        sentencias_para("public")


def test_genera_una_sentencia_por_columna_mas_los_indices():
    sentencias = sentencias_para("tenant_1ee8c5bd")
    assert all('"tenant_1ee8c5bd".' in s for s in sentencias)
    assert len(sentencias) == len(COLUMNAS_NUEVAS) + 2
