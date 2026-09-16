import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.payment import EstadoPago


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    property_id: uuid.UUID | None
    monto: float
    estado: EstadoPago
    referencia_recibida: str
    clave_rastreo: str
    proveedor: str
    fecha_deteccion: datetime


class PaymentResolveRequest(BaseModel):
    property_id: uuid.UUID
