import uuid

from pydantic import BaseModel, EmailStr


class StaffLoginRequest(BaseModel):
    email: EmailStr
    password: str


class CurrentStaff(BaseModel):
    staff_id: str


class ExecutiveTenantSummary(BaseModel):
    tenant_id: uuid.UUID
    nombre: str
    viviendas: int
    ingresos_mes_actual: float
    deuda_pendiente: float
    cargos_totales: int
    cargos_vencidos: int
    incidencias_abiertas: int


class ExecutiveTotales(BaseModel):
    total_condominios: int
    total_viviendas: int
    ingresos_mes_actual: float
    deuda_pendiente: float
    tasa_morosidad: float  # cargos_vencidos / cargos_totales de TODOS los tenants, 0.0 si no hay ninguno
    incidencias_abiertas: int


class ExecutiveSummary(BaseModel):
    periodo: str  # "AAAA-MM", el mes cuyo ingreso se está reportando
    tenants: list[ExecutiveTenantSummary]
    totales: ExecutiveTotales
