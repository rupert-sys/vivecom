import uuid
from datetime import date

from pydantic import BaseModel


class PropertyCollectionsSummary(BaseModel):
    property_id: uuid.UUID
    identificador: str
    cobrado: float
    pendiente: float


class CollectionsSummary(BaseModel):
    periodo: date | None
    cobrado_total: float
    pendiente_total: float
    por_vivienda: list[PropertyCollectionsSummary]


class EstatusVivienda(BaseModel):
    property_id: uuid.UUID
    identificador: str
    estatus: str  # al_corriente | pendiente | moroso
    adeudo_total: float
    cargos_vencidos: int
    # None si la vivienda no tiene cargo en el periodo consultado.
    periodo_pagado: bool | None


class EstatusCobranza(BaseModel):
    """Quién ya pagó, quién falta y quién es moroso — para el panel del administrador."""

    periodo: date
    total_viviendas: int
    al_corriente: int
    pendientes: int
    morosas: int
    adeudo_total: float
    viviendas: list[EstatusVivienda]
