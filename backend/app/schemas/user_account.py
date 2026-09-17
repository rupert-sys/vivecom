import uuid

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.user import Rol


class UserAccountCreate(BaseModel):
    email: EmailStr
    password: str
    rol: Rol


class UserAccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    rol: Rol
