"""
F2-02/F2-03: QR de acceso temporal de un solo uso (HU-S02, HU-S03).
"""

import json
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.property import Property
from app.models.visitor_qr import VisitorQR


async def generate_visitor_qr(
    db: AsyncSession,
    property_id: uuid.UUID | None,
    tipo: str = "visitante",
    descripcion: str | None = None,
    nombre_visitante: str | None = None,
    numero_personas: int | None = None,
    horario_esperado: datetime | None = None,
    vivienda_nombre: str | None = None,
    residente_nombre: str | None = None,
    residente_telefono: str | None = None,
) -> VisitorQR:
    codigo = secrets.token_urlsafe(16)
    horario_utc = horario_esperado.astimezone(timezone.utc).replace(tzinfo=None) if horario_esperado else None
    qr = VisitorQR(
        property_id=property_id,
        codigo=codigo,
        fecha_generado=datetime.now(timezone.utc).replace(tzinfo=None),
        tipo=tipo,
        descripcion=descripcion,
        nombre_visitante=nombre_visitante,
        numero_personas=numero_personas,
        horario_esperado=horario_utc,
    )
    if tipo == "visitante":
        # Congelado al generarse (no se recalcula si el residente cambia su nombre/teléfono después):
        # es lo que la app residente codifica en la imagen del QR, para que el guardia pueda leer quién
        # es el visitante y a quién llamar SIN conexión. La validación de "ya se usó" sigue en línea.
        qr.qr_payload = json.dumps(
            {
                "codigo": codigo,
                "nombre_visitante": nombre_visitante,
                "numero_personas": numero_personas,
                "horario_esperado": horario_utc.isoformat() if horario_utc else None,
                "vivienda": vivienda_nombre,
                "nombre_residente": residente_nombre,
                "telefono_residente": residente_telefono,
            }
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
    nombre_visitante: str | None = None
    horario_esperado: datetime | None = None
    numero_personas: int | None = None
    nombre_residente: str | None = None
    telefono_residente: str | None = None


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
    # nombre_residente/telefono_residente no son columnas propias (ver generate_visitor_qr): viven solo
    # dentro de qr_payload, la misma fuente que la app residente codifica en la imagen del QR — así el
    # guardia ve exactamente lo mismo en línea o leyendo el código sin conexión.
    datos_payload: dict = json.loads(qr.qr_payload) if qr.qr_payload else {}
    qr.usado = True
    qr.fecha_usado = datetime.now(timezone.utc).replace(tzinfo=None)
    resultado = ResultadoValidacionQR(
        valido=True,
        property_id=qr.property_id,
        tipo=qr.tipo,
        descripcion=qr.descripcion,
        vivienda=propiedad.identificador if propiedad is not None else None,
        nombre_visitante=qr.nombre_visitante,
        horario_esperado=qr.horario_esperado,
        numero_personas=qr.numero_personas,
        nombre_residente=datos_payload.get("nombre_residente"),
        telefono_residente=datos_payload.get("telefono_residente"),
    )
    await db.commit()
    return resultado
