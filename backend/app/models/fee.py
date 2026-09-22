import enum
import uuid
from datetime import date

from sqlalchemy import Date, Enum, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database_base import TenantBase


class Periodicidad(str, enum.Enum):
    mensual = "mensual"
    bimestral = "bimestral"
    # Se puede elegir, pero hoy se GENERA con la misma cadencia que "mensual" (ver fee_charge_service): facturar
    # de verdad cada semana necesitaría que periodo/FeeCharge dejen de ser "un mes" y que el cálculo de recargo
    # (denominado en meses, reglamento Art. 9) cambie de unidad — no se implementó, marcado explícitamente.
    semanal = "semanal"
    # Pago único (p. ej. una cuota extraordinaria o de proyecto): NO participa en la selección de "la cuota
    # recurrente vigente" (ver fee_charge_service.get_active_fee) — si lo hiciera, en cuanto pasara su fecha
    # reemplazaría en silencio a la cuota mensual real para todos los periodos siguientes. En vez de eso, genera
    # exactamente un cargo, para el periodo que sea igual a `activa_desde` (aquí significa "el periodo al que
    # aplica", no "a partir de cuándo" como en las periodicidades recurrentes).
    unica = "unica"


class Fee(TenantBase):
    """
    Configuración de cuota del condominio (monto y periodicidad). El recargo
    por mora NO vive aquí — sale del reglamento de cada condominio
    (models/reglamento.py); sin configurar aplica el default de la
    plataforma (10% único, día 6), ver app/core/business_rules.py. Ver
    alcance, sección 3.1.
    """

    __tablename__ = "fee"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    monto: Mapped[float] = mapped_column(Numeric(10, 2))
    periodicidad: Mapped[Periodicidad] = mapped_column(Enum(Periodicidad))
    activa_desde: Mapped[date] = mapped_column(Date)
