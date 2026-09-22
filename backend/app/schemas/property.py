import uuid

from pydantic import BaseModel, ConfigDict


class PropertyCreate(BaseModel):
    identificador: str


class PropertyUpdate(BaseModel):
    identificador: str | None = None


class PropertyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    identificador: str
    referencia_pago: str
    saldo_a_favor: float
    # Quién vive ahí, para la lista de Viviendas — el primer propietario (o, si no hay, el primer inquilino),
    # por nombre; None si la vivienda no tiene ningún residente ligado todavía. Ver residents_summary_service.py.
    residente_principal: str | None = None
    residente_principal_rol: str | None = None  # "propietario" | "inquilino"
    total_residentes: int = 0
