import uuid

from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database_base import ControlBase


class Tenant(ControlBase):
    """Vive en el schema público de control. Ver modelo_datos_vivecom.md."""

    __tablename__ = "tenant"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String)
    clabe_destino: Mapped[str] = mapped_column(String(18))
    precio_por_vivienda: Mapped[float] = mapped_column(Numeric(10, 2), default=25.00)
    schema_name: Mapped[str] = mapped_column(String, unique=True)
