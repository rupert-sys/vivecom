import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database_base import TenantBase


class Vehicle(TenantBase):
    """Vehículo asociado a un acceso (F2-03, HU-S04). Ver modelo_datos_vivecom.md."""

    __tablename__ = "vehicle"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # F2-22: filtrado por access_log_id en cada consulta de placas (ahora en
    # lote con IN (...), ver access_log.py — antes era una consulta por
    # access log, N+1).
    access_log_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("access_log.id"), index=True)
    placa: Mapped[str] = mapped_column(String)
