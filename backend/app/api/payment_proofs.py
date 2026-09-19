"""
Comprobantes de pago que el residente adjunta desde su app (captura o PDF del banco). No son un
pago: hasta que tesorería los revisa y acepta no se concilia nada. Al aceptarlos se registra un
pago normal (mismo camino que el efectivo) y el residente puede descargar su recibo.
"""

import uuid
from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_tenant_db, require_roles
from app.core.concurrency import advertir_si_with_for_update_es_no_op
from app.models.payment import EstadoPago, Payment
from app.models.payment_proof import EstadoComprobante, PaymentProof
from app.models.property import Property
from app.models.stored_file import StoredFile
from app.models.user import Rol
from app.schemas.payment_proof import PaymentProofAccept, PaymentProofCreate, PaymentProofRead, PaymentProofReject
from app.services.file_links import firmar_url
from app.services.manual_payment_service import registrar_pago_manual_ya_con_candado
from app.services.payment_reconciliation_service import _locks_por_propiedad

router = APIRouter(prefix="/payment-proofs", tags=["payment-proofs"])

tesorero_only = [Depends(require_roles(Rol.tesorero, Rol.admin))]

MAX_PENDIENTES_POR_VIVIENDA = 20
# Un pago que ya detectó el SPEI llega con unos días de diferencia respecto de la fecha del comprobante.
VENTANA_DUPLICADO_DIAS = 5


def _ahora() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _a_lectura(prueba: PaymentProof, schema_name: str) -> PaymentProofRead:
    return PaymentProofRead(
        id=prueba.id, property_id=prueba.property_id, monto=float(prueba.monto), fecha_pago=prueba.fecha_pago,
        nota=prueba.nota, estado=prueba.estado, created_at=prueba.created_at, revisado_en=prueba.revisado_en,
        motivo_rechazo=prueba.motivo_rechazo, payment_id=prueba.payment_id,
        archivo_url=firmar_url(prueba.archivo_id, schema_name),
    )


@router.post("", response_model=PaymentProofRead, status_code=status.HTTP_201_CREATED)
async def send_payment_proof(
    payload: PaymentProofCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """El residente avisa "ya pagué" con su comprobante del banco; queda pendiente de que tesorería lo revise."""
    if current_user.property_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Esta acción es solo para residentes ligados a una vivienda")
    property_id = uuid.UUID(current_user.property_id)

    archivo = await db.get(StoredFile, payload.archivo_id)
    # Solo se puede adjuntar un archivo propio y subido como comprobante de pago: nadie
    # puede colgar a su comprobante el archivo de otra persona.
    if archivo is None or archivo.kind != "pago" or str(archivo.uploaded_by) != current_user.user_id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "El archivo adjunto no existe o no es tuyo.")
    if payload.fecha_pago is not None and payload.fecha_pago > date.today() + timedelta(days=1):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "La fecha del pago no puede ser futura.")

    pendientes = (
        await db.execute(
            select(func.count()).select_from(PaymentProof).where(
                PaymentProof.property_id == property_id, PaymentProof.estado == EstadoComprobante.pendiente
            )
        )
    ).scalar_one()
    if pendientes >= MAX_PENDIENTES_POR_VIVIENDA:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya tienes muchos comprobantes en revisión; espera a que tesorería los revise.")

    prueba = PaymentProof(
        property_id=property_id, monto=payload.monto, fecha_pago=payload.fecha_pago, nota=payload.nota,
        archivo_id=payload.archivo_id, enviado_por=uuid.UUID(current_user.user_id), created_at=_ahora(),
    )
    db.add(prueba)
    await db.commit()
    return _a_lectura(prueba, current_user.schema_name)


