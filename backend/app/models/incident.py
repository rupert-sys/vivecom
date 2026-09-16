import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database_base import TenantBase


class EstadoIncidencia(str, enum.Enum):
    abierta = "abierta"
    en_proceso = "en_proceso"
    resuelta = "resuelta"


class Incident(TenantBase):
    """
    Incidencia reportada por el guardia, con seguimiento (F2-05, HU-S06).
    Ver modelo_datos_vivecom.md. Visible para admin Y comité, no solo el
    admin — a diferencia de casi todo lo demás en este proyecto, que es
    admin-only para escritura.
    """

    __tablename__ = "incident"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    reportado_por: Mapped[uuid.UUID] = mapped_column(ForeignKey("user_account.id"))
    estado: Mapped[EstadoIncidencia] = mapped_column(Enum(EstadoIncidencia), default=EstadoIncidencia.abierta)
    descripcion: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime)


class IncidentUpdate(TenantBase):
    """Entrada de seguimiento (comentario) sobre una incidencia. Ver modelo_datos_vivecom.md."""

    __tablename__ = "incident_update"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("incident.id"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user_account.id"))
    comentario: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime)
