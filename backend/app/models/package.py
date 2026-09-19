import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database_base import TenantBase


class Package(TenantBase):
    """
    Paquetería (F2-04, HU-S05). Ver modelo_datos_vivecom.md. Dos
    notificaciones distintas, cada una una sola vez — mismo patrón boolean-
    flag que FeeCharge.confirmacion_enviada (F1-13) y
    Announcement.notificacion_enviada (F1-32): una al llegar, otra al
    recogerse (cierra el registro).
    """

    __tablename__ = "package"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    property_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("property.id"))
    fecha_llegada: Mapped[datetime] = mapped_column(DateTime)
    fecha_recogido: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notificacion_llegada_enviada: Mapped[bool] = mapped_column(Boolean, default=False)
    notificacion_recogido_enviada: Mapped[bool] = mapped_column(Boolean, default=False)
    # UUID generado por la app caseta al registrar la llegada sin conexión: un
    # reintento de sincronización (mismo client_id) no duplica el paquete — mismo
    # esquema que AccessLog.client_id e Incident.client_id (F2-07/F2-11).
    client_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, unique=True, index=True)
