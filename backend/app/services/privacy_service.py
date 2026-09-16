"""
F3-02: cumplimiento LFPDPPP (Ley Federal de Protección de Datos Personales
en Posesión de los Particulares) — aviso de privacidad, consentimiento, y
derechos ARCO de acceso y cancelación.

AVISO — el texto de PRIVACY_NOTICE_TEXT es una plantilla genérica, NO un
aviso de privacidad real: falta el nombre legal de la empresa, domicilio
fiscal, datos de contacto del responsable, y sobre todo revisión por un
abogado especializado en protección de datos antes de publicarlo. Mismo
espíritu que "cambia-esto-en-produccion" en config.py — el placeholder deja
claro qué falta, no pretende ser el documento final.

La cancelación (derecho ARCO) se implementa como ANONIMIZACIÓN, no borrado
físico: LFPDPPP mismo reconoce excepciones cuando existe una obligación
legal de conservar el dato (la Ley del Impuesto Sobre la Renta exige
conservar registros contables varios años) — Payment y FeeCharge cuelgan de
Property, no de Resident, así que anonimizar a la persona no borra ese
historial financiero, que es exactamente el balance correcto aquí.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.announcement import ReadReceipt
from app.models.incident import Incident
from app.models.lost_found_item import LostFoundItem
from app.models.poll import Vote
from app.models.property import Property
from app.models.reservation import Reservation
from app.models.resident import Resident, ResidentProperty

PRIVACY_NOTICE_TEXT = """
AVISO DE PRIVACIDAD (PLANTILLA — REQUIERE REVISIÓN LEGAL ANTES DE PUBLICARSE)

[Razón social del responsable], con domicilio en [domicilio fiscal], es
responsable del tratamiento de sus datos personales conforme a la Ley
Federal de Protección de Datos Personales en Posesión de los Particulares.

Sus datos personales (nombre, teléfono, correo electrónico) se utilizan
para: identificarlo como residente de su condominio, enviarle avisos y
notificaciones (WhatsApp/SMS), y procesar sus solicitudes de amenidades,
votaciones y reportes.

Usted puede ejercer sus derechos de Acceso, Rectificación, Cancelación y
Oposición (derechos ARCO) a través de los medios que su administración le
indique. La cancelación de sus datos puede no proceder de forma inmediata
sobre información que la ley exige conservar con fines contables o legales.

[Falta: datos de contacto del responsable/oficial de privacidad, mecanismo
de solicitud ARCO fuera de la app, aviso de transferencias a terceros si
las hay (ej. proveedor de WhatsApp/SMS), y firma/validación de un abogado
especializado antes de usarse en producción.]
""".strip()


async def _resident_data_export(db: AsyncSession, resident: Resident) -> dict[str, Any]:
    propiedades = (
        await db.execute(
            select(Property)
            .join(ResidentProperty, ResidentProperty.property_id == Property.id)
            .where(ResidentProperty.resident_id == resident.id)
        )
    ).scalars().all()
    property_ids = [p.id for p in propiedades]

    votos = (await db.execute(select(Vote).where(Vote.property_id.in_(property_ids)))).scalars().all() if property_ids else []
    lecturas = (
        await db.execute(select(ReadReceipt).where(ReadReceipt.property_id.in_(property_ids)))
    ).scalars().all() if property_ids else []
    reservaciones = (
        await db.execute(select(Reservation).where(Reservation.property_id.in_(property_ids)))
    ).scalars().all() if property_ids else []

    return {
        "residente": {
            "id": str(resident.id),
            "nombre": resident.nombre,
            "telefono": resident.telefono,
            "email": resident.email,
            "aviso_privacidad_aceptado_en": resident.aviso_privacidad_aceptado_en,
        },
        "viviendas": [{"id": str(p.id), "identificador": p.identificador} for p in propiedades],
        "votos_emitidos": [{"poll_id": str(v.poll_id), "option_id": str(v.option_id)} for v in votos],
        "avisos_leidos": [
            {"announcement_id": str(r.announcement_id), "leido_at": r.leido_at} for r in lecturas
        ],
        "reservaciones_solicitadas": [
            {"amenity_id": str(r.amenity_id), "fecha_inicio": r.fecha_inicio, "estado": r.estado.value}
            for r in reservaciones
        ],
    }


async def export_personal_data(db: AsyncSession, resident_id: uuid.UUID, user_id: uuid.UUID) -> dict[str, Any]:
    """HU derecho de Acceso: todo lo que Vivecom tiene ligado a esta persona."""
    resident = await db.get(Resident, resident_id)
    datos = await _resident_data_export(db, resident) if resident is not None else {}

    incidencias = (
        await db.execute(select(Incident).where(Incident.reportado_por == user_id))
    ).scalars().all()
    objetos = (
        await db.execute(select(LostFoundItem).where(LostFoundItem.publicado_por == user_id))
    ).scalars().all()

    datos["incidencias_reportadas"] = [{"id": str(i.id), "descripcion": i.descripcion, "estado": i.estado.value} for i in incidencias]
    datos["objetos_publicados"] = [{"id": str(o.id), "descripcion": o.descripcion, "estado": o.estado.value} for o in objetos]
    return datos


async def accept_privacy_notice(db: AsyncSession, resident_id: uuid.UUID) -> Resident | None:
    """
    None si resident_id no resuelve a un Resident real. Reachable porque
    UserAccount.resident_id (a diferencia de toda otra referencia entre
    tablas de este proyecto) no tiene ForeignKey — nada impide que apunte a
    una fila que ya no existe. Antes esto se deshacía en un AttributeError
    sin capturar (500) en vez de dejar que el endpoint responda 404.
    """
    resident = await db.get(Resident, resident_id)
    if resident is None:
        return None
    resident.aviso_privacidad_aceptado_en = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    return resident


async def erase_personal_data(db: AsyncSession, resident_id: uuid.UUID) -> Resident | None:
    """
    Derecho de Cancelación: anonimiza en vez de borrar la fila — ver el
    aviso al inicio del archivo sobre por qué (excepción de conservación
    contable de LFPDPPP; el historial financiero cuelga de Property, no de
    esta fila, así que anonimizar aquí no lo afecta). None si resident_id no
    resuelve a un Resident real — ver la nota en accept_privacy_notice.
    """
    resident = await db.get(Resident, resident_id)
    if resident is None:
        return None
    resident.nombre = "[Eliminado a solicitud del titular]"
    resident.telefono = ""
    resident.email = None
    resident.datos_eliminados = True
    await db.commit()
    return resident
