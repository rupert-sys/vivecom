import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.validators import validar_clabe


class TenantClabeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str
    clabe_destino: str | None  # None: el condominio (alta por /signup) todavía no la configuró.


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
    clabe_anterior: str | None
    clabe_nueva: str
    cambiado_por: uuid.UUID
    fecha: datetime


class TenantConfigRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str
    tiene_logo: bool


class TenantNombreUpdate(BaseModel):
    nombre: str = Field(min_length=1, max_length=200)
