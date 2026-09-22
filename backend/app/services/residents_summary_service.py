"""
Quién vive en cada vivienda, resumido para una lista (Viviendas en el panel): un nombre y si es propietario o
inquilino, sin acarrear el listado completo de residentes por cada fila. Property/Resident están en N:N (ver
resident.py): una vivienda puede tener varios residentes o ninguno — aquí se elige uno solo para mostrar
(propietario antes que inquilino; a igualdad de rol, por nombre — ResidentProperty no guarda cuándo se ligó,
así que no hay forma de saber cuál fue primero) y se cuentan los demás.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resident import Resident, ResidentProperty, RolOcupacion


async def residentes_principales(
    db: AsyncSession, property_ids: list[uuid.UUID]
) -> dict[uuid.UUID, tuple[str, str, int]]:
    """{property_id: (nombre, rol, total_de_residentes)} — una vivienda sin residentes no aparece en el resultado."""
    if not property_ids:
        return {}

    fila = (
        select(
            ResidentProperty.property_id,
            Resident.nombre,
            ResidentProperty.rol,
            func.row_number()
            .over(
                partition_by=ResidentProperty.property_id,
                # propietario antes que inquilino (False < True ordena primero); a igualdad, por nombre.
                order_by=(ResidentProperty.rol == RolOcupacion.inquilino, Resident.nombre),
            )
            .label("orden"),
        )
        .join(Resident, Resident.id == ResidentProperty.resident_id)
        .where(ResidentProperty.property_id.in_(property_ids))
        .subquery()
    )
    principales = (
        await db.execute(select(fila.c.property_id, fila.c.nombre, fila.c.rol).where(fila.c.orden == 1))
    ).all()

    conteos = dict(
        (
            await db.execute(
                select(ResidentProperty.property_id, func.count())
                .where(ResidentProperty.property_id.in_(property_ids))
                .group_by(ResidentProperty.property_id)
            )
        ).all()
    )

    return {
        property_id: (nombre, rol.value, conteos.get(property_id, 0))
        for property_id, nombre, rol in principales
    }
