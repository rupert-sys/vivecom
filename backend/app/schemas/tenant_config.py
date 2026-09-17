import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.core.validators import validar_clabe


class TenantClabeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str
    clabe_destino: str


class ClabeChangeRequest(BaseModel):
    clabe_nueva: str
    confirmo_cambio: bool

    _validar_clabe = field_validator("clabe_nueva")(validar_clabe)

    @field_validator("confirmo_cambio")
    @classmethod
    def debe_confirmar_explicitamente(cls, v: bool) -> bool:
        if not v:
            raise ValueError(
                "Cambiar la cuenta de destino requiere confirmación explícita: "
                "envía confirmo_cambio=true para proceder."
            )
        return v


class ClabeChangeLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    clabe_anterior: str
    clabe_nueva: str
    cambiado_por: uuid.UUID
    fecha: datetime
