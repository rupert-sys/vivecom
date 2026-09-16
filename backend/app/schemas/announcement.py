import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AnnouncementCreate(BaseModel):
    titulo: str
    contenido: str
    fecha_publicacion: datetime | None = None  # None = publicar de inmediato


class AnnouncementUpdate(BaseModel):
    titulo: str | None = None
    contenido: str | None = None
    fecha_publicacion: datetime | None = None


class AnnouncementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    titulo: str
    contenido: str
    fecha_publicacion: datetime


class ReadStatusEntry(BaseModel):
    property_id: uuid.UUID
    identificador: str
    leido: bool
    leido_at: datetime | None
