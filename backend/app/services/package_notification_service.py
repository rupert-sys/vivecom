"""
F2-04: notificaciones de paquetería (HU-S05) — al llegar y al recogerse,
cada una una sola vez. Mismo patrón de "barrido" que reminder_service.py
(F1-13) y announcement_service.py (F1-32): separado de la creación/
actualización del Package para no entrelazar WhatsApp/SMS con esa lógica.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.package import Package
from app.models.resident import Resident, ResidentProperty
from app.services.notification_providers.base import NotificationProvider


async def _telefonos_de_vivienda(db: AsyncSession, property_id: uuid.UUID) -> list[str]:
    result = await db.execute(
        select(Resident.telefono)
        .join(ResidentProperty, ResidentProperty.resident_id == Resident.id)
        .where(ResidentProperty.property_id == property_id)
    )
    return [telefono for telefono in result.scalars().all() if telefono]


async def send_package_notifications(db: AsyncSession, provider: NotificationProvider) -> int:
    """
    Revisión: los flags notificacion_*_enviada se marcaban sin fijarse si el
    envío tuvo éxito — igual que el bug ya corregido en reminder_service y
    announcement_service. Ahora solo se marcan si todos los envíos
    intentados a esa vivienda tuvieron éxito (o no había a quién avisar);
    si alguno falla, se reintenta en la siguiente corrida.
    """
    llegadas = (
        await db.execute(select(Package).where(Package.notificacion_llegada_enviada.is_(False)))
    ).scalars().all()
    recogidas = (
        await db.execute(
            select(Package).where(
                Package.fecha_recogido.is_not(None), Package.notificacion_recogido_enviada.is_(False)
            )
        )
    ).scalars().all()

    notificados = 0
    for paquete in llegadas:
        telefonos = await _telefonos_de_vivienda(db, paquete.property_id)
        resultados = [
            await provider.send(telefono, "Vivecom: te llegó un paquete. Pásalo a recoger en la caseta.")
            for telefono in telefonos
        ]
        if all(resultados):
            paquete.notificacion_llegada_enviada = True
            notificados += 1

    for paquete in recogidas:
        telefonos = await _telefonos_de_vivienda(db, paquete.property_id)
        resultados = [
            await provider.send(telefono, "Vivecom: tu paquete fue recogido. Registro cerrado.")
            for telefono in telefonos
        ]
        if all(resultados):
            paquete.notificacion_recogido_enviada = True
            notificados += 1

    if notificados:
        await db.commit()
    return notificados
