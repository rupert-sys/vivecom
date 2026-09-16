import uuid

from pydantic import BaseModel, ConfigDict, EmailStr

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
