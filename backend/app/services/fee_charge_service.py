"""
Lógica de generación de FeeCharge. Separada en su propio módulo (no vive
directamente en el job de Celery ni en el endpoint) para poder probarla con
pytest sin necesitar un broker de Celery corriendo, y para reusarla desde
el disparo manual (POST /fees/generate-charges) y desde el job periódico.
"""

import asyncio
from collections import defaultdict
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.business_rules import RECARGO_DIA_DEL_MES, RECARGO_PORCENTAJE
from app.models.fee import Fee
from app.models.fee_charge import EstadoCargo, FeeCharge
from app.models.property import Property
from app.services.payment_reconciliation_service import TOLERANCIA_CENTAVOS

# Revisión (post-F2-20): el chequeo de "ya tiene cargo este periodo" era un
# SELECT seguido de INSERTs condicionales, sin restricción única en
# FeeCharge ni candado — dos disparos concurrentes para el mismo periodo
# (el job de Celery y un disparo manual casi al mismo tiempo, por ejemplo)
# podían ambos pasar la validación antes de que cualquiera comiteara y
# cobrar dos veces la misma vivienda el mismo mes. Se corrige con un candado
# en memoria por periodo — igual que en reservation_service.py, esto NO
# protege entre procesos distintos, solo dentro de uno; la limitación
# adicional aquí es que el candado se comparte entre TODOS los tenants del
# proceso (esta función no recibe el tenant, solo la sesión ya aislada por
# schema), así que dos tenants generando cargos para el mismo mes calendario
# se serializan entre sí innecesariamente — un costo de contención menor,
# aceptable porque esto corre una vez al mes por tenant, a cambio de cerrar
# una carrera financiera real.
_locks_por_periodo: dict[date, asyncio.Lock] = defaultdict(asyncio.Lock)


def _meses_desde(inicio: date, periodo: date) -> int:
    return (periodo.year - inicio.year) * 12 + (periodo.month - inicio.month)


async def get_active_fee(db: AsyncSession, periodo: date) -> Fee | None:
    """La configuración de cuota vigente para ese periodo: la más reciente
    con activa_desde <= periodo."""
    result = await db.execute(
        select(Fee).where(Fee.activa_desde <= periodo).order_by(Fee.activa_desde.desc()).limit(1)
    )
    return result.scalar_one_or_none()


def fee_applies_to_period(fee: Fee, periodo: date) -> bool:
    """
    Mensual: aplica todos los meses. Bimestral: aplica cada 2 meses contados
    desde activa_desde (para no generar cargo en el mes intermedio).
    """
    if fee.periodicidad.value == "mensual":
        return True
    return _meses_desde(fee.activa_desde, periodo) % 2 == 0


async def generate_charges_for_period(db: AsyncSession, periodo: date) -> list[FeeCharge]:
    """
    Genera (de forma idempotente) un FeeCharge por vivienda para el periodo
    dado, usando la configuración de cuota vigente. Si ya existe un cargo
    para una vivienda en ese periodo, no se duplica.
    """
    async with _locks_por_periodo[periodo]:
        fee = await get_active_fee(db, periodo)
        if fee is None or not fee_applies_to_period(fee, periodo):
            return []

        properties_result = await db.execute(select(Property))
        properties = properties_result.scalars().all()

        existing_result = await db.execute(select(FeeCharge.property_id).where(FeeCharge.periodo == periodo))
        ya_tienen_cargo = {row for row in existing_result.scalars().all()}

        nuevos_cargos = []
        for prop in properties:
            if prop.id in ya_tienen_cargo:
                continue
            charge = FeeCharge(property_id=prop.id, fee_id=fee.id, periodo=periodo, monto_base=fee.monto)

            # Saldo a favor (F1-09): si la vivienda tiene crédito suficiente para
            # cubrir este cargo completo, se salda de inmediato con ese crédito
            # en vez de esperar un nuevo depósito.
            saldo = float(prop.saldo_a_favor)
            if saldo + TOLERANCIA_CENTAVOS >= float(fee.monto):
                charge.estado = EstadoCargo.pagado
                prop.saldo_a_favor = saldo - float(fee.monto)

            db.add(charge)
            nuevos_cargos.append(charge)

        if nuevos_cargos:
            await db.commit()
            # Sin refresh(): ver nota en core/database.py sobre el search_path transaccional.
        return nuevos_cargos


def _fecha_limite_sin_recargo(periodo: date) -> date:
    """
    El recargo aplica a partir del minuto 1 del día 6 de CADA MES (regla
    global, no por condominio — alcance sección 3.1). `periodo` es el primer
    día del mes al que corresponde el cargo, así que el límite es el día
    RECARGO_DIA_DEL_MES de ese mismo mes.
    """
    return date(periodo.year, periodo.month, RECARGO_DIA_DEL_MES)


async def apply_late_surcharges(db: AsyncSession, hoy: date) -> list[FeeCharge]:
    """
    Recorre los FeeCharge pendientes y, a quienes ya pasaron su fecha límite
    sin pagar, les aplica el recargo global y los marca como vencidos.
    Idempotente: si un cargo ya tiene recargo aplicado, no se vuelve a tocar
    (evita recalcularlo cada vez que corre el job).
    """
    result = await db.execute(
        select(FeeCharge).where(FeeCharge.estado == EstadoCargo.pendiente, FeeCharge.recargo_aplicado == 0)
    )
    candidatos = result.scalars().all()

    afectados = []
    for charge in candidatos:
        if hoy >= _fecha_limite_sin_recargo(charge.periodo):
            charge.recargo_aplicado = round(float(charge.monto_base) * RECARGO_PORCENTAJE, 2)
            charge.estado = EstadoCargo.vencido
            afectados.append(charge)

    if afectados:
        await db.commit()
    return afectados
