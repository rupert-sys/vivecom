"""
F1-21: dashboard financiero (cobrado vs. pendiente, filtrable por vivienda y
periodo). No existía ningún endpoint que agregara FeeCharge entre viviendas
— GET /properties/{id}/statement (F1-14) es por-vivienda; componer el
dashboard desde el frontend llamando ese endpoint una vez por vivienda sería
N+1 y duplicaría la regla de bucketing pagado=cobrado /
pendiente+vencido=pendiente que ya vive en statement_service. Este servicio
la agrega con una sola consulta agrupada por vivienda.
"""

import uuid
from datetime import date

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fee_charge import EstadoCargo, FeeCharge
from app.models.property import Property
from app.schemas.reports import CollectionsSummary, PropertyCollectionsSummary


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

    return CollectionsSummary(
        periodo=periodo,
        cobrado_total=sum(p.cobrado for p in por_vivienda),
        pendiente_total=sum(p.pendiente for p in por_vivienda),
        por_vivienda=por_vivienda,
    )
