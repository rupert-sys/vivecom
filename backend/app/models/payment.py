import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database_base import TenantBase


class EstadoPago(str, enum.Enum):
    pendiente = "pendiente"  # detectado pero sin conciliar todavía (ej. referencia no reconocida)
    confirmado = "confirmado"
    rechazado = "rechazado"


class Payment(TenantBase):
    """
    Un depósito SPEI detectado por el proveedor de recepción (STP/Fintoc).
    property_id es nullable: si la referencia numérica no coincide con
    ninguna vivienda, el pago se guarda igual para que el tesorero lo
    resuelva manualmente (ver HU-A06), en vez de perderse.
    """

    __tablename__ = "payment"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    property_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("property.id"), nullable=True)
    monto: Mapped[float] = mapped_column(Numeric(10, 2))
    estado: Mapped[EstadoPago] = mapped_column(Enum(EstadoPago), default=EstadoPago.pendiente)
    referencia_recibida: Mapped[str] = mapped_column(String(7))
    # Identificador único de la transacción SPEI (evita procesar el mismo
    # webhook dos veces si el proveedor lo reintenta — ver F1-07).
    clave_rastreo: Mapped[str] = mapped_column(String, unique=True)
    proveedor: Mapped[str] = mapped_column(String, default="stp")
    fecha_deteccion: Mapped[datetime] = mapped_column(DateTime)
