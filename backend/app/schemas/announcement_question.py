import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class QuestionCreate(BaseModel):
    texto: str = Field(min_length=1, max_length=500)


class QuestionAnswer(BaseModel):
    respuesta: str = Field(min_length=1, max_length=1000)
    # Publicarla como aclaración visible para todos, sin nombre ni vivienda.
    publicar: bool = False


class QuestionUpdate(BaseModel):
    publica: bool | None = None
    respuesta: str | None = Field(default=None, min_length=1, max_length=1000)


class QuestionRead(BaseModel):
    id: uuid.UUID
    announcement_id: uuid.UUID
    aviso_titulo: str | None = None
    texto: str
    estado: str  # abierta | respondida
    respuesta: str | None
    respondido_en: datetime | None
    publica: bool
    created_at: datetime
    # ¿es de MI vivienda? Las aclaraciones ajenas llegan sin vivienda ni datos de quien preguntó.
    propia: bool = False
    # Solo para la administración y el comité: de qué vivienda viene.
    vivienda: str | None = None
    # Para el residente autor: la respuesta llegó y todavía no la ha visto.
    respuesta_nueva: bool = False
