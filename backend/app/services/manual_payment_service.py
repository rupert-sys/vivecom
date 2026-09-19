"""
Registro de un pago capturado a mano (efectivo, o una transferencia que el SPEI no
detectó, o un comprobante que tesorería aceptó). Sigue el mismo camino que un
depósito detectado: queda confirmado, se concilia contra los cargos más antiguos
(el sobrante es saldo a favor) y genera recibo. Igual que en
deposit_processing_service, el INSERT y la conciliación son UNA sola sección
crítica bajo el candado de la vivienda (ver F1-37).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import EstadoPago, Payment
from app.models.property import Property
from app.services.payment_reconciliation_service import _locks_por_propiedad, reconcile_payment_ya_con_candado


async def registrar_pago_manual_ya_con_candado(
    db: AsyncSession, propiedad: Property, monto: float, metodo: str, registrado_por: uuid.UUID
) -> Payment:
    """Para quien YA tiene el candado de la vivienda (asyncio.Lock no es reentrante). No hace commit."""
    payment = Payment(
        property_id=propiedad.id,
        monto=monto,
        estado=EstadoPago.confirmado,
        referencia_recibida=propiedad.referencia_pago,
        clave_rastreo=f"MANUAL-{uuid.uuid4().hex}",
        proveedor=metodo,
        fecha_deteccion=datetime.now(timezone.utc).replace(tzinfo=None),
        registrado_por=registrado_por,
    )
    db.add(payment)
    await db.flush()
    await reconcile_payment_ya_con_candado(db, payment)
    return payment


async def registrar_pago_manual(
    db: AsyncSession, propiedad: Property, monto: float, metodo: str, registrado_por: uuid.UUID
) -> Payment:
    async with _locks_por_propiedad[propiedad.id]:
        return await registrar_pago_manual_ya_con_candado(db, propiedad, monto, metodo, registrado_por)
