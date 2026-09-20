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
from app.models.payment_agreement import PaymentAgreement
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
        return await reconcile_payment_ya_con_candado(db, payment)


async def reconcile_payment_ya_con_candado(db: AsyncSession, payment: Payment) -> list[FeeCharge]:
    """
    Cuerpo real de la conciliación, SIN adquirir _locks_por_propiedad — para
    deposit_processing_service.process_incoming_deposit(), que necesita
    tener el candado tomado desde ANTES de insertar el propio Payment, no
    solo durante la conciliación.

    F1-37 (QA de carga): con dos depósitos concurrentes para la MISMA
    vivienda, la versión anterior (INSERT del Payment fuera del candado,
    reconcile_payment() adquiriéndolo después) producía un interbloqueo
    real contra Postgres, reproducible con qa_carga_financiera.py: el
    INSERT en `payment` toma un lock implícito (FOR KEY SHARE) sobre la
    fila de `property` referenciada por la llave foránea, ANTES de que esa
    petición intente tomar el candado en memoria. Si la OTRA petición
    concurrente ya tiene el candado y está esperando su propio
    with_for_update() sobre esa misma fila, quedan esperándose una a la
    otra para siempre: Python nunca ve el ciclo (la mitad de la espera es
    un asyncio.Lock, invisible para el detector de interbloqueos de
    Postgres) así que nadie lo rompe solo. La corrección real es que el
    INSERT del Payment y la conciliación pasen a ser una sola sección
    crítica bajo el mismo candado — ver process_incoming_deposit().
    """
    advertir_si_with_for_update_es_no_op(db, "payment_reconciliation_service.reconcile_payment")
    # Bloquea la fila de Property antes de leer/decidir nada: sin esto,
    # dos conciliaciones concurrentes para la misma vivienda pueden leer
    # el mismo saldo_a_favor de partida y pisarse una a la otra al
    # escribir (ver revisión de F2-20/F3 arriba).
    propiedad = (
        await db.execute(select(Property).where(Property.id == payment.property_id).with_for_update())
    ).scalar_one()

    result = await db.execute(
        select(FeeCharge)
        .where(
            FeeCharge.property_id == payment.property_id,
            FeeCharge.estado.in_([EstadoCargo.pendiente, EstadoCargo.vencido]),
            FeeCharge.payment_id.is_(None),
        )
        .order_by(FeeCharge.periodo.asc())
    )
    candidatos = list(result.scalars().all())

    # Con un acuerdo de pago vigente, primero se pagan las cuotas CORRIENTES (las que no cubre el acuerdo) y
    # al final lo acordado: así pagar la cuota del mes no se va a la deuda vieja y deja al vecino en mora por
    # la cuota nueva. (Python ordena estable: dentro de cada grupo se conserva el orden por periodo.)
    acuerdos = (
        await db.execute(
            select(PaymentAgreement).where(
                PaymentAgreement.property_id == payment.property_id, PaymentAgreement.estado == "vigente"
            )
        )
    ).scalars().all()
    cubiertos = {cargo for a in acuerdos for cargo in (a.cargos_cubiertos or [])}
    if cubiertos:
        candidatos.sort(key=lambda c: str(c.id) in cubiertos)

    # Con un acuerdo de pago vigente (pagos en parcialidades), el saldo a favor que ya tenía la vivienda se
    # junta con este pago para saldar la deuda: si no, un abono menor al cargo más viejo se iba a saldo a
    # favor y NUNCA se sumaba al siguiente abono, y las parcialidades no saldarían nada. Fuera de un acuerdo
    # se conserva el comportamiento de siempre (un depósito solo salda lo que él solo alcanza a cubrir; ver
    # test_deposit_must_cover_recargo_to_settle_overdue_charge): cambiarlo para todos es decisión de producto.
    saldo_previo = float(propiedad.saldo_a_favor)
    usar_saldo = bool(cubiertos) and bool(candidatos) and saldo_previo > TOLERANCIA_CENTAVOS
    restante = float(payment.monto) + (saldo_previo if usar_saldo else 0.0)
    if usar_saldo:
        propiedad.saldo_a_favor = 0  # pasó al fondo de este pago; lo que sobre vuelve a saldo más abajo
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
        propiedad.saldo_a_favor = float(propiedad.saldo_a_favor) + restante

    if conciliados or restante > TOLERANCIA_CENTAVOS:
        await db.flush()
    return conciliados
