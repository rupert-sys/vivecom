import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.models.cash_movement import Caja, TipoMovimiento


class CashMovementCreate(BaseModel):
    caja: Caja
    tipo: TipoMovimiento
    monto: float = Field(gt=0)
    motivo: str = Field(min_length=1)
    fecha: date


class CashMovementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    caja: Caja
    tipo: TipoMovimiento
    monto: float
    motivo: str
    fecha: date
    registrado_por: uuid.UUID


class CashBalance(BaseModel):
    """Saldo actual de cada caja — ingresos menos egresos de todo su historial (F0-12)."""

    chica: float
    grande: float
