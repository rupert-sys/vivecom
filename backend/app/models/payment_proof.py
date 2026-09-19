import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database_base import TenantBase


class EstadoComprobante(str, enum.Enum):
    pendiente = "pendiente"  # el residente lo mandó, tesorería aún no lo revisa
    aceptado = "aceptado"  # tesorería lo validó y registró el pago
    rechazado = "rechazado"


class PaymentProof(TenantBase):
    """
    Comprobante de pago que el residente adjunta desde su app (captura o PDF del
    banco): "ya pagué, aquí está". No es un pago: hasta que tesorería lo acepta no
    se concilia contra ningún cargo — al aceptarlo se registra un Payment normal.
    """

    __tablename__ = "payment_proof"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    property_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("property.id"), index=True)
    monto: Mapped[float] = mapped_column(Numeric(10, 2))
    fecha_pago: Mapped[date | None] = mapped_column(Date, nullable=True)  # la que dice el comprobante
    nota: Mapped[str | None] = mapped_column(Text, nullable=True)
    archivo_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stored_file.id"))
    estado: Mapped[EstadoComprobante] = mapped_column(Enum(EstadoComprobante), default=EstadoComprobante.pendiente)
    enviado_por: Mapped[uuid.UUID] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(DateTime)
    revisado_por: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    revisado_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    motivo_rechazo: Mapped[str | None] = mapped_column(String, nullable=True)
    # Pago que se registró al aceptarlo.
    payment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("payment.id"), nullable=True)
