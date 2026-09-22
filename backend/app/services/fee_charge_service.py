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

from app.models.fee import Fee, Periodicidad
from app.models.fee_charge import EstadoCargo, FeeCharge
from app.models.property import Property
from app.services.payment_reconciliation_service import TOLERANCIA_CENTAVOS
from app.services.reglamento_service import (
    acuerdos_vigentes, cargos_con_recargo_congelado, get_reglamento, meses_con_recargo,
)

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
    """La configuración de cuota RECURRENTE vigente para ese periodo: la más reciente (mensual o bimestral) con
    activa_desde <= periodo. Un pago único nunca se cuenta aquí (ver Periodicidad.unica): si se contara, en
    cuanto pasara su fecha reemplazaría en silencio a la cuota mensual real para todos los periodos siguientes."""
    result = await db.execute(
        select(Fee)
        .where(Fee.activa_desde <= periodo, Fee.periodicidad != Periodicidad.unica)
        .order_by(Fee.activa_desde.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_unique_fees_for_period(db: AsyncSession, periodo: date) -> list[Fee]:
    """Cuotas de pago único (extraordinarias, de proyecto) que aplican EXACTAMENTE a este periodo."""
    result = await db.execute(
        select(Fee).where(Fee.periodicidad == Periodicidad.unica, Fee.activa_desde == periodo)
    )
    return list(result.scalars().all())


def fee_applies_to_period(fee: Fee, periodo: date) -> bool:
    """
    Mensual: aplica todos los meses. Bimestral: aplica cada 2 meses contados desde activa_desde (para no generar
    cargo en el mes intermedio). Semanal: se genera con la misma cadencia que mensual (ver Periodicidad.semanal:
    facturar de verdad cada semana no está implementado todavía).
    """
    if fee.periodicidad.value in ("mensual", "semanal"):
        return True
    return _meses_desde(fee.activa_desde, periodo) % 2 == 0


async def generate_charges_for_period(db: AsyncSession, periodo: date) -> list[FeeCharge]:
    """
    Genera (de forma idempotente) un FeeCharge por vivienda para el periodo dado, por cada cuota que le aplique:
    la recurrente vigente (mensual/bimestral) y cualquier cuota de pago único (extraordinaria, de proyecto) cuyo
    periodo sea este mismo — pueden coexistir, así que la idempotencia se controla por (vivienda, cuota), no solo
    por vivienda: una vivienda puede tener más de un cargo el mismo periodo si hay más de una cuota vigente.
    """
    async with _locks_por_periodo[periodo]:
        recurrente = await get_active_fee(db, periodo)
        fees_a_generar = [f for f in [recurrente] if f is not None and fee_applies_to_period(f, periodo)]
        fees_a_generar += await get_unique_fees_for_period(db, periodo)
        if not fees_a_generar:
            return []

        properties_result = await db.execute(select(Property))
        properties = properties_result.scalars().all()

        existing_result = await db.execute(
            select(FeeCharge.property_id, FeeCharge.fee_id).where(FeeCharge.periodo == periodo)
        )
        ya_tienen_cargo = set(existing_result.all())

        nuevos_cargos = []
        for fee in fees_a_generar:
            for prop in properties:
                if (prop.id, fee.id) in ya_tienen_cargo:
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
                ya_tienen_cargo.add((prop.id, fee.id))

        if nuevos_cargos:
            await db.commit()
            # Sin refresh(): ver nota en core/database.py sobre el search_path transaccional.
        return nuevos_cargos


async def apply_late_surcharges(db: AsyncSession, hoy: date) -> list[FeeCharge]:
    """
    Recorre los FeeCharge sin pagar y les aplica el recargo por mora según el
    reglamento del condominio (ver models/reglamento.py): a partir del día
    siguiente al límite de pago de cada mes ("unico": una sola vez, la regla
    global histórica) o, si el reglamento lo pide, de nuevo cada mes que la
    cuota sigue sin pagarse ("mensual_sobre_saldo": Condominio Arequipa,
    Art. 9 I — 5% mensual sobre saldos insolutos).

    El monto se recalcula de forma absoluta (porcentaje × monto_base × meses
    en mora), no incremental, así que correr el job varias veces el mismo día
    es idempotente y un cargo que ya traía su recargo no se vuelve a tocar.
    Nunca se reduce un recargo ya aplicado. Regresa solo los cargos que
    cambiaron en esta corrida.
    """
    reglamento = await get_reglamento(db)
    # Los cargos de un acuerdo de pago vigente con recargo congelado no se tocan mientras se cumple; si el
    # acuerdo se incumple o se cancela, dejan de estar en este conjunto y el recálculo absoluto los alcanza.
    congelados = cargos_con_recargo_congelado(await acuerdos_vigentes(db))
    result = await db.execute(
        select(FeeCharge).where(
            FeeCharge.estado.in_([EstadoCargo.pendiente, EstadoCargo.vencido]), FeeCharge.payment_id.is_(None)
        )
    )

    afectados = []
    hubo_cambios = False
    for charge in result.scalars().all():
        if str(charge.id) in congelados:
            continue
        meses = meses_con_recargo(charge.periodo, hoy, reglamento.dia_recargo)
        if meses == 0:
            continue
        if reglamento.recargo_modalidad == "unico":
            meses = 1
        esperado = round(float(charge.monto_base) * reglamento.recargo_porcentaje * meses, 2)
        if esperado > float(charge.recargo_aplicado) + TOLERANCIA_CENTAVOS:
            charge.recargo_aplicado = esperado
            charge.estado = EstadoCargo.vencido
            afectados.append(charge)
            hubo_cambios = True
        elif charge.estado == EstadoCargo.pendiente:
            # Recargo ya aplicado antes (o porcentaje 0%): el cargo sigue en
            # mora, solo falta reflejar su estado. No cuenta como "afectado".
            charge.estado = EstadoCargo.vencido
            hubo_cambios = True

    if hubo_cambios:
        await db.commit()
    return afectados
