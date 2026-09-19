import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PackageCreate(BaseModel):
    property_id: uuid.UUID
    # UUID generado por la app caseta al capturar la llegada sin conexión.
    client_id: uuid.UUID | None = None


class PackageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    property_id: uuid.UUID
    fecha_llegada: datetime
    fecha_recogido: datetime | None
