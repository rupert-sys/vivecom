import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.access_log import TipoAcceso


class AccessLogCreate(BaseModel):
    property_id: uuid.UUID | None = None  # None: proveedor sin vivienda asociada
    tipo: TipoAcceso
    placas: list[str] = []  # F2-03: vehículos asociados a este acceso
    # F2-07: UUID generado por la app caseta — ver client_id en el modelo.
    client_id: uuid.UUID | None = None


class AccessLogRead(BaseModel):
    id: uuid.UUID
    property_id: uuid.UUID | None
    tipo: TipoAcceso
    hora_entrada: datetime
    hora_salida: datetime | None
    placas: list[str] = []