@router.get("", response_model=list[PaymentProofRead])
async def list_payment_proofs(
    estado: EstadoComprobante | None = None,
    property_id: uuid.UUID | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Tesorería ve todos (los pendientes primero); un residente solo los de su vivienda."""
    query = select(PaymentProof).order_by(PaymentProof.created_at.desc())
    if current_user.rol in {Rol.tesorero.value, Rol.admin.value}:
        if property_id is not None:
            query = query.where(PaymentProof.property_id == property_id)
    else:
        if current_user.property_id is None:
            return []
        query = query.where(PaymentProof.property_id == uuid.UUID(current_user.property_id))
    if estado is not None:
        query = query.where(PaymentProof.estado == estado)
    pruebas = (await db.execute(query)).scalars().all()
    pruebas = sorted(pruebas, key=lambda p: p.estado != EstadoComprobante.pendiente)  # estable: pendientes primero
    return [_a_lectura(p, current_user.schema_name) for p in pruebas]


async def _pago_ya_detectado(db: AsyncSession, prueba: PaymentProof, monto: float) -> Payment | None:
    """Un pago del mismo monto que el SPEI ya detectó para esta vivienda por las mismas fechas."""
    centro = prueba.fecha_pago or prueba.created_at.date()
    desde = datetime.combine(centro - timedelta(days=VENTANA_DUPLICADO_DIAS), time.min)
    hasta = datetime.combine(centro + timedelta(days=VENTANA_DUPLICADO_DIAS + 1), time.min)
    return (
        await db.execute(
            select(Payment).where(
                Payment.property_id == prueba.property_id,
                Payment.estado == EstadoPago.confirmado,
                Payment.registrado_por.is_(None),  # detectado automáticamente, no capturado a mano
                Payment.monto == monto,
                Payment.fecha_deteccion >= desde,
                Payment.fecha_deteccion < hasta,
            )
        )
    ).scalars().first()


@router.post("/{proof_id}/accept", response_model=PaymentProofRead, dependencies=tesorero_only)
async def accept_payment_proof(
    proof_id: uuid.UUID,
    payload: PaymentProofAccept,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """
    Tesorería revisó el comprobante y el dinero sí llegó: se registra el pago (transferencia) y se
    concilia contra los cargos más antiguos. Si el SPEI ya detectó un pago igual para esa vivienda
    por esas fechas, es casi seguro el mismo: se rechaza la aceptación (409) salvo que tesorería
    confirme con `forzar` que es otro — así un mismo dinero no se cuenta dos veces.
    """
    prueba = await db.get(PaymentProof, proof_id)
    if prueba is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Comprobante no encontrado")
    propiedad = await db.get(Property, prueba.property_id)

    # Todo dentro del candado de la vivienda: la revisión del estado, el registro del pago y el cambio
    # de estado son una sola sección crítica (dos tesoreros aceptando a la vez no duplican el pago).
    async with _locks_por_propiedad[propiedad.id]:
        advertir_si_with_for_update_es_no_op(db, "payment_proofs.accept_payment_proof")
        prueba = (
            await db.execute(select(PaymentProof).where(PaymentProof.id == proof_id).with_for_update())
        ).scalar_one()
        if prueba.estado != EstadoComprobante.pendiente:
            raise HTTPException(status.HTTP_409_CONFLICT, "Este comprobante ya fue revisado")

        monto = payload.monto if payload.monto is not None else float(prueba.monto)
        if not payload.forzar:
            detectado = await _pago_ya_detectado(db, prueba, monto)
            if detectado is not None:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    f"El SPEI ya detectó un pago de ${monto:,.2f} para esta vivienda el "
                    f"{detectado.fecha_deteccion:%d/%m/%Y}: probablemente es el mismo. Si de verdad es otro, "
                    "acéptalo confirmando que es distinto.",
                )

        pago = await registrar_pago_manual_ya_con_candado(
            db, propiedad, monto, "transferencia", uuid.UUID(current_user.user_id)
        )
        prueba.estado = EstadoComprobante.aceptado
        prueba.revisado_por = uuid.UUID(current_user.user_id)
        prueba.revisado_en = _ahora()
        prueba.payment_id = pago.id
    await db.commit()
    return _a_lectura(prueba, current_user.schema_name)


@router.post("/{proof_id}/reject", response_model=PaymentProofRead, dependencies=tesorero_only)
async def reject_payment_proof(
    proof_id: uuid.UUID,
    payload: PaymentProofReject,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """El comprobante no es válido (ilegible, no llegó el dinero...): se rechaza con el motivo, que el residente ve."""
    prueba = await db.get(PaymentProof, proof_id)
    if prueba is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Comprobante no encontrado")
    if prueba.estado != EstadoComprobante.pendiente:
        raise HTTPException(status.HTTP_409_CONFLICT, "Este comprobante ya fue revisado")
    prueba.estado = EstadoComprobante.rechazado
    prueba.motivo_rechazo = payload.motivo.strip()
    prueba.revisado_por = uuid.UUID(current_user.user_id)
    prueba.revisado_en = _ahora()
    await db.commit()
    return _a_lectura(prueba, current_user.schema_name)
