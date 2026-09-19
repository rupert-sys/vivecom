import uuid
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TipoGasto = Literal["operativo", "programado", "extraordinario"]
TipoComprobante = Literal["remision", "factura"]


class Cotizacion(BaseModel):
    proveedor: str = Field(min_length=1)
    monto: float = Field(gt=0)
    url: str | None = None  # foto o PDF de la cotización


class ExpenseCreate(BaseModel):
    categoria: str
    monto: float
    comprobante_url: str = Field(min_length=1)  # obligatorio, ver HU-A09
    fecha: date
    # Reglamento Art. 8: los gastos programados/extraordinarios grandes se
    # aprueban en asamblea y se sustentan con cotizaciones.
    tipo: TipoGasto = "operativo"
    aprobado_en_asamblea: bool = False
    acta_referencia: str | None = None
    cotizaciones: list[Cotizacion] = []
    tipo_comprobante: TipoComprobante | None = None


class ExpenseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    categoria: str
    monto: float
    comprobante_url: str
    fecha: date
    tipo: str = "operativo"
    aprobado_en_asamblea: bool = False
    acta_referencia: str | None = None
    cotizaciones: list[Cotizacion] | None = None
    tipo_comprobante: str | None = None


class TotalPorConcepto(BaseModel):
    concepto: str
    total: float
    cantidad: int


class FinancialSummary(BaseModel):
    """
    Resumen financiero del condominio para un rango de fechas (reglamento
    Art. 7 VI: estado de cuenta cuatrimestral a cada condómino): cuánto entró,
    cuánto se gastó y el saldo — a favor si es positivo, en contra si no.
    """

    desde: date | None
    hasta: date | None
    ingresos: float  # cuotas efectivamente cobradas (pagos confirmados)
    gastos: float
    saldo: float
    por_cobrar: float  # cuotas generadas y aún sin pagar en el rango
    gastos_por_tipo: list[TotalPorConcepto]
    gastos_por_categoria: list[TotalPorConcepto]
