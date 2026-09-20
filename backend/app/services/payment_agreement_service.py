"""
Acuerdos de pago (prórroga de cuotas): reglas de calendario, seguimiento y cumplimiento.

Ver models/payment_agreement.py para el modelo y el porqué. Aquí viven las reglas puras (calendario,
evaluación de cumplimiento) y las consultas que las alimentan, para poder probarlas sin HTTP.
"""

import calendar
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fee_charge import EstadoCargo, FeeCharge
from app.models.payment import EstadoPago, Payment
from app.models.payment_agreement import PaymentAgreement

MAX_PAGOS = 6
TOLERANCIA = 0.01


def sumar_meses(fecha: date, meses: int) -> date:
    """Mismo día del mes k meses después (el último día del mes si ese no existe: 31 → 30/28)."""
    anio, mes = divmod(fecha.year * 12 + fecha.month - 1 + meses, 12)
    return date(anio, mes + 1, min(fecha.day, calendar.monthrange(anio, mes + 1)[1]))


def construir_calendario(deuda: float, numero_de_pagos: int, primer_pago: date) -> list[dict]:
    """Pagos mensuales iguales (al centavo); el último absorbe la diferencia de redondeo."""
    base = int(deuda * 100 // numero_de_pagos) / 100
    pagos = [{"fecha": sumar_meses(primer_pago, k).isoformat(), "monto": base} for k in range(numero_de_pagos)]
    pagos[-1]["monto"] = round(deuda - base * (numero_de_pagos - 1), 2)
    return pagos


def validar_calendario(pagos: list[dict], deuda: float, hoy: date, max_meses: int) -> str | None:
    """Motivo por el que un calendario no es válido, o None si lo es."""
    if not 1 <= len(pagos) <= MAX_PAGOS:
        return f"El acuerdo debe tener de 1 a {MAX_PAGOS} pagos."
    fechas = [date.fromisoformat(p["fecha"]) for p in pagos]
    if fechas != sorted(fechas) or len(set(fechas)) != len(fechas):
        return "Las fechas del calendario deben ir en orden y sin repetirse."
    if fechas[0] <= hoy:
        return "El primer pago debe ser posterior a hoy."
    if fechas[-1] > sumar_meses(hoy, max_meses):
        return f"El acuerdo debe quedar liquidado en un máximo de {max_meses} meses."
    if any(p["monto"] <= 0 for p in pagos):
        return "Cada pago debe ser mayor a cero."
    if abs(sum(p["monto"] for p in pagos) - deuda) > TOLERANCIA:
        return f"Los pagos deben sumar la deuda cubierta (${deuda:,.2f})."
    return None


async def cargos_sin_pagar(db: AsyncSession, property_id: uuid.UUID) -> list[FeeCharge]:
    return list(
        (
            await db.execute(
                select(FeeCharge)
                .where(
                    FeeCharge.property_id == property_id,
                    FeeCharge.estado.in_([EstadoCargo.pendiente, EstadoCargo.vencido]),
                    FeeCharge.payment_id.is_(None),
                )
                .order_by(FeeCharge.periodo)
            )
        ).scalars()
    )


def _total(cargo: FeeCharge) -> float:
    return float(cargo.monto_base) + float(cargo.recargo_aplicado)


async def pendiente_cubierto(db: AsyncSession, acuerdo: PaymentAgreement) -> float:
    """Lo que todavía se debe de los cargos que cubre el acuerdo."""
    ids = [uuid.UUID(c) for c in (acuerdo.cargos_cubiertos or [])]
    if not ids:
        return 0.0
    cargos = (await db.execute(select(FeeCharge).where(FeeCharge.id.in_(ids)))).scalars().all()
    return round(sum(_total(c) for c in cargos if c.estado != EstadoCargo.pagado and c.payment_id is None), 2)


async def pagos_confirmados(db: AsyncSession, property_id: uuid.UUID) -> list[str]:
    """Ids de los pagos confirmados de la vivienda (la línea base con la que se mide lo abonado a un acuerdo)."""
    filas = await db.execute(
        select(Payment.id).where(Payment.property_id == property_id, Payment.estado == EstadoPago.confirmado)
    )
    return [str(pago_id) for pago_id in filas.scalars()]


async def abonado_al_acuerdo(db: AsyncSession, acuerdo: PaymentAgreement) -> float:
    """
    Cuánto ha pagado la vivienda hacia lo acordado desde que se aprobó: todo lo que pagó desde entonces menos
    lo que se fue a cuotas NO cubiertas por el acuerdo (las corrientes, que se pagan primero — ver
    payment_reconciliation_service). Se mide por dinero pagado, no por cargos saldados, porque un cargo se
    salda completo y una parcialidad puede quedarse un rato como saldo a favor. "Desde entonces" son los pagos
    que no estaban ya confirmados al aprobar (`pagos_previos`), no una fecha (ver el modelo).
    """
    previos = set(acuerdo.pagos_previos or [])
    nuevos = {
        pago.id: float(pago.monto)
        for pago in (
            await db.execute(
                select(Payment).where(Payment.property_id == acuerdo.property_id, Payment.estado == EstadoPago.confirmado)
            )
        ).scalars()
        if str(pago.id) not in previos
    }
    if not nuevos:
        return 0.0
    cubiertos = {uuid.UUID(c) for c in (acuerdo.cargos_cubiertos or [])}
    corrientes = (
        await db.execute(
            select(FeeCharge).where(
                FeeCharge.property_id == acuerdo.property_id,
                FeeCharge.estado == EstadoCargo.pagado,
                FeeCharge.payment_id.in_(nuevos),
            )
        )
    ).scalars().all()
    en_corrientes = sum(_total(c) for c in corrientes if c.id not in cubiertos)
    return round(max(0.0, sum(nuevos.values()) - en_corrientes), 2)


def evaluar(calendario: list[dict], abonado: float, pendiente: float, hoy: date) -> str:
    """
    cumplido: no queda nada por pagar de lo cubierto (aunque sea antes de tiempo).
    incumplido: venció (fecha estrictamente pasada) un pago del calendario sin el acumulado que le tocaba; el
    ÚLTIMO pago exige liquidar todo lo cubierto. vigente: cualquier otro caso.
    """
    if pendiente <= TOLERANCIA:
        return "cumplido"
    pagos = sorted(calendario, key=lambda p: p["fecha"])
    acumulado = 0.0
    for indice, pago in enumerate(pagos):
        acumulado += pago["monto"]
        if date.fromisoformat(pago["fecha"]) < hoy:
            if indice == len(pagos) - 1 or abonado + TOLERANCIA < acumulado:
                return "incumplido"
    return "vigente"


def proximo_pago(calendario: list[dict], abonado: float, hoy: date) -> dict | None:
    """El siguiente pago que aún no está cubierto: cuánto falta y para cuándo."""
    acumulado = 0.0
    for pago in sorted(calendario, key=lambda p: p["fecha"]):
        acumulado += pago["monto"]
        if abonado + TOLERANCIA < acumulado:
            return {"fecha": pago["fecha"], "monto": round(acumulado - abonado, 2)}
    return None


async def procesar_acuerdos(db: AsyncSession, hoy: date) -> dict[str, int]:
    """
    El job diario (corre a las 00:00, ANTES del recargo de las 00:01): marca cada acuerdo vigente como
    cumplido o incumplido. Al dejar de estar vigente, sus cargos vuelven a contar como mora y el recargo
    vuelve a correr en la siguiente pasada.
    """
    vigentes = (await db.execute(select(PaymentAgreement).where(PaymentAgreement.estado == "vigente"))).scalars().all()
    resultado = {"cumplidos": 0, "incumplidos": 0}
    for acuerdo in vigentes:
        nuevo = evaluar(
            acuerdo.calendario or [], await abonado_al_acuerdo(db, acuerdo), await pendiente_cubierto(db, acuerdo), hoy
        )
        if nuevo == "vigente":
            continue
        acuerdo.estado = nuevo
        acuerdo.cerrado_en = datetime.now(timezone.utc).replace(tzinfo=None)
        resultado["cumplidos" if nuevo == "cumplido" else "incumplidos"] += 1
    if resultado["cumplidos"] or resultado["incumplidos"]:
        await db.commit()
    return resultado
