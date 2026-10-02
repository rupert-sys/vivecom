import enum
import uuid
from datetime import date

from sqlalchemy import Date, Enum, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database_base import TenantBase


class Caja(str, enum.Enum):
    chica = "chica"
    grande = "grande"


class TipoMovimiento(str, enum.Enum):
    ingreso = "ingreso"
    egreso = "egreso"


class CashMovement(TenantBase):
    """
    F0-12: movimiento de caja chica o caja grande (efectivo físico que administra tesorería, distinto del
    dinero en la cuenta bancaria del condominio — ver Payment/Expense). El saldo de cada caja NO se guarda
    como campo aparte: se calcula sumando ingresos y restando egresos (ver cash_movements_service.py), igual
    que un libro de caja real — así nunca puede quedar desincronizado de su propio historial.
    """

    __tablename__ = "cash_movement"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    caja: Mapped[Caja] = mapped_column(Enum(Caja))
    tipo: Mapped[TipoMovimiento] = mapped_column(Enum(TipoMovimiento))
    monto: Mapped[float] = mapped_column(Numeric(10, 2))
    motivo: Mapped[str] = mapped_column(String)
    fecha: Mapped[date] = mapped_column(Date)
    # Quién lo registró — mismo patrón que Payment.registrado_por (pago manual): auditoría de quién metió o
    # sacó dinero de la caja física, exigible por el reglamento igual que un recibo (Art. 7 VI).
    registrado_por: Mapped[uuid.UUID] = mapped_column()
