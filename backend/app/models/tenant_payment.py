import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database_base import ControlBase


class TipoPagoTenant(str, enum.Enum):
    """Cómo el condominio le paga su cuota a Vivecom — no cómo los residentes le pagan al condominio
    (eso es app/models/payment.py, dentro del schema de cada tenant)."""

    efectivo = "efectivo"
    transferencia = "transferencia"


class TenantPayment(ControlBase):
    """
    Historial de pagos de UN condominio A Vivecom, con su recibo de comprobación. Vive en el
    schema de control junto a `tenant` — portal de administrador principal (ver api/staff_tenants.py).
    """

    __tablename__ = "tenant_payment"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id"))
    fecha: Mapped[date] = mapped_column(Date)
    monto: Mapped[float] = mapped_column(Numeric(10, 2))
    tipo_pago: Mapped[TipoPagoTenant] = mapped_column(Enum(TipoPagoTenant))
    notas: Mapped[str | None] = mapped_column(String, nullable=True)
    # Recibo adjunto (foto o PDF), mismo almacenamiento que el resto del sistema (file_storage.py) pero con
    # una llave fuera de cualquier schema de tenant (ver _llave_recibo en api/staff_tenants.py): este pago
    # no pertenece a ningún condominio desde el punto de vista del almacenamiento, solo por tenant_id aquí.
    recibo_storage_key: Mapped[str | None] = mapped_column(String, nullable=True)
    recibo_content_type: Mapped[str | None] = mapped_column(String, nullable=True)
    recibo_nombre_original: Mapped[str | None] = mapped_column(String, nullable=True)
    registrado_por: Mapped[uuid.UUID] = mapped_column()  # vivecom_staff.id (vive en otra tabla, sin FK cruzada)
    registrado_en: Mapped[datetime] = mapped_column(DateTime)
