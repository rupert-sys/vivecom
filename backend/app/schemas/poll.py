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
    # None para quien no es residente ligado a una vivienda — mismo criterio
    # que AnnouncementRead.leido (F1-34): sin esto, la app residente no
    # tenía forma de saber si SU vivienda ya votó sin intentarlo y toparse
    # con el 409 de "ya_voto".
    ya_voto: bool | None = None
    # Reglamento del condominio (Arequipa Art. 5 III): la vivienda en mora
    # conserva voz pero pierde el voto. None si no aplica (no es residente, o
    # el condominio no tiene esa regla) — la app muestra el motivo en vez de
    # dejar al residente tocar "Votar" y toparse con un error.
    voto_restringido_por_mora: bool | None = None


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
