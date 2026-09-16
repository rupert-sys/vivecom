import uuid

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database_base import TenantBase


class Amenity(TenantBase):
    """Amenidad reservable (F2-16, HU-C06). Ver modelo_datos_vivecom.md."""

    __tablename__ = "amenity"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String)
    # Tiempo límite de respuesta para aprobar/rechazar una reservación de
    # esta amenidad (HU-C07): si nadie responde dentro de este plazo, se
    # rechaza automáticamente. Configurable por amenidad, no global.
    periodo_limite_horas: Mapped[int] = mapped_column(Integer)


class AmenityApprover(TenantBase):
    """
    Qué miembros del comité (rol comite_aprobador) pueden aprobar
    reservaciones de esta amenidad (F2-17, HU-C07): "el administrador
    designa a uno o más miembros del comité como aprobadores".
    """

    __tablename__ = "amenity_approver"

    amenity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("amenity.id"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user_account.id"), primary_key=True)
