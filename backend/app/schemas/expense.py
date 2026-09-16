import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class ExpenseCreate(BaseModel):
    categoria: str
    monto: float
    comprobante_url: str = Field(min_length=1)  # obligatorio, ver HU-A09
    fecha: date


class ExpenseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    categoria: str
    monto: float
    comprobante_url: str
    fecha: date
