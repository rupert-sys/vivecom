"""
tenant_domain.py deriva el "dominio" de correo de un condominio a partir de su nombre — usado por /signup para
el admin (administracion@dominio) y cada vivienda (casa<n>@dominio). slug_de_condominio() es pura (sin DB);
generar_dominio_unico()/dominio_disponible() solo tocan UserLookup (schema de control) — a diferencia de
provision_tenant_con_casas() (CREATE SCHEMA, sintaxis de Postgres), sí corren contra SQLite.
"""

import uuid
from contextlib import asynccontextmanager

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database_base import ControlBase
from app.models.user_lookup import UserLookup
from app.services.tenant_domain import dominio_disponible, generar_dominio_unico, slug_de_condominio


def test_quita_condominio_y_usa_la_palabra_significativa():
    assert slug_de_condominio("Condominio Arequipa") == "arequipa"


def test_quita_acentos():
    assert slug_de_condominio("Residencial Las Jacarandás") == "jacarandas"  # "residencial"/"las": genéricas


def test_varias_palabras_significativas_se_concatenan():
    assert slug_de_condominio("Fraccionamiento Vista Hermosa") == "vistahermosa"


def test_quita_simbolos_y_mayusculas():
    assert slug_de_condominio("Privada San José #12") == "sanjose12"


def test_nombre_compuesto_solo_de_palabras_genericas_no_se_queda_vacio():
    assert slug_de_condominio("Condominio de la Privada") == "condominiodelaprivada"


def test_nombre_vacio_de_simbolos_cae_al_valor_por_defecto():
    assert slug_de_condominio("###") == "condominio"


@asynccontextmanager
async def _control_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    async with engine.begin() as conn:
        await conn.run_sync(ControlBase.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_dominio_disponible_cuando_nadie_lo_uso():
    async with _control_db() as db:
        assert await dominio_disponible(db, "arequipa.com.mx") is True


@pytest.mark.asyncio
async def test_dominio_no_disponible_si_ya_hay_un_administracion_ahi():
    async with _control_db() as db:
        db.add(UserLookup(email="administracion@arequipa.com.mx", tenant_id=uuid.uuid4(), user_id=uuid.uuid4()))
        await db.commit()

        assert await dominio_disponible(db, "arequipa.com.mx") is False


@pytest.mark.asyncio
async def test_generar_dominio_unico_da_el_slug_simple_si_esta_libre():
    async with _control_db() as db:
        assert await generar_dominio_unico(db, "Condominio Arequipa") == "arequipa.com.mx"


@pytest.mark.asyncio
async def test_generar_dominio_unico_agrega_un_sufijo_si_ya_existe():
    async with _control_db() as db:
        db.add(UserLookup(email="administracion@arequipa.com.mx", tenant_id=uuid.uuid4(), user_id=uuid.uuid4()))
        await db.commit()

        assert await generar_dominio_unico(db, "Condominio Arequipa") == "arequipa2.com.mx"


@pytest.mark.asyncio
async def test_generar_dominio_unico_salta_varios_sufijos_ocupados():
    async with _control_db() as db:
        for dominio in ("arequipa.com.mx", "arequipa2.com.mx", "arequipa3.com.mx"):
            db.add(UserLookup(email=f"administracion@{dominio}", tenant_id=uuid.uuid4(), user_id=uuid.uuid4()))
        await db.commit()

        assert await generar_dominio_unico(db, "Condominio Arequipa") == "arequipa4.com.mx"
