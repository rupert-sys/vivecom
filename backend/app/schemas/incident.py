import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.incident import EstadoIncidencia


class IncidentCreate(BaseModel):
    descripcion: str


class IncidentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reportado_por: uuid.UUID
    estado: EstadoIncidencia
    descripcion: str
    created_at: datetime


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
