"""
F1-21: dashboard financiero (cobrado vs. pendiente, filtrable por vivienda y
periodo). No existía ningún endpoint que agregara FeeCharge entre viviendas
— GET /properties/{id}/statement (F1-14) es por-vivienda; componer el
dashboard desde el frontend llamando ese endpoint una vez por vivienda sería
N+1 y duplicaría la regla de bucketing pagado=cobrado /
pendiente+vencido=pendiente que ya vive en statement_service. Este servicio
la agrega con una sola consulta agrupada por vivienda.

También agrega por_origen (Mantenimiento/Amenidades/Proyecto), pedido para
el dashboard: Mantenimiento y Proyecto salen de FeeCharge (join a Fee para
distinguir periodicidad "unica" de las recurrentes); Amenidades sale de
Reservation.cuota, que es un cobro aparte — la cuota de uso de un área común
se entrega a tesorería al solicitarla (Reglamento Art. 2 VI) y nunca pasa
por FeeCharge/Payment.
"""

import uuid
from datetime import date

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fee import Fee, Periodicidad
from app.models.fee_charge import EstadoCargo, FeeCharge
from app.models.property import Property
from app.models.reservation import EstadoReserva, Reservation
from app.schemas.reports import CollectionsSummary, OrigenCollectionsSummary, PropertyCollectionsSummary


async def get_collections_summary(
    db: AsyncSession, periodo: date | None, property_id: uuid.UUID | None
) -> CollectionsSummary:
    monto_total = FeeCharge.monto_base + FeeCharge.recargo_aplicado
    query = (
        select(
            FeeCharge.property_id,
            Property.identificador,
            func.sum(case((FeeCharge.estado == EstadoCargo.pagado, monto_total), else_=0)).label("cobrado"),
            func.sum(case((FeeCharge.estado != EstadoCargo.pagado, monto_total), else_=0)).label("pendiente"),
        )
        .join(Property, Property.id == FeeCharge.property_id)
        .group_by(FeeCharge.property_id, Property.identificador)
        .order_by(Property.identificador)
    )
    if periodo is not None:
        query = query.where(FeeCharge.periodo == periodo)
    if property_id is not None:
        query = query.where(FeeCharge.property_id == property_id)

    filas = (await db.execute(query)).all()
    por_vivienda = [
        PropertyCollectionsSummary(
            property_id=fila.property_id,
            identificador=fila.identificador,
            cobrado=float(fila.cobrado or 0),
            pendiente=float(fila.pendiente or 0),
        )
        for fila in filas
    ]

    por_origen = await _por_origen(db, periodo, property_id, monto_total)

    return CollectionsSummary(
        periodo=periodo,
        cobrado_total=sum(p.cobrado for p in por_vivienda),
        pendiente_total=sum(p.pendiente for p in por_vivienda),
        por_vivienda=por_vivienda,
        por_origen=por_origen,
    )


async def _por_origen(
    db: AsyncSession, periodo: date | None, property_id: uuid.UUID | None, monto_total
) -> list[OrigenCollectionsSummary]:
    cargos_query = (
        select(
            Fee.periodicidad,
            func.sum(case((FeeCharge.estado == EstadoCargo.pagado, monto_total), else_=0)).label("cobrado"),
            func.sum(case((FeeCharge.estado != EstadoCargo.pagado, monto_total), else_=0)).label("pendiente"),
        )
        .join(Fee, Fee.id == FeeCharge.fee_id)
        .group_by(Fee.periodicidad)
    )
    if periodo is not None:
        cargos_query = cargos_query.where(FeeCharge.periodo == periodo)
    if property_id is not None:
        cargos_query = cargos_query.where(FeeCharge.property_id == property_id)
    cargos_por_periodicidad = {fila.periodicidad: fila for fila in (await db.execute(cargos_query)).all()}

    mantenimiento_cobrado = 0.0
    mantenimiento_pendiente = 0.0
    proyecto_cobrado = 0.0
    proyecto_pendiente = 0.0
    for periodicidad, fila in cargos_por_periodicidad.items():
        if periodicidad == Periodicidad.unica:
            proyecto_cobrado += float(fila.cobrado or 0)
            proyecto_pendiente += float(fila.pendiente or 0)
        else:
            mantenimiento_cobrado += float(fila.cobrado or 0)
            mantenimiento_pendiente += float(fila.pendiente or 0)

    # Se debe desde que se solicita (pendiente/aprobada); rechazada/expirada nunca generan un cobro pendiente real.
    amenidades_query = select(
        func.sum(case((Reservation.cuota_pagada.is_(True), Reservation.cuota), else_=0)).label("cobrado"),
        func.sum(
            case(
                (
                    Reservation.cuota_pagada.is_(False) & Reservation.estado.in_([EstadoReserva.pendiente, EstadoReserva.aprobada]),
                    Reservation.cuota,
                ),
                else_=0,
            )
        ).label("pendiente"),
    )
    if periodo is not None:
        fin_mes = date(periodo.year + (periodo.month == 12), periodo.month % 12 + 1, 1)
        amenidades_query = amenidades_query.where(Reservation.fecha_inicio >= periodo, Reservation.fecha_inicio < fin_mes)
    if property_id is not None:
        amenidades_query = amenidades_query.where(Reservation.property_id == property_id)
    fila_amenidades = (await db.execute(amenidades_query)).one()

    return [
        OrigenCollectionsSummary(concepto="Mantenimiento", cobrado=mantenimiento_cobrado, pendiente=mantenimiento_pendiente),
        OrigenCollectionsSummary(
            concepto="Amenidades", cobrado=float(fila_amenidades.cobrado or 0), pendiente=float(fila_amenidades.pendiente or 0)
        ),
        OrigenCollectionsSummary(concepto="Proyecto", cobrado=proyecto_cobrado, pendiente=proyecto_pendiente),
    ]
