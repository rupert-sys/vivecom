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
from app.services.payment_reconciliation_service import _locks_por_propiedad, reconcile_payment_ya_con_candado


class TenantNoEncontrado(Exception):
    pass


async def process_incoming_deposit(deposito: DepositoRecibido, control_db: AsyncSession) -> Payment:
    # .limit(1): clabe_destino ahora es unique=True (F1-29) y /signup y
    # PATCH /tenant/clabe validan duplicados antes de escribir, pero ese
    # índice no se aplicó retroactivamente a una base ya existente con
    # duplicados — sin el límite, un webhook público (sin autenticación)
    # revienta con 500 para CUALQUIER tenant que ya tuviera un duplicado
    # de antes de este fix, en vez de simplemente conciliar (aunque sea de
    # forma ambigua) contra uno de ellos.
    tenant = (
        await control_db.execute(select(Tenant).where(Tenant.clabe_destino == deposito.cuenta_beneficiaria).limit(1))
    ).scalar_one_or_none()
    # F1-37 (QA de carga): control_db es una dependencia de FastAPI inyectada
    # por todo lo que dure el request — sin este close(), su conexión del
    # pool compartido se queda reservada durante TODA la reconciliación de
    # abajo (que puede incluir varias consultas y un with_for_update), aunque
    # ya no se vuelva a usar. Bajo ~100 depósitos concurrentes esto duplicaba
    # la presión sobre el pool (2 conexiones por request en vez de 1) y lo
    # agotaba con QueuePool TimeoutError real, encontrado con
    # qa_carga_financiera.py. Cerrarla aquí la libera de inmediato; que
    # control_session() la vuelva a cerrar al terminar el request es un
    # no-op seguro sobre una sesión ya cerrada.
    await control_db.close()
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

        # F1-37 (QA de carga): el INSERT de abajo toma un lock implícito (FOR
        # KEY SHARE) sobre la fila de `property` referenciada por la llave
        # foránea — si eso pasa FUERA del candado en memoria por vivienda,
        # dos depósitos concurrentes para la MISMA vivienda pueden
        # interbloquearse contra Postgres de verdad (uno esperando el
        # candado que el otro ya tiene, el otro esperando el with_for_update()
        # que el primero bloquea con su INSERT sin comitear). Reproducido con
        # qa_carga_financiera.py. La corrección: el INSERT y la conciliación
        # son una sola sección crítica bajo el mismo candado — ver el
        # docstring de reconcile_payment_ya_con_candado().
        if propiedad is not None:
            async with _locks_por_propiedad[propiedad.id]:
                db.add(payment)
                await db.flush()  # asigna payment.id (default de Python) para poder enlazarlo a un FeeCharge
                # Conciliación automática (F1-07): si el pago quedó
                # confirmado, se aplica contra los cargos pendientes/vencidos
                # de esa vivienda antes del commit final, en la misma transacción.
                await reconcile_payment_ya_con_candado(db, payment)
        else:
            db.add(payment)
            await db.flush()

        await db.commit()
        return payment
