import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.reservation import EstadoReserva


class ReservationCreate(BaseModel):
    amenity_id: uuid.UUID
    fecha_inicio: datetime
    fecha_fin: datetime


class ReservationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    amenity_id: uuid.UUID
    property_id: uuid.UUID
    fecha_inicio: datetime
    fecha_fin: datetime
    estado: EstadoReserva
    aprobador_id: uuid.UUID | None
