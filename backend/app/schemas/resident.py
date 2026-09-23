import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.resident import RolOcupacion


class ResidentCreate(BaseModel):
    nombre: str
    telefono: str
    email: EmailStr | None = None


class ResidentUpdate(BaseModel):
    nombre: str | None = None
    telefono: str | None = None
    email: EmailStr | None = None


class ResidentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str
    telefono: str
    email: str | None


class LinkResidentToProperty(BaseModel):
    resident_id: uuid.UUID
    rol: RolOcupacion


class ResidentActivationPreview(BaseModel):
    # Lo que la app muestra en vivo mientras el residente escribe su condominio/número de casa, antes de que
    # termine de llenar el resto del formulario — así confirma que es su vivienda antes de registrarse.
    email: str
    identificador: str


class ResidentActivationRequest(BaseModel):
    nombre_condominio: str = Field(min_length=1, max_length=200)
    numero_de_casa: int = Field(ge=1)
    nombre_completo: str = Field(min_length=1, max_length=200)
    rol: RolOcupacion  # propietario | inquilino
    telefono: str = Field(min_length=1, max_length=30)
    password: str = Field(min_length=8)
