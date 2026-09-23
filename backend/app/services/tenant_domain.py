"""
Deriva el "dominio" de correo de un condominio a partir de su nombre — NO es un dominio real que Vivecom sea
dueño de registrar ni de recibir correo: el proyecto no tiene canal de correo (alcance: solo WhatsApp+SMS), así
que el email de cada cuenta es solo un identificador único de login, nunca una bandeja real. Ej. "Condominio
Arequipa" -> "arequipa.com.mx"; el administrador queda en administracion@arequipa.com.mx y cada vivienda en
casa<n>@arequipa.com.mx (ver provisioning.py).
"""

import re
import unicodedata

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_lookup import UserLookup

# Palabras genéricas que no distinguen a un condominio de otro — se quitan antes de generar el dominio para que
# "Condominio Las Jacarandas" y "Residencial Las Jacarandas" no colisionen en el mismo slug por accidente más de
# lo necesario, y para que el dominio se lea más parecido a un nombre real.
_PALABRAS_GENERICAS = {"condominio", "residencial", "fraccionamiento", "conjunto", "privada", "unidad", "de", "del", "la", "las", "el", "los"}


def _sin_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def slug_de_condominio(nombre: str) -> str:
    palabras = re.sub(r"[^a-z0-9\s]", "", _sin_acentos(nombre).lower()).split()
    significativas = [p for p in palabras if p not in _PALABRAS_GENERICAS] or palabras
    slug = "".join(significativas)
    return slug or "condominio"  # nombre compuesto solo de palabras genéricas o símbolos (caso límite)


async def dominio_disponible(control_db: AsyncSession, dominio: str) -> bool:
    ocupado = (
        await control_db.execute(select(UserLookup).where(UserLookup.email == f"administracion@{dominio}"))
    ).scalar_one_or_none()
    return ocupado is None


async def generar_dominio_unico(control_db: AsyncSession, nombre_condominio: str) -> str:
    """
    "administracion@<dominio>" es la primera cuenta que crea provision_tenant() para todo tenant nuevo (ver
    provisioning.py) — comprobar que esa dirección esté libre basta para saber que el dominio completo lo está
    (ningún tenant existente pudo haber tomado casa1@ese-dominio sin también haber tomado administracion@).
    """
    base = slug_de_condominio(nombre_condominio)
    dominio = f"{base}.com.mx"
    sufijo = 2
    while not await dominio_disponible(control_db, dominio):
        dominio = f"{base}{sufijo}.com.mx"
        sufijo += 1
    return dominio
