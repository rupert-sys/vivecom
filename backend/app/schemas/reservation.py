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
    cuota_pagada: bool = False
    # Cuota de uso de la amenidad al solicitarla (0 = sin cuota) — la app la muestra.
    cuota: float = 0
