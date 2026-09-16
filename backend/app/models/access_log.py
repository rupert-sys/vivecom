import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database_base import TenantBase


class TipoAcceso(str, enum.Enum):
    residente = "residente"
    visitante = "visitante"
    proveedor = "proveedor"


class AccessLog(TenantBase):
    """
    Registro de entrada/salida (F2-01, HU-S01). Ver modelo_datos_vivecom.md.
    property_id es nullable: un proveedor puede no tener vivienda asociada
    (ej. mensajería para el condominio en general). Sin límite de
    visitantes ni restricción de horario — alcance §10.2.
    """

    __tablename__ = "access_log"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    property_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("property.id"), nullable=True)
    tipo: Mapped[TipoAcceso] = mapped_column(Enum(TipoAcceso))
    hora_entrada: Mapped[datetime] = mapped_column(DateTime)
    hora_salida: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
