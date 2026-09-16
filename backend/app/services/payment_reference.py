"""
Genera la referencia numérica SPEI (7 dígitos) de una vivienda: se usan los
últimos dígitos del identificador (ej. "Casa 14" -> termina en "...0014")
para que el residente pueda confirmarla a simple vista contra su propio
número de casa/depto, tal como se decidió en el alcance (F1-06).
"""

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.property import Property

REFERENCIA_LONGITUD = 7


async def generate_payment_reference(identificador: str, db: AsyncSession) -> str:
    digitos = re.sub(r"\D", "", identificador)
    base = digitos[-4:] if digitos else "0"
    candidato = base.zfill(REFERENCIA_LONGITUD)

    # Si esa referencia ya está tomada (dos viviendas con el mismo número,
    # ej. "Casa 14" en dos secciones distintas, o un identificador sin
    # dígitos), se le agrega un sufijo incremental hasta encontrar una libre.
    sufijo = 0
    while True:
        existe = (
            await db.execute(select(Property).where(Property.referencia_pago == candidato))
        ).scalar_one_or_none()
        if existe is None:
            return candidato
        sufijo += 1
        candidato = str(int(base) + sufijo).zfill(REFERENCIA_LONGITUD)[-REFERENCIA_LONGITUD:]
