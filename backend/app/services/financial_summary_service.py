"""
Resumen financiero del condominio (ingresos, gastos y saldo) y estatus de
cobranza por vivienda (quién pagó, quién falta, quién es moroso). Solo agrega
datos que ya existen — la regla de "moroso" vive en reglamento_service.
"""

from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.expense import Expense
from app.models.fee_charge import EstadoCargo, FeeCharge
from app.models.payment import EstadoPago, Payment
from app.models.property import Property
from app.schemas.expense import FinancialSummary, TotalPorConcepto
from app.schemas.reports import EstatusCobranza, EstatusVivienda
from app.services.reglamento_service import (
    TZ_CONDOMINIO, acuerdos_vigentes, cargos_cubiertos, esta_en_mora, get_reglamento, hoy_local,
)


def _a_utc_ingenuo(dia: date, fin_de_dia: bool = False) -> datetime:
    """Límite de un día LOCAL del condominio expresado como UTC ingenuo (como guarda la base)."""
    local = datetime.combine(dia + timedelta(days=1 if fin_de_dia else 0), time.min, tzinfo=TZ_CONDOMINIO)
    return local.astimezone(timezone.utc).replace(tzinfo=None)


async def get_financial_summary(db: AsyncSession, desde: date | None, hasta: date | None) -> FinancialSummary:
    gastos_q = select(Expense)
    if desde is not None:
        gastos_q = gastos_q.where(Expense.fecha >= desde)
    if hasta is not None:
        gastos_q = gastos_q.where(Expense.fecha <= hasta)
    gastos = (await db.execute(gastos_q)).scalars().all()

    ingresos_q = select(func.coalesce(func.sum(Payment.monto), 0)).where(Payment.estado == EstadoPago.confirmado)
    if desde is not None:
        ingresos_q = ingresos_q.where(Payment.fecha_deteccion >= _a_utc_ingenuo(desde))
    if hasta is not None:
        ingresos_q = ingresos_q.where(Payment.fecha_deteccion < _a_utc_ingenuo(hasta, fin_de_dia=True))
    ingresos = float((await db.execute(ingresos_q)).scalar_one())

    cargos_q = select(FeeCharge).where(FeeCharge.estado != EstadoCargo.pagado)
    if desde is not None:
        cargos_q = cargos_q.where(FeeCharge.periodo >= desde.replace(day=1))
    if hasta is not None:
        cargos_q = cargos_q.where(FeeCharge.periodo <= hasta)
    por_cobrar = sum(float(c.monto_base) + float(c.recargo_aplicado) for c in (await db.execute(cargos_q)).scalars())

    total_gastos = sum(float(g.monto) for g in gastos)
    return FinancialSummary(
        desde=desde,
        hasta=hasta,
        ingresos=round(ingresos, 2),
        gastos=round(total_gastos, 2),
        saldo=round(ingresos - total_gastos, 2),
        por_cobrar=round(por_cobrar, 2),
        gastos_por_tipo=_agrupar(gastos, lambda g: g.tipo or "operativo"),
        gastos_por_categoria=_agrupar(gastos, lambda g: g.categoria),
    )


def _agrupar(gastos, clave) -> list[TotalPorConcepto]:
    acumulado: dict[str, list[float]] = {}
    for gasto in gastos:
        total_y_cantidad = acumulado.setdefault(clave(gasto), [0.0, 0])
        total_y_cantidad[0] += float(gasto.monto)
        total_y_cantidad[1] += 1
    return sorted(
        (TotalPorConcepto(concepto=k, total=round(v[0], 2), cantidad=int(v[1])) for k, v in acumulado.items()),
        key=lambda t: t.total,
        reverse=True,
    )


async def get_collection_status(db: AsyncSession, periodo: date) -> EstatusCobranza:
    """
    Por vivienda: al_corriente / pendiente (debe, pero aún dentro del plazo) /
    moroso (venció el plazo del reglamento). `periodo_pagado` dice si el cargo
    del periodo pedido ya está cubierto.
    """
    hoy = hoy_local()
    reglamento = await get_reglamento(db)
    periodo = periodo.replace(day=1)

    vigentes = await acuerdos_vigentes(db)
    cubiertos = cargos_cubiertos(vigentes)
    con_acuerdo = {a.property_id for a in vigentes}

    viviendas = (await db.execute(select(Property).order_by(Property.identificador))).scalars().all()
    cargos = (await db.execute(select(FeeCharge))).scalars().all()
    por_vivienda: dict = {}
    for cargo in cargos:
        por_vivienda.setdefault(cargo.property_id, []).append(cargo)

    filas: list[EstatusVivienda] = []
    for vivienda in viviendas:
        propios = por_vivienda.get(vivienda.id, [])
        sin_pagar = [c for c in propios if c.estado != EstadoCargo.pagado]
        # Lo que cubre un acuerdo de pago vigente no cuenta como mora mientras se cumpla.
        vencidos = [c for c in sin_pagar if str(c.id) not in cubiertos and esta_en_mora(c, hoy, reglamento.dia_recargo)]
        del_periodo = [c for c in propios if c.periodo == periodo]

        if vencidos:
            estatus = "moroso"
        elif vivienda.id in con_acuerdo:
            estatus = "con_acuerdo"
        elif sin_pagar:
            estatus = "pendiente"
        else:
            estatus = "al_corriente"
        filas.append(
            EstatusVivienda(
                property_id=vivienda.id,
                identificador=vivienda.identificador,
                estatus=estatus,
                adeudo_total=round(sum(float(c.monto_base) + float(c.recargo_aplicado) for c in sin_pagar), 2),
                cargos_vencidos=len(vencidos),
                periodo_pagado=(all(c.estado == EstadoCargo.pagado for c in del_periodo) if del_periodo else None),
            )
        )

    orden = {"moroso": 0, "con_acuerdo": 1, "pendiente": 2, "al_corriente": 3}
    filas.sort(key=lambda f: (orden[f.estatus], f.identificador))
    return EstatusCobranza(
        periodo=periodo,
        total_viviendas=len(filas),
        al_corriente=sum(f.estatus == "al_corriente" for f in filas),
        pendientes=sum(f.estatus == "pendiente" for f in filas),
        morosas=sum(f.estatus == "moroso" for f in filas),
        con_acuerdo=sum(f.estatus == "con_acuerdo" for f in filas),
        adeudo_total=round(sum(f.adeudo_total for f in filas), 2),
        viviendas=filas,
    )
