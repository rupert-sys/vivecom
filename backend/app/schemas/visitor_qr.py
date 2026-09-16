import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class VisitorQRRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    property_id: uuid.UUID
    codigo: str
    usado: bool
    fecha_generado: datetime
    fecha_usado: datetime | None


class VisitorQRValidateResult(BaseModel):
    valido: bool
    motivo: str | None = None  # "no_existe" | "ya_usado", cuando valido=False
    property_id: uuid.UUID | None = None
