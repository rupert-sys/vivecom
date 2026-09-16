import enum
import uuid
from datetime import date

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database_base import TenantBase


class EstadoCargo(str, enum.Enum):
    pendiente = "pendiente"
    pagado = "pagado"
    vencido = "vencido"


class FeeCharge(TenantBase):
    """
    Cargo generado para una vivienda en un ciclo específico. Se crea
    automáticamente (job periódico, ver app/workers/tasks.py) a partir de la
    configuración vigente en Fee. Ver alcance sección 3.1 y modelo_datos_vivecom.md.
    """

    __tablename__ = "fee_charge"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    property_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("property.id"))
    fee_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("fee.id"))
    periodo: Mapped[date] = mapped_column(Date)  # primer día del mes/ciclo que corresponde
    monto_base: Mapped[float] = mapped_column(Numeric(10, 2))
    recargo_aplicado: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    estado: Mapped[EstadoCargo] = mapped_column(Enum(EstadoCargo), default=EstadoCargo.pendiente)
    # Se llena al conciliar automáticamente un depósito (ver F1-07,
    # payment_reconciliation_service.py). Nullable: un cargo pendiente o
    # vencido todavía no tiene pago asociado.
    payment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("payment.id"), nullable=True)
    # F1-13: última fecha en que se mandó un recordatorio de este cargo (se
    # manda una vez por día, no en cada corrida del job) y si ya se mandó la
    # confirmación de pago (una sola vez, cuando el cargo pasa a pagado, sin
    # importar qué lo pagó — depósito directo, saldo a favor, pago
    # anticipado o resolución manual del tesorero).
    recordatorio_enviado_en: Mapped[date | None] = mapped_column(Date, nullable=True)
    confirmacion_enviada: Mapped[bool] = mapped_column(Boolean, default=False)
