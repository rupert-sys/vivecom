"""
Procesa un depósito ya normalizado (DepositoRecibido): identifica a qué
tenant pertenece por la CLABE beneficiaria, y dentro de ese tenant intenta
emparejar la referencia numérica con una vivienda. Separado del endpoint
del webhook para poder probarlo sin necesitar HTTP de por medio.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import tenant_session
from app.models.payment import EstadoPago, Payment
from app.models.property import Property
from app.models.tenant import Tenant
from app.services.payment_providers.base import DepositoRecibido
from app.services.payment_reconciliation_service import reconcile_payment


class TenantNoEncontrado(Exception):
    pass


async def process_incoming_deposit(deposito: DepositoRecibido, control_db: AsyncSession) -> Payment:
    tenant = (
        await control_db.execute(select(Tenant).where(Tenant.clabe_destino == deposito.cuenta_beneficiaria))
    ).scalar_one_or_none()
    if tenant is None:
        raise TenantNoEncontrado(
            f"Ningún condominio tiene la CLABE {deposito.cuenta_beneficiaria} configurada como destino."
        )

    async with tenant_session(tenant.schema_name) as db:
        # Idempotencia: si STP reintenta el mismo webhook (les pasa seguido a
        # todos los proveedores), no se debe crear un Payment duplicado.
        existente = (
            await db.execute(select(Payment).where(Payment.clave_rastreo == deposito.clave_rastreo))
        ).scalar_one_or_none()
        if existente is not None:
            return existente

        propiedad = (
            await db.execute(select(Property).where(Property.referencia_pago == deposito.referencia_numerica))
        ).scalar_one_or_none()

        payment = Payment(
            property_id=propiedad.id if propiedad else None,
            monto=deposito.monto,
            estado=EstadoPago.confirmado if propiedad else EstadoPago.pendiente,
            referencia_recibida=deposito.referencia_numerica,
            clave_rastreo=deposito.clave_rastreo,
            proveedor="stp",
            fecha_deteccion=deposito.fecha,
        )
        db.add(payment)
        await db.flush()  # asigna payment.id (default de Python) para poder enlazarlo a un FeeCharge

        # Conciliación automática (F1-07): si el pago quedó confirmado, se
        # aplica contra los cargos pendientes/vencidos de esa vivienda antes
        # del commit final, para que quede todo en la misma transacción.
        await reconcile_payment(db, payment)

        await db.commit()
        return payment
