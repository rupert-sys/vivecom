import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.access_log import TipoAcceso

# Reglamento Art. 17 V.3: el acceso requiere autorización previa del condómino,
# o llamarle por teléfono si la visita es inesperada.
AutorizadoPor = Literal["residente_previo", "telefono", "otro"]


class AccessLogCreate(BaseModel):
    property_id: uuid.UUID | None = None  # None: proveedor sin vivienda asociada
    tipo: TipoAcceso
    placas: list[str] = []  # F2-03: vehículos asociados a este acceso
    # F2-07: UUID generado por la app caseta — ver client_id en el modelo.
    client_id: uuid.UUID | None = None
    # Reglamento Art. 17 V.1: bitácora con nombre, acompañantes e identificación.
    nombre_visitante: str | None = None
    acompanantes: int = Field(default=0, ge=0)
    identificacion: str | None = None
    autorizado_por: AutorizadoPor | None = None


class AccessLogRead(BaseModel):
    id: uuid.UUID
    property_id: uuid.UUID | None
    tipo: TipoAcceso
    hora_entrada: datetime
    hora_salida: datetime | None
    placas: list[str] = []
    nombre_visitante: str | None = None
    acompanantes: int = 0
    identificacion: str | None = None
    autorizado_por: str | None = None


class EstacionamientoVisitas(BaseModel):
    """Ocupación de los cajones de visitas (reglamento Art. 2 IX-XI, Art. 17 V.7)."""

    total_cajones: int
    ocupados: int
    libres: int
    horas_maximas: int
    # Accesos de visitante con vehículo aún adentro por más de `horas_maximas`.
    excedidos: list[uuid.UUID] = []
