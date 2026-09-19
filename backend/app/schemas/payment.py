import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

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
    registrado_por: uuid.UUID | None = None


class PaymentResolveRequest(BaseModel):
    property_id: uuid.UUID


class ManualPaymentCreate(BaseModel):
    """Pago capturado a mano por el tesorero (efectivo, o una transferencia que el SPEI no detectó)."""

    property_id: uuid.UUID
    monto: float = Field(gt=0)
    metodo: Literal["efectivo", "transferencia"] = "efectivo"
