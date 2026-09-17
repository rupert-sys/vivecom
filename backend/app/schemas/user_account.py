import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import Rol


class UserAccountCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    rol: Rol


class UserAccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    rol: Rol
