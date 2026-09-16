import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PackageCreate(BaseModel):
    property_id: uuid.UUID


class PackageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    property_id: uuid.UUID
    fecha_llegada: datetime
    fecha_recogido: datetime | None
