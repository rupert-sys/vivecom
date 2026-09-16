import enum
import uuid
from datetime import date

from sqlalchemy import Date, Enum, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database_base import TenantBase


class Periodicidad(str, enum.Enum):
    mensual = "mensual"
    bimestral = "bimestral"


class Fee(TenantBase):
    """
    Configuración de cuota del condominio (monto y periodicidad). El recargo
    por mora NO vive aquí — es una regla global de la plataforma (10%, día 6
    de cada mes), ver app/core/business_rules.py. Ver alcance, sección 3.1.
    """

    __tablename__ = "fee"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    monto: Mapped[float] = mapped_column(Numeric(10, 2))
    periodicidad: Mapped[Periodicidad] = mapped_column(Enum(Periodicidad))
    activa_desde: Mapped[date] = mapped_column(Date)
