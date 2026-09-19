import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.models.incident import EstadoIncidencia


# La caseta levanta incidencias de seguridad (ruido, extraños, daños) y reporta
# fallas de mantenimiento (luminaria, portón). Reportar no es administrar el
# mantenimiento — ver alcance §1.
TipoIncidencia = Literal["seguridad", "mantenimiento", "otro"]


class IncidentCreate(BaseModel):
    descripcion: str
    tipo: TipoIncidencia = "seguridad"
    # Reglamento Art. 17 V.2: número de casa y nombre de la persona involucrada.
    property_id: uuid.UUID | None = None
    persona_involucrada: str | None = None
    foto_url: str | None = None
    # Alternativa a `foto_url`: una foto ya subida (POST /files con kind=incidencia, por el mismo
    # usuario). Si vienen las dos, gana el archivo.
    foto_archivo_id: uuid.UUID | None = None
    # F2-07: UUID generado por la app caseta — ver client_id en el modelo.
    client_id: uuid.UUID | None = None


class IncidentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reportado_por: uuid.UUID
    estado: EstadoIncidencia
    descripcion: str
    foto_url: str | None
    tipo: str = "seguridad"
    property_id: uuid.UUID | None = None
    persona_involucrada: str | None = None
    created_at: datetime
    resolved_at: datetime | None


class IncidentStatusChange(BaseModel):
    estado: EstadoIncidencia


class IncidentCommentCreate(BaseModel):
    comentario: str


class IncidentCommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    incident_id: uuid.UUID
    user_id: uuid.UUID
    comentario: str
    created_at: datetime
