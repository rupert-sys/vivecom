from typing import Literal

from pydantic import BaseModel, Field


class ReglamentoRead(BaseModel):
    dia_limite_pago: int
    dia_recargo: int  # derivado: primer día del mes en que ya corre el recargo
    recargo_porcentaje: float
    recargo_modalidad: Literal["unico", "mensual_sobre_saldo"]
    acepta_pago_efectivo: bool
    morosos_sin_voto: bool
    morosos_sin_areas_comunes: bool
    gasto_umbral_asamblea: float | None
    cotizaciones_minimas: int
    cajones_visitas: int
    horas_max_estacionamiento_visitas: int


class ReglamentoUpdate(BaseModel):
    dia_limite_pago: int | None = Field(default=None, ge=1, le=27)
    recargo_porcentaje: float | None = Field(default=None, ge=0, le=1)
    recargo_modalidad: Literal["unico", "mensual_sobre_saldo"] | None = None
    acepta_pago_efectivo: bool | None = None
    morosos_sin_voto: bool | None = None
    morosos_sin_areas_comunes: bool | None = None
    gasto_umbral_asamblea: float | None = Field(default=None, ge=0)
    cotizaciones_minimas: int | None = Field(default=None, ge=0, le=10)
    cajones_visitas: int | None = Field(default=None, ge=0, le=500)
    horas_max_estacionamiento_visitas: int | None = Field(default=None, ge=1, le=720)
