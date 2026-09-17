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
    # F2-12: se llena cuando estado pasa a "resuelta" y se limpia si se
    # reabre (la máquina de estados es permisiva, ver change_incident_status)
    # — así siempre refleja la transición A resuelta más reciente, para
    # poder medir tiempos de resolución en el dashboard de seguridad.
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # F2-09: igual que LostFoundItem.foto_url — no hay infraestructura de
    # storage de archivos en el proyecto todavía, así que es una URL de
    # texto (subida a donde sea que el cliente resuelva) y no un upload.
    foto_url: Mapped[str | None] = mapped_column(nullable=True)
    # F2-07/F2-11: mismo propósito que AccessLog.client_id — idempotencia de
    # sync offline desde la app caseta.
    client_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, unique=True, index=True)


class IncidentUpdate(TenantBase):
    """Entrada de seguimiento (comentario) sobre una incidencia. Ver modelo_datos_vivecom.md."""

    __tablename__ = "incident_update"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # F2-22: filtrado por incident_id en GET /incidents/{id}/comments.
    incident_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("incident.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user_account.id"))
    comentario: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime)
