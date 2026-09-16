import enum
import uuid
from datetime import date

from sqlalchemy import Date, Enum, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database_base import TenantBase


class PeriodicidadPresupuesto(str, enum.Enum):
    """
    Distinta de Periodicidad (fee.py: mensual/bimestral) — un presupuesto se
    carga mensual por defecto, o anual para actividades específicas (HU-A10).
    """

    mensual = "mensual"
    anual = "anual"


class Budget(TenantBase):
    """
    Presupuesto por categoría y periodo (F1-16, HU-A10). `periodo` es el
    primer día del mes (periodicidad mensual) o el primer día de enero del
    año (periodicidad anual) al que corresponde. Ver modelo_datos_vivecom.md.
    """

    __tablename__ = "budget"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    categoria: Mapped[str] = mapped_column(String)
    periodicidad: Mapped[PeriodicidadPresupuesto] = mapped_column(
        Enum(PeriodicidadPresupuesto), default=PeriodicidadPresupuesto.mensual
    )
    periodo: Mapped[date] = mapped_column(Date)
    monto_planeado: Mapped[float] = mapped_column(Numeric(10, 2))
