import uuid

from pydantic import BaseModel, ConfigDict

from app.models.lost_found_item import EstadoObjeto


class LostFoundItemCreate(BaseModel):
    descripcion: str
    foto_url: str | None = None


class LostFoundItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    publicado_por: uuid.UUID
    descripcion: str
    foto_url: str | None
    estado: EstadoObjeto


class LostFoundItemModerate(BaseModel):
    estado: EstadoObjeto
