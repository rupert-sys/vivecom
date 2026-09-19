"""
F2-02/F2-03: QR de acceso temporal de un solo uso (HU-S02, HU-S03).
"""

import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.property import Property
from app.models.visitor_qr import VisitorQR


async def generate_visitor_qr(
    db: AsyncSession, property_id: uuid.UUID | None, tipo: str = "visitante", descripcion: str | None = None
) -> VisitorQR:
    qr = VisitorQR(
        property_id=property_id,
        codigo=secrets.token_urlsafe(16),
        fecha_generado=datetime.now(timezone.utc).replace(tzinfo=None),
        tipo=tipo,
        descripcion=descripcion,
    )
    db.add(qr)
    await db.commit()
    return qr


@dataclass
class ResultadoValidacionQR:
    valido: bool
    motivo: str | None = None
    property_id: uuid.UUID | None = None
    tipo: str | None = None
    descripcion: str | None = None
    vivienda: str | None = None  # identificador legible (ej. "Casa 4") para el guardia


async def validate_and_consume_qr(db: AsyncSession, codigo: str) -> ResultadoValidacionQR:
    """
    HU-S03: si el QR no existe o ya se usó, se rechaza indicándolo. Si es
    válido, se consume de inmediato (usado=True) — un mismo código nunca
    autoriza dos entradas.
    """
    qr = (await db.execute(select(VisitorQR).where(VisitorQR.codigo == codigo))).scalar_one_or_none()
    if qr is None:
        return ResultadoValidacionQR(valido=False, motivo="no_existe")
    if qr.usado:
        return ResultadoValidacionQR(valido=False, motivo="ya_usado")

    # La vivienda se consulta ANTES del commit: después, el search_path del tenant ya no aplica.
    propiedad = await db.get(Property, qr.property_id) if qr.property_id is not None else None
    qr.usado = True
    qr.fecha_usado = datetime.now(timezone.utc).replace(tzinfo=None)
    resultado = ResultadoValidacionQR(
        valido=True,
        property_id=qr.property_id,
        tipo=qr.tipo,
        descripcion=qr.descripcion,
        vivienda=propiedad.identificador if propiedad is not None else None,
    )
    await db.commit()
    return resultado
