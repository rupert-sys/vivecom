import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class AgreementRequest(BaseModel):
    """La solicitud por escrito (Art. 1 VIII y 9 VII): la causa y cómo propone pagar."""

    # Solo lo usa el administrador, que captura la solicitud que el vecino entregó en papel.
    property_id: uuid.UUID | None = None
    causa: str = Field(min_length=20, max_length=1000)
    numero_de_pagos: int = Field(ge=1, le=6)  # 1 = "una nueva fecha"; más = parcialidades mensuales
    primer_pago: date
    archivo_id: uuid.UUID | None = None  # documento de respaldo (POST /files, kind=acuerdo)


class ScheduledPayment(BaseModel):
    fecha: date
    monto: float = Field(gt=0)


class AgreementApprove(BaseModel):
    # El comité decide, acuerdo por acuerdo, si el recargo se congela mientras se cumple.
    congela_recargo: bool = True
    # Otros términos que los propuestos: un calendario propio (debe sumar la deuda cubierta).
    pagos: list[ScheduledPayment] | None = None


class AgreementReject(BaseModel):
    motivo: str = Field(min_length=1, max_length=300)


class NextPayment(BaseModel):
    fecha: date
    monto: float


class AgreementRead(BaseModel):
    id: uuid.UUID
    property_id: uuid.UUID
    vivienda: str | None = None
    estado: str  # solicitado | vigente | rechazado | cumplido | incumplido | cancelado
    causa: str
    propuesta_pagos: int
    propuesta_primer_pago: date
    capturado_por_admin: bool
    created_at: datetime
    decidido_en: datetime | None
    motivo_rechazo: str | None
    # Enlace firmado al documento de respaldo.
    archivo_url: str | None = None
    # Lo acordado (al aprobar) y cómo va el cumplimiento.
    vigente_desde: datetime | None = None
    calendario: list[ScheduledPayment] | None = None
    congela_recargo: bool | None = None
    deuda_inicial: float | None = None
    abonado: float | None = None
    pendiente_cubierto: float | None = None
    proximo_pago: NextPayment | None = None
    # Para el comité: cuántos acuerdos anteriores de esta vivienda se incumplieron (0 para el residente).
    incumplimientos_previos: int = 0
