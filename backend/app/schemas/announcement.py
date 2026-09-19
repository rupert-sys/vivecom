import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class AnnouncementCreate(BaseModel):
    titulo: str
    contenido: str
    fecha_publicacion: datetime | None = None  # None = publicar de inmediato
    # None = lo que diga el reglamento del condominio (dudas_en_avisos_por_defecto).
    permite_dudas: bool | None = None
    dudas_hasta: date | None = None  # última fecha para mandar dudas; None = sin límite


class AnnouncementUpdate(BaseModel):
    titulo: str | None = None
    contenido: str | None = None
    fecha_publicacion: datetime | None = None
    permite_dudas: bool | None = None
    dudas_hasta: date | None = None


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
    permite_dudas: bool = False
    dudas_hasta: date | None = None
    # ¿Se pueden mandar dudas ahora? (activadas y dentro del plazo) — la app lo usa para mostrar el botón.
    dudas_abiertas: bool = False


class ReadStatusEntry(BaseModel):
    property_id: uuid.UUID
    identificador: str
    leido: bool
    leido_at: datetime | None
