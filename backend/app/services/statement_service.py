"""
Estado de cuenta por vivienda (F1-14): historial de cargos y pagos, más el
saldo actual (a favor o en contra). Solo agrega datos que ya existen — sin
reglas de negocio propias, por eso no tiene la batería de pruebas de un
servicio como payment_reconciliation_service; se prueba a través del
endpoint en test_account_statement.py.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fee_charge import EstadoCargo, FeeCharge
from app.models.payment import Payment
from app.models.property import Property


@dataclass
class EstadoDeCuenta:
    propiedad: Property
    cargos: list[FeeCharge]
    pagos: list[Payment]
    deuda_total: float


async def get_account_statement(db: AsyncSession, property_id: uuid.UUID) -> EstadoDeCuenta | None:
    propiedad = await db.get(Property, property_id)
    if propiedad is None:
        return None

    cargos = (
        await db.execute(select(FeeCharge).where(FeeCharge.property_id == property_id).order_by(FeeCharge.periodo))
    ).scalars().all()

    pagos = (
        await db.execute(
            select(Payment).where(Payment.property_id == property_id).order_by(Payment.fecha_deteccion.desc())
        )
    ).scalars().all()

    deuda_total = sum(
        (float(cargo.monto_base) + float(cargo.recargo_aplicado))
        for cargo in cargos
        if cargo.estado in (EstadoCargo.pendiente, EstadoCargo.vencido)
    )

    return EstadoDeCuenta(propiedad=propiedad, cargos=cargos, pagos=pagos, deuda_total=deuda_total)
