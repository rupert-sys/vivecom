"""
F1-31 (confirmación de lectura) y F1-32 (notificación al publicarse) de
avisos y circulares (F1-30, HU-C01).
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.announcement import Announcement, ReadReceipt
from app.models.property import Property
from app.models.resident import Resident
from app.services.notification_providers.base import NotificationProvider


@dataclass
class ReadStatusEntry:
    property_id: uuid.UUID
    identificador: str
    leido: bool
    leido_at: datetime | None


async def mark_announcement_read(db: AsyncSession, announcement_id: uuid.UUID, property_id: uuid.UUID) -> ReadReceipt:
    """Idempotente: si la vivienda ya lo había marcado como leído, regresa el registro existente."""
    existente = (
        await db.execute(
            select(ReadReceipt).where(
                ReadReceipt.announcement_id == announcement_id, ReadReceipt.property_id == property_id
            )
        )
    ).scalar_one_or_none()
    if existente is not None:
        return existente

    receipt = ReadReceipt(
        announcement_id=announcement_id, property_id=property_id,
        leido_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(receipt)
    await db.commit()
    return receipt


async def get_read_status(db: AsyncSession, announcement_id: uuid.UUID) -> list[ReadStatusEntry]:
    """Todas las viviendas del condominio, marcando cuáles ya leyeron este aviso."""
    propiedades = (await db.execute(select(Property).order_by(Property.identificador))).scalars().all()
    receipts = (
        await db.execute(select(ReadReceipt).where(ReadReceipt.announcement_id == announcement_id))
    ).scalars().all()
    leido_por_propiedad = {receipt.property_id: receipt.leido_at for receipt in receipts}

    return [
        ReadStatusEntry(
            property_id=propiedad.id,
            identificador=propiedad.identificador,
            leido=propiedad.id in leido_por_propiedad,
            leido_at=leido_por_propiedad.get(propiedad.id),
        )
        for propiedad in propiedades
    ]


async def send_announcement_notifications(db: AsyncSession, provider: NotificationProvider, ahora: datetime) -> int:
    """
    Avisos ya publicados (fecha_publicacion <= ahora) que aún no se
    notificaron. Se manda a TODOS los residentes del condominio, no por
    vivienda — un aviso es comunitario, no financiero.

    Revisión: antes se marcaba notificacion_enviada=True sin fijarse si los
    envíos tuvieron éxito, así que una falla de Twilio dejaba el aviso como
    "notificado" para siempre sin haber llegado a nadie. Ahora solo se marca
    si TODOS los envíos intentados tuvieron éxito (o no había a quién
    avisar); si alguno falla, se reintenta el aviso completo en la próxima
    corrida. Compromiso deliberado, no una solución perfecta: un solo
    número inválido entre muchos residentes puede hacer que se reintente el
    envío a todos los demás también — la alternativa correcta (registrar
    éxito/fracaso por residente, no por aviso) es un cambio de modelo más
    grande que no se hizo aquí; esto sigue siendo estrictamente mejor que
    dar por hecho un envío que nunca ocurrió.
    """
    result = await db.execute(
        select(Announcement).where(Announcement.fecha_publicacion <= ahora, Announcement.notificacion_enviada.is_(False))
    )
    candidatos = result.scalars().all()
    if not candidatos:
        return 0

    telefonos = [t for t in (await db.execute(select(Resident.telefono))).scalars().all() if t]

    notificados = 0
    for aviso in candidatos:
        mensaje = f"Vivecom: nuevo aviso — {aviso.titulo}"
        resultados = [await provider.send(telefono, mensaje) for telefono in telefonos]
        if all(resultados):
            aviso.notificacion_enviada = True
            notificados += 1

    if notificados:
        await db.commit()
    return notificados
