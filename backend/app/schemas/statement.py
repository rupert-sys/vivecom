import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.fee_charge import EstadoCargo
from app.models.payment import EstadoPago


class FeeChargeSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    periodo: date
    monto_base: float
    recargo_aplicado: float
    estado: EstadoCargo


class PaymentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    monto: float
    estado: EstadoPago
    fecha_deteccion: datetime
    clave_rastreo: str


class AccountStatement(BaseModel):
    property_id: uuid.UUID
    identificador: str
    saldo_a_favor: float
    deuda_total: float
    cargos: list[FeeChargeSummary]
    pagos: list[PaymentSummary]
    # Reglamento: la vivienda con cuotas vencidas pierde ciertos derechos. La app
    # los muestra en un aviso en vez de que el residente los descubra al fallar.
    en_mora: bool = False
    # Tiene un acuerdo de pago vigente: lo cubierto por él no cuenta como mora (conserva voto y áreas comunes).
    en_acuerdo: bool = False
    restricciones_por_mora: list[str] = []
