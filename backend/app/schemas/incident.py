import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.incident import EstadoIncidencia


class IncidentCreate(BaseModel):
    descripcion: str
    foto_url: str | None = None
    # F2-07: UUID generado por la app caseta — ver client_id en el modelo.
    client_id: uuid.UUID | None = None


class IncidentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reportado_por: uuid.UUID
    estado: EstadoIncidencia
    descripcion: str
    foto_url: str | None
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
