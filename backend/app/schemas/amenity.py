import uuid
from datetime import datetime, time

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

_DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def _validar_dias(valor):
    if valor is None:
        return None
    if isinstance(valor, str):  # así se guarda en la base: "0,1,2,3,4"
        valor = [int(d) for d in valor.split(",") if d.strip() != ""]
    if any(d < 0 or d > 6 for d in valor):
        raise ValueError("Los días van de 0 (lunes) a 6 (domingo)")
    return sorted(set(valor))


class AmenityRules(BaseModel):
    """Reglas de uso de una amenidad — salen del reglamento interior del condominio."""

    dias_anticipacion_minimos: int = Field(default=0, ge=0, le=365)
    hora_inicio_permitida: time | None = None
    hora_fin_maxima: time | None = None
    dias_semana_permitidos: list[int] | None = None  # 0=lunes … 6=domingo; None = todos
    capacidad: int = Field(default=1, ge=1, le=500)
    cuota: float = Field(default=0, ge=0)
    max_duracion_horas: int | None = Field(default=None, ge=1, le=24 * 30)
    notas_reglamento: str | None = None

    _v_dias = field_validator("dias_semana_permitidos", mode="before")(_validar_dias)


class AmenityCreate(AmenityRules):
    nombre: str
    periodo_limite_horas: int


class AmenityUpdate(BaseModel):
    nombre: str | None = None
    periodo_limite_horas: int | None = None
    dias_anticipacion_minimos: int | None = Field(default=None, ge=0, le=365)
    hora_inicio_permitida: time | None = None
    hora_fin_maxima: time | None = None
    dias_semana_permitidos: list[int] | None = None
    capacidad: int | None = Field(default=None, ge=1, le=500)
    cuota: float | None = Field(default=None, ge=0)
    max_duracion_horas: int | None = Field(default=None, ge=1, le=24 * 30)
    notas_reglamento: str | None = None

    _v_dias = field_validator("dias_semana_permitidos", mode="before")(_validar_dias)


class AmenityRead(AmenityRules):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str
    periodo_limite_horas: int

    @computed_field  # type: ignore[prop-decorator]
    @property
    def reglas(self) -> list[str]:
        """Las reglas en lenguaje llano, listas para mostrarse al residente."""
        texto = []
        if self.dias_anticipacion_minimos:
            texto.append(f"Solicítala con al menos {self.dias_anticipacion_minimos} días de anticipación.")
        if self.dias_semana_permitidos is not None and len(self.dias_semana_permitidos) < 7:
            dias = ", ".join(_DIAS[d] for d in self.dias_semana_permitidos)
            texto.append(f"Solo se puede usar: {dias}.")
        if self.hora_inicio_permitida:
            texto.append(f"Horario de inicio: a partir de las {self.hora_inicio_permitida:%H:%M}.")
        if self.hora_fin_maxima:
            texto.append(f"Horario máximo de uso: hasta las {self.hora_fin_maxima:%H:%M}.")
        if self.max_duracion_horas:
            texto.append(f"Duración máxima: {self.max_duracion_horas} horas.")
        if self.capacidad > 1:
            texto.append(f"Capacidad: {self.capacidad} lugares al mismo tiempo.")
        if self.cuota:
            texto.append(f"Cuota de uso: ${self.cuota:,.2f} MXN, se entrega a tesorería al solicitarla.")
        return texto


class AmenityApproverCreate(BaseModel):
    user_id: uuid.UUID


class AmenityBusySlot(BaseModel):
    fecha_inicio: datetime
    fecha_fin: datetime


class AmenityDayAvailability(BaseModel):
    """Ocupación de una amenidad en un día (hora local del condominio)."""

    amenity_id: uuid.UUID
    fecha: str  # AAAA-MM-DD
    capacidad: int
    cupos_libres_todo_el_dia: int  # cuántos lugares siguen libres durante TODO el día
    reservaciones: list[AmenityBusySlot]
    reglas: list[str]
