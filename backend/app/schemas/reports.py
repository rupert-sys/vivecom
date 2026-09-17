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
