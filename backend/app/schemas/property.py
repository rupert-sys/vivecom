import uuid

from pydantic import BaseModel, ConfigDict


class PropertyCreate(BaseModel):
    identificador: str


class PropertyUpdate(BaseModel):
    identificador: str | None = None


class PropertyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    identificador: str
    referencia_pago: str
    saldo_a_favor: float
