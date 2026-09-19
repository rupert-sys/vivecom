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


class ProviderQRCreate(BaseModel):
    """Código que el guardia emite para un proveedor (quién es, y a qué vivienda va si aplica)."""

    descripcion: str = Field(min_length=1)
    property_id: uuid.UUID | None = None


class VisitorQRValidateResult(BaseModel):
    valido: bool
    motivo: str | None = None  # "no_existe" | "ya_usado", cuando valido=False
    property_id: uuid.UUID | None = None
    # Para que el guardia sepa a quién deja pasar y a dónde.
    tipo: Literal["visitante", "proveedor"] | None = None
    descripcion: str | None = None
    vivienda: str | None = None
