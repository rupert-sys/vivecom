import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_tenant_db, require_roles
from app.models.payment import EstadoPago, Payment
from app.models.property import Property
from app.models.tenant import Tenant
from app.models.user import Rol
from app.schemas.payment import ManualPaymentCreate, PaymentRead, PaymentResolveRequest
from app.services.payment_reconciliation_service import (
    _locks_por_propiedad, reconcile_payment, reconcile_payment_ya_con_candado,
)
from app.services.reglamento_service import get_reglamento
from app.services.receipt_service import build_receipt_pdf

router = APIRouter(prefix="/payments", tags=["payments"])

tesorero_only = [Depends(require_roles(Rol.tesorero, Rol.admin))]


@router.get("", response_model=list[PaymentRead], dependencies=tesorero_only)
async def list_payments(estado: EstadoPago | None = None, db: AsyncSession = Depends(get_tenant_db)):
    """HU-A06: lista de pagos recientes con su estado, para que el tesorero
    identifique cuáles necesitan resolución manual (estado=pendiente)."""
    query = select(Payment).order_by(Payment.fecha_deteccion.desc())
    if estado is not None:
        query = query.where(Payment.estado == estado)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/manual", response_model=PaymentRead, status_code=status.HTTP_201_CREATED, dependencies=tesorero_only)
async def register_manual_payment(
    payload: ManualPaymentCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """
    Pago capturado a mano por el tesorero. El alcance original decía "no hay
    pago en efectivo", pero el reglamento del Condominio Arequipa (Art. 9 IV)
    lo acepta: "el pago en efectivo se recibirá en días y horarios a notificar
    por parte de la tesorería" — y obliga a entregar recibo (Art. 7 VI). Solo
    se permite si el condominio lo activó (ReglamentoConfig.acepta_pago_efectivo).

    Sigue el mismo camino que un depósito detectado: queda confirmado, se
    concilia contra los cargos más antiguos (y el sobrante es saldo a favor) y
    genera recibo descargable. Igual que en deposit_processing_service, el
    INSERT y la conciliación son una sola sección crítica bajo el candado de
    la vivienda (ver F1-37).
    """
    reglamento = await get_reglamento(db)
    if payload.metodo == "efectivo" and not reglamento.acepta_pago_efectivo:
        raise HTTPException(status.HTTP_409_CONFLICT, "Este condominio no tiene activado el pago en efectivo")

    propiedad = await db.get(Property, payload.property_id)
    if propiedad is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vivienda no encontrada")

    payment = Payment(
        property_id=propiedad.id,
        monto=payload.monto,
        estado=EstadoPago.confirmado,
        referencia_recibida=propiedad.referencia_pago,
        clave_rastreo=f"MANUAL-{uuid.uuid4().hex}",
        proveedor=payload.metodo,
        fecha_deteccion=datetime.now(timezone.utc).replace(tzinfo=None),
        registrado_por=uuid.UUID(current_user.user_id),
    )
    async with _locks_por_propiedad[propiedad.id]:
        db.add(payment)
        await db.flush()
        await reconcile_payment_ya_con_candado(db, payment)
    await db.commit()
    return payment


@router.post("/{payment_id}/resolve", response_model=PaymentRead, dependencies=tesorero_only)
async def resolve_payment(
    payment_id: uuid.UUID, payload: PaymentResolveRequest, db: AsyncSession = Depends(get_tenant_db)
):
    """
    Caso especial de HU-A06: un depósito llegó con una referencia numérica
    que no coincidió con ninguna vivienda (ej. el residente la capturó mal).
    El tesorero, que sí sabe de quién es, lo asigna a mano. A partir de ahí
    sigue el mismo camino que un pago emparejado automáticamente: se
    concilia contra los cargos pendientes/vencidos de esa vivienda (F1-07) y
    cualquier sobrante se acredita como saldo a favor (F1-09).
    """
    payment = await db.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pago no encontrado")
    if payment.estado != EstadoPago.pendiente:
        raise HTTPException(status.HTTP_409_CONFLICT, "Solo se pueden resolver pagos en estado pendiente")

    propiedad = await db.get(Property, payload.property_id)
    if propiedad is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vivienda no encontrada")

    payment.property_id = propiedad.id
    payment.estado = EstadoPago.confirmado
    await reconcile_payment(db, payment)
    await db.commit()
    return payment


@router.post("/{payment_id}/reject", response_model=PaymentRead, dependencies=tesorero_only)
async def reject_payment(payment_id: uuid.UUID, db: AsyncSession = Depends(get_tenant_db)):
    """
    Caso especial de HU-A06: el depósito detectado no corresponde a ninguna
    vivienda del condominio (ej. transferencia de un tercero ajeno, monto
    incorrecto). Se marca como rechazado para que quede fuera de la lista de
    pendientes; el residente afectado debe repetir la transferencia.
    Solo aplica a pagos pendientes: uno ya confirmado ya se concilió contra
    cargos reales y deshacer eso no es parte de este alcance.
    """
    payment = await db.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pago no encontrado")
    if payment.estado != EstadoPago.pendiente:
        raise HTTPException(status.HTTP_409_CONFLICT, "Solo se pueden rechazar pagos en estado pendiente")

    payment.estado = EstadoPago.rechazado
    await db.commit()
    return payment


@router.get("/{payment_id}/receipt")
async def download_receipt(
    payment_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """
    F1-11 / HU-A08: recibo simple (NO fiscal), descargable por el residente
    dueño de la vivienda o por admin/tesorero. Se genera al vuelo — no hay
    nada que timbrar ni un archivo que persistir.
    """
    payment = await db.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pago no encontrado")
    if payment.estado != EstadoPago.confirmado:
        raise HTTPException(status.HTTP_409_CONFLICT, "Solo hay recibo para pagos confirmados")

    es_staff = current_user.rol in {Rol.admin.value, Rol.tesorero.value}
    if not es_staff and current_user.property_id != str(payment.property_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes acceso a este recibo")

    propiedad = await db.get(Property, payment.property_id)
    tenant = await db.get(Tenant, uuid.UUID(current_user.tenant_id))

    pdf_bytes = build_receipt_pdf(payment, propiedad, tenant)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="recibo-{payment.id}.pdf"'},
    )
