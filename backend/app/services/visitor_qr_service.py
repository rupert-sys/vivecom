"""
F2-02/F2-03: QR de acceso temporal de un solo uso (HU-S02, HU-S03).
"""

import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.visitor_qr import VisitorQR


async def generate_visitor_qr(db: AsyncSession, property_id: uuid.UUID) -> VisitorQR:
    qr = VisitorQR(
        property_id=property_id,
        codigo=secrets.token_urlsafe(16),
        fecha_generado=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(qr)
    await db.commit()
    return qr


async def validate_and_consume_qr(db: AsyncSession, codigo: str) -> tuple[bool, str | None, uuid.UUID | None]:
    """
    HU-S03: si el QR no existe o ya se usó, se rechaza indicándolo. Si es
    válido, se consume de inmediato (usado=True) — un mismo código nunca
    autoriza dos entradas.
    """
    qr = (await db.execute(select(VisitorQR).where(VisitorQR.codigo == codigo))).scalar_one_or_none()
    if qr is None:
        return False, "no_existe", None
    if qr.usado:
        return False, "ya_usado", None

    qr.usado = True
    qr.fecha_usado = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    return True, None, qr.property_id
