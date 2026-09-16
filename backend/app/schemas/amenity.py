import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AmenityCreate(BaseModel):
    nombre: str
    periodo_limite_horas: int


class AmenityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str
    periodo_limite_horas: int


class AmenityApproverCreate(BaseModel):
    user_id: uuid.UUID


class AmenityBusySlot(BaseModel):
    fecha_inicio: datetime
    fecha_fin: datetime
