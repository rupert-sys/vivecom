import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict

from app.models.budget import PeriodicidadPresupuesto


class BudgetCreate(BaseModel):
    categoria: str
    periodicidad: PeriodicidadPresupuesto
    periodo: date
    monto_planeado: float


class BudgetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    categoria: str
    periodicidad: PeriodicidadPresupuesto
    periodo: date
    monto_planeado: float


class BudgetComparison(BaseModel):
    categoria: str
    periodicidad: PeriodicidadPresupuesto
    monto_planeado: float
    monto_real: float
