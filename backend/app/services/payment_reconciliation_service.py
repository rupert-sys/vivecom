"""
Conciliación automática (F1-07): una vez que un depósito ya se emparejó con
una vivienda (Payment.estado == confirmado), se aplica ese monto contra los
FeeCharge pendientes/vencidos más antiguos de esa vivienda, del más viejo al
más nuevo, hasta agotar el monto del depósito. Separado de
deposit_processing_service.py para poder probarlo aparte y reusarlo si algún
día se concilia un pago manualmente desde el panel admin.

Si, después de saldar todo lo pendiente/vencido, lo que sobra es un múltiplo
exacto de la cuota mensual vigente (1 a 12 veces), se interpreta como pago
anticipado (F1-08, HU-A05: "como residente quiero pagar de 1 a 12 meses por
adelantado, para evitar recargos futuros") y se crean de una vez los
FeeCharge de esos meses futuros, ya marcados como pagados — así nunca llegan
a existir en estado pendiente el día que correría el recargo. Solo aplica
si la vivienda ya no debe nada (si quedó algo pendiente/vencido sin cubrir,
no tendría sentido "adelantar" meses futuros).

Si sobra dinero que NO es ese múltiplo exacto (un excedente cualquiera), se
guarda como saldo a favor de la vivienda (F1-09, alcance sección "HU-A06":
"si un residente transfiere de más, el excedente queda como saldo a favor
para el siguiente periodo"). Ese saldo se consume automáticamente cuando se
genera el siguiente FeeCharge — ver fee_charge_service.generate_charges_for_period().
"""

import asyncio
import uuid
from collections import defaultdict
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.concurrency import advertir_si_with_for_update_es_no_op
from app.models.fee_charge import EstadoCargo, FeeCharge
from app.models.payment import Payment
from app.models.property import Property

# Revisión (post-F2-20): reconcile_payment hacía un read-modify-write de
# Property.saldo_a_favor y marcaba FeeCharge.pagado sin ningún candado — dos
# depósitos para la misma vivienda conciliados a la vez podían pisarse
# (perder un incremento de saldo, o que dos pagos distintos reclamen el
# mismo cargo). Mismo patrón que reservation_service.py: candado en memoria
# por vivienda (protección real dentro de un proceso) + with_for_update()
# sobre la fila de Property (protección entre procesos en Postgres — con la
# misma limitación conocida: no verificable contra un Postgres real desde
# aquí, ver advertir_si_with_for_update_es_no_op).
_locks_por_propiedad: dict[uuid.UUID, asyncio.Lock] = defaultdict(asyncio.Lock)

# Tolerancia para comparar montos en punto flotante (ej. 1500.00 - 1500.00
# puede no dar exactamente 0.0 por redondeo binario).
TOLERANCIA_CENTAVOS = 0.005

MESES_ANTICIPO_MINIMO = 1
MESES_ANTICIPO_MAXIMO = 12


def _siguiente_mes(periodo: date) -> date:
    if periodo.month == 12:
        return date(periodo.year + 1, 1, 1)
    return date(periodo.year, periodo.month + 1, 1)


async def _aplicar_pago_anticipado(db: AsyncSession, payment: Payment, restante: float) -> tuple[list[FeeCharge], float]:
    """
    F1-08: si `restante` es un múltiplo exacto (1-12x) de la cuota mensual
    vigente, crea ya pagados los FeeCharge de esos próximos meses. Import
    local de get_active_fee (no al inicio del módulo) para no crear un ciclo
    de imports con fee_charge_service, que a su vez importa TOLERANCIA_CENTAVOS
    de este módulo.
    """
    from app.services.fee_charge_service import get_active_fee

    ultimo_periodo = (
        await db.execute(
            select(FeeCharge.periodo)
            .where(FeeCharge.property_id == payment.property_id)
            .order_by(FeeCharge.periodo.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    periodo_inicial = _siguiente_mes(ultimo_periodo) if ultimo_periodo else payment.fecha_deteccion.date().replace(day=1)

    fee = await get_active_fee(db, periodo_inicial)
    if fee is None or fee.periodicidad.value != "mensual" or float(fee.monto) <= 0:
        return [], restante

    n_meses = round(restante / float(fee.monto))
    if not (MESES_ANTICIPO_MINIMO <= n_meses <= MESES_ANTICIPO_MAXIMO):
        return [], restante
    if abs(restante - n_meses * float(fee.monto)) > TOLERANCIA_CENTAVOS:
        return [], restante

    cargos_creados = []
    periodo_actual = periodo_inicial
    for _ in range(n_meses):
        cargo = FeeCharge(
            property_id=payment.property_id,
            fee_id=fee.id,
            periodo=periodo_actual,
            monto_base=fee.monto,
            estado=EstadoCargo.pagado,
            payment_id=payment.id,
        )
        db.add(cargo)
        cargos_creados.append(cargo)
        periodo_actual = _siguiente_mes(periodo_actual)

    return cargos_creados, 0.0


async def reconcile_payment(db: AsyncSession, payment: Payment) -> list[FeeCharge]:
    """
    Idempotente: un FeeCharge que ya tiene payment_id no se vuelve a tocar,
    así que conciliar el mismo Payment dos veces no duplica nada. El
    excedente sí podría re-acreditarse en un reintento del mismo depósito —
    pero deposit_processing_service ya evita esa doble llamada gracias a su
    propia idempotencia por clave_rastreo (nunca vuelve a llamar a
    reconcile_payment() para un Payment que ya existía).
    """
    if payment.property_id is None:
        return []

    async with _locks_por_propiedad[payment.property_id]:
        advertir_si_with_for_update_es_no_op(db, "payment_reconciliation_service.reconcile_payment")
        # Bloquea la fila de Property antes de leer/decidir nada: sin esto,
        # dos conciliaciones concurrentes para la misma vivienda pueden leer
        # el mismo saldo_a_favor de partida y pisarse una a la otra al
        # escribir (ver revisión de F2-20/F3 arriba).
        await db.execute(select(Property).where(Property.id == payment.property_id).with_for_update())

        result = await db.execute(
            select(FeeCharge)
            .where(
                FeeCharge.property_id == payment.property_id,
                FeeCharge.estado.in_([EstadoCargo.pendiente, EstadoCargo.vencido]),
                FeeCharge.payment_id.is_(None),
            )
            .order_by(FeeCharge.periodo.asc())
        )
        candidatos = result.scalars().all()

        restante = float(payment.monto)
        conciliados = []
        for charge in candidatos:
            total_cargo = float(charge.monto_base) + float(charge.recargo_aplicado)
            if restante + TOLERANCIA_CENTAVOS < total_cargo:
                break
            charge.estado = EstadoCargo.pagado
            charge.payment_id = payment.id
            conciliados.append(charge)
            restante -= total_cargo

        # F1-08: solo tiene sentido "adelantar" meses futuros si ya no queda
        # nada pendiente/vencido sin cubrir de esta vivienda.
        if restante > TOLERANCIA_CENTAVOS and len(conciliados) == len(candidatos):
            cargos_anticipados, restante = await _aplicar_pago_anticipado(db, payment, restante)
            conciliados.extend(cargos_anticipados)

        if restante > TOLERANCIA_CENTAVOS:
            propiedad = await db.get(Property, payment.property_id)
            propiedad.saldo_a_favor = float(propiedad.saldo_a_favor) + restante

        if conciliados or restante > TOLERANCIA_CENTAVOS:
            await db.flush()
        return conciliados
