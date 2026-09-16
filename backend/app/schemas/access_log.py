import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.access_log import TipoAcceso


class AccessLogCreate(BaseModel):
    property_id: uuid.UUID | None = None  # None: proveedor sin vivienda asociada
    tipo: TipoAcceso
    placas: list[str] = []  # F2-03: vehículos asociados a este acceso


class AccessLogRead(BaseModel):
    id: uuid.UUID
    property_id: uuid.UUID | None
    tipo: TipoAcceso
    hora_entrada: datetime
    hora_salida: datetime | None
    placas: list[str] = []
