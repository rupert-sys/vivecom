import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class VisitorQRRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    property_id: uuid.UUID | None
    codigo: str
    usado: bool
    fecha_generado: datetime
    fecha_usado: datetime | None
    tipo: str = "visitante"
    descripcion: str | None = None
    nombre_visitante: str | None = None
    horario_esperado: datetime | None = None
    numero_personas: int | None = None
    qr_payload: str | None = None


class VisitorQRCreate(BaseModel):
    """El residente captura quién viene, cuándo lo espera y cuántos son, para que el guardia lo vea al validar."""

    nombre_visitante: str = Field(min_length=1)
    numero_personas: int = Field(default=1, ge=1)
    horario_esperado: datetime | None = None


class ProviderQRCreate(BaseModel):
    """Código que el guardia emite para un proveedor (quién es, y a qué vivienda va si aplica)."""

    descripcion: str = Field(min_length=1)
    property_id: uuid.UUID | None = None


class VisitorQRValidateResult(BaseModel):
    valido: bool
    motivo: str | None = None  # "no_existe" | "ya_usado", cuando valido=False
    property_id: uuid.UUID | None = None
    # Para que el guardia sepa a quién deja pasar, a dónde, y a quién espera.
    tipo: Literal["visitante", "proveedor"] | None = None
    descripcion: str | None = None
    vivienda: str | None = None
    nombre_visitante: str | None = None
    horario_esperado: datetime | None = None
    numero_personas: int | None = None
    nombre_residente: str | None = None
    telefono_residente: str | None = None
