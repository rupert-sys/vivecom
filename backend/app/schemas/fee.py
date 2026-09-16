import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict

from app.models.fee import Periodicidad


class FeeCreate(BaseModel):
    monto: float
    periodicidad: Periodicidad
    activa_desde: date


class FeeUpdate(BaseModel):
    monto: float | None = None
    periodicidad: Periodicidad | None = None
    activa_desde: date | None = None


class FeeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    monto: float
    periodicidad: Periodicidad
    activa_desde: date
