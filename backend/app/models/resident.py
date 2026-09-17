import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database_base import TenantBase


class RolOcupacion(str, enum.Enum):
    propietario = "propietario"
    inquilino = "inquilino"


class Resident(TenantBase):
    """Persona. Puede estar ligada a más de una Property (ver resident_property)."""

    __tablename__ = "resident"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String)
    telefono: Mapped[str] = mapped_column(String)  # usado para WhatsApp/SMS
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    # F3-02, LFPDPPP: consentimiento del aviso de privacidad y derecho de
    # cancelación (ARCO). datos_eliminados no borra la fila — anonimiza
    # nombre/telefono/email y conserva el id para no romper el historial
    # financiero (FeeCharge/Payment cuelgan de Property, no de Resident,
    # pero ResidentProperty y los reportes de incidencias/objetos perdidos sí
    # referencian directamente al usuario). Ver privacy_service.py.
    aviso_privacidad_aceptado_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    datos_eliminados: Mapped[bool] = mapped_column(Boolean, default=False)


class ResidentProperty(TenantBase):
    """
    Tabla puente N:N. Un mismo Resident puede tener varias Property (ver alcance,
    sección 2): cada vivienda se administra de forma independiente, así que esta
    tabla solo registra la relación — las finanzas, accesos, etc. siempre se
    anclan a la Property, nunca directamente al Resident.
    """

    __tablename__ = "resident_property"

    resident_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("resident.id"), primary_key=True)
    # F2-22: la PK compuesta (resident_id, property_id) sirve consultas que
    # filtran por resident_id (o por ambas), pero NO a las que filtran solo
    # por property_id — que es exactamente el patrón más común aquí
    # (telefonos_de_vivienda, list_property_residents, recordatorios,
    # notificaciones de paquetería): todas preguntan "¿quién vive en esta
    # vivienda?", nunca al revés. index=True agrega ese índice que la PK no cubre.
    property_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("property.id"), primary_key=True, index=True)
    rol: Mapped[RolOcupacion] = mapped_column(Enum(RolOcupacion))
