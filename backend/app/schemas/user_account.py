import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import Rol


class UserAccountCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    rol: Rol
    property_id: uuid.UUID | None = None


class UserAccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    rol: Rol
    property_id: uuid.UUID | None


class UserAccountUpdate(BaseModel):
    """Todos los campos son opcionales: solo cambia lo que se manda. property_id: null explícito la quita."""

    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8)
    rol: Rol | None = None
    property_id: uuid.UUID | None = None
