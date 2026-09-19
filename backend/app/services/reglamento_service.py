"""
Reglas del reglamento interior de un condominio (ver models/reglamento.py) y
las consultas que las hacen cumplir: qué viviendas están en mora, si una
puede votar o usar áreas comunes, cuántos cajones de visitas hay libres.
"""

from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.business_rules import RECARGO_DIA_DEL_MES, RECARGO_PORCENTAJE
from app.models.fee_charge import EstadoCargo, FeeCharge
from app.models.reglamento import ReglamentoConfig

# Los condominios de Vivecom son todos de México (alcance §6): los límites de
# "primeros 5 días del mes", "hasta la 01:00 am", "de lunes a viernes" se
# evalúan en hora local, no en UTC — a las 8pm del día 5 en México ya es día 6
# en UTC.
TZ_CONDOMINIO = ZoneInfo("America/Mexico_City")


def hoy_local() -> date:
    return datetime.now(TZ_CONDOMINIO).date()


@dataclass(frozen=True)
class Reglamento:
    dia_limite_pago: int = RECARGO_DIA_DEL_MES - 1
    recargo_porcentaje: float = RECARGO_PORCENTAJE
    recargo_modalidad: str = "unico"
    acepta_pago_efectivo: bool = False
    morosos_sin_voto: bool = False
    morosos_sin_areas_comunes: bool = False
    gasto_umbral_asamblea: float | None = None
    cotizaciones_minimas: int = 3
    cajones_visitas: int = 0
    horas_max_estacionamiento_visitas: int = 24
    dudas_en_avisos_por_defecto: bool = False

    @property
    def dia_recargo(self) -> int:
        """Primer día del mes en que ya corre el recargo."""
        return self.dia_limite_pago + 1


def reglamento_de_fila(fila: ReglamentoConfig | None) -> Reglamento:
    if fila is None:
        return Reglamento()
    return Reglamento(
        dia_limite_pago=fila.dia_limite_pago,
        recargo_porcentaje=float(fila.recargo_porcentaje),
        recargo_modalidad=fila.recargo_modalidad,
        acepta_pago_efectivo=fila.acepta_pago_efectivo,
        morosos_sin_voto=fila.morosos_sin_voto,
        morosos_sin_areas_comunes=fila.morosos_sin_areas_comunes,
        gasto_umbral_asamblea=float(fila.gasto_umbral_asamblea) if fila.gasto_umbral_asamblea is not None else None,
        cotizaciones_minimas=fila.cotizaciones_minimas,
        cajones_visitas=fila.cajones_visitas,
        horas_max_estacionamiento_visitas=fila.horas_max_estacionamiento_visitas,
        dudas_en_avisos_por_defecto=fila.dudas_en_avisos_por_defecto,
    )


async def get_reglamento(db: AsyncSession) -> Reglamento:
    fila = (await db.execute(select(ReglamentoConfig).where(ReglamentoConfig.id == 1))).scalar_one_or_none()
    return reglamento_de_fila(fila)


def meses_con_recargo(periodo: date, hoy: date, dia_recargo: int) -> int:
    """
    Cuántas veces ya corrió el recargo mensual de un cargo del `periodo`
    (primer día del mes al que corresponde): la primera vez el `dia_recargo`
    de ese mismo mes, y luego cada mes siguiente en el mismo día. 0 si todavía
    está dentro del plazo de pago.
    """
    meses_transcurridos = (hoy.year - periodo.year) * 12 + (hoy.month - periodo.month)
    if meses_transcurridos < 0:
        return 0
    return max(0, meses_transcurridos + (1 if hoy.day >= dia_recargo else 0))


def esta_en_mora(cargo: FeeCharge, hoy: date, dia_recargo: int) -> bool:
    """
    Un cargo sin pagar está en mora en cuanto vence su plazo, no cuando el job
    diario lo marca 'vencido' — así las restricciones (voto, áreas comunes) no
    dependen de que ese job ya haya corrido hoy.
    """
    if cargo.estado == EstadoCargo.pagado or cargo.payment_id is not None:
        return False
    return meses_con_recargo(cargo.periodo, hoy, dia_recargo) >= 1


async def viviendas_morosas(db: AsyncSession, hoy: date, reglamento: Reglamento | None = None) -> set:
    reglamento = reglamento or await get_reglamento(db)
    cargos = (
        await db.execute(
            select(FeeCharge).where(
                FeeCharge.estado.in_([EstadoCargo.pendiente, EstadoCargo.vencido]), FeeCharge.payment_id.is_(None)
            )
        )
    ).scalars().all()
    return {c.property_id for c in cargos if esta_en_mora(c, hoy, reglamento.dia_recargo)}


async def vivienda_en_mora(db: AsyncSession, property_id, hoy: date, reglamento: Reglamento | None = None) -> bool:
    reglamento = reglamento or await get_reglamento(db)
    cargos = (
        await db.execute(
            select(FeeCharge).where(
                FeeCharge.property_id == property_id,
                FeeCharge.estado.in_([EstadoCargo.pendiente, EstadoCargo.vencido]),
                FeeCharge.payment_id.is_(None),
            )
        )
    ).scalars().all()
    return any(esta_en_mora(c, hoy, reglamento.dia_recargo) for c in cargos)
