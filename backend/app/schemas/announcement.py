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
    # None para quien no es residente ligado a una vivienda (admin, guardia,
    # etc.) — "leído" no aplica a ellos. Para un residente, refleja si SU
    # vivienda ya confirmó lectura de este aviso (F1-34: la bandeja de
    # avisos de la app residente necesita este dato en el propio listado,
    # no solo en GET /{id}/read-status, que es admin-only y agrega TODAS
    # las viviendas).
    leido: bool | None = None


class ReadStatusEntry(BaseModel):
    property_id: uuid.UUID
    identificador: str
    leido: bool
    leido_at: datetime | None
