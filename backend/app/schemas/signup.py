import uuid

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.validators import validar_clabe


class TenantSignupRequest(BaseModel):
    nombre_condominio: str = Field(min_length=1)
    clabe_destino: str
    admin_email: EmailStr
    admin_password: str = Field(min_length=8)

    _validar_clabe = field_validator("clabe_destino")(validar_clabe)


class TenantSignupResponse(BaseModel):
    tenant_id: uuid.UUID
    nombre: str
    admin_email: str
