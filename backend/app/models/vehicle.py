import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database_base import TenantBase


class Vehicle(TenantBase):
    """Vehículo asociado a un acceso (F2-03, HU-S04). Ver modelo_datos_vivecom.md."""

    __tablename__ = "vehicle"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    access_log_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("access_log.id"))
    placa: Mapped[str] = mapped_column(String)
