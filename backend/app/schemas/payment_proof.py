import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.payment_proof import EstadoComprobante


class PaymentProofCreate(BaseModel):
    monto: float = Field(gt=0)
    fecha_pago: date | None = None  # la que dice el comprobante del banco
    nota: str | None = Field(default=None, max_length=500)
    archivo_id: uuid.UUID  # POST /files con kind=pago


class PaymentProofAccept(BaseModel):
    # Lo que de verdad llegó, si difiere de lo que declaró el residente.
    monto: float | None = Field(default=None, gt=0)
    # Confirma que NO es el mismo pago que ya detectó el SPEI (ver accept_payment_proof).
    forzar: bool = False


class PaymentProofReject(BaseModel):
    motivo: str = Field(min_length=1, max_length=300)


class PaymentProofRead(BaseModel):
    id: uuid.UUID
    property_id: uuid.UUID
    monto: float
    fecha_pago: date | None
    nota: str | None
    estado: EstadoComprobante
    created_at: datetime
    revisado_en: datetime | None
    motivo_rechazo: str | None
    payment_id: uuid.UUID | None
    # Enlace firmado de vida corta al archivo (foto o PDF).
    archivo_url: str
