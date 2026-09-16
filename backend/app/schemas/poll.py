import uuid
from datetime import date

from pydantic import BaseModel, Field


class PollCreate(BaseModel):
    pregunta: str
    opciones: list[str] = Field(min_length=2)
    fecha_cierre: date
    resultados_en_vivo: bool = False


class PollOptionRead(BaseModel):
    id: uuid.UUID
    texto: str


class PollRead(BaseModel):
    id: uuid.UUID
    pregunta: str
    fecha_cierre: date
    resultados_en_vivo: bool
    quorum_alcanzado: bool
    reactivada: bool
    opciones: list[PollOptionRead]


class VoteCreate(BaseModel):
    option_id: uuid.UUID


class PollResultOption(BaseModel):
    option_id: uuid.UUID
    texto: str
    votos: int


class PollResults(BaseModel):
    poll_id: uuid.UUID
    total_votos: int
    resultados: list[PollResultOption]
