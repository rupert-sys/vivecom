"""
Acuerdos de pago (prórroga de cuotas). El residente solicita por escrito, el comité aprobador (o el
administrador) decide y el sistema da seguimiento: mientras se cumple, la vivienda no cuenta como morosa
(conserva voto y áreas comunes) y, si el comité lo decide, su recargo se congela. Ver
models/payment_agreement.py y el alcance (HU-A13).
"""

import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_tenant_db, require_roles
from app.models.payment_agreement import PaymentAgreement
from app.models.property import Property
from app.models.stored_file import StoredFile
from app.models.user import Rol
from app.schemas.payment_agreement import (
    AgreementApprove, AgreementRead, AgreementReject, AgreementRequest, NextPayment, ScheduledPayment,
)
from app.services.file_links import firmar_url
from app.services.payment_agreement_service import (
    abonado_al_acuerdo, cargos_sin_pagar, construir_calendario, pagos_confirmados, pendiente_cubierto, procesar_acuerdos,
    proximo_pago, sumar_meses, validar_calendario,
)
from app.services.payment_reconciliation_service import _locks_por_propiedad
from app.services.reglamento_service import get_reglamento, hoy_local

router = APIRouter(prefix="/payment-agreements", tags=["payment-agreements"])

# El comité aprobador decide (Art. 9 VII: "el comité tendrá la facultad de tomar el acuerdo"); el administrador
# también, para condominios sin comité configurado. El comité de solo lectura y tesorería lo ven, no deciden.
DECIDEN = (Rol.admin, Rol.comite_aprobador)
VEN_TODOS = {Rol.admin.value, Rol.comite_aprobador.value, Rol.comite_lectura.value, Rol.tesorero.value}
decide = [Depends(require_roles(*DECIDEN))]
ve_todos = [Depends(require_roles(Rol.admin, Rol.comite_aprobador, Rol.comite_lectura, Rol.tesorero))]
_ORDEN = {"solicitado": 0, "vigente": 1}


def _ahora() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def _a_lectura(
    db: AsyncSession, acuerdo: PaymentAgreement, schema_name: str, ve_staff: bool, hoy: date
) -> AgreementRead:
    propiedad = await db.get(Property, acuerdo.property_id)
    lectura = AgreementRead(
        id=acuerdo.id, property_id=acuerdo.property_id, vivienda=propiedad.identificador if propiedad else None,
        estado=acuerdo.estado, causa=acuerdo.causa, propuesta_pagos=acuerdo.propuesta_pagos,
        propuesta_primer_pago=acuerdo.propuesta_primer_pago, capturado_por_staff=acuerdo.capturado_por_staff,
        created_at=acuerdo.created_at, decidido_en=acuerdo.decidido_en, motivo_rechazo=acuerdo.motivo_rechazo,
        archivo_url=firmar_url(acuerdo.archivo_id, schema_name) if acuerdo.archivo_id else None,
        vigente_desde=acuerdo.vigente_desde, congela_recargo=acuerdo.congela_recargo if acuerdo.calendario else None,
        deuda_inicial=float(acuerdo.deuda_inicial) if acuerdo.deuda_inicial is not None else None,
    )
    if acuerdo.calendario:
        lectura.calendario = [ScheduledPayment(**p) for p in acuerdo.calendario]
        abonado = await abonado_al_acuerdo(db, acuerdo)
        lectura.abonado = abonado
        lectura.pendiente_cubierto = await pendiente_cubierto(db, acuerdo)
        if acuerdo.estado == "vigente":
            siguiente = proximo_pago(acuerdo.calendario, abonado, hoy)
            lectura.proximo_pago = NextPayment(**siguiente) if siguiente else None
    if ve_staff:
        lectura.incumplimientos_previos = (
            await db.execute(
                select(func.count()).select_from(PaymentAgreement).where(
                    PaymentAgreement.property_id == acuerdo.property_id,
                    PaymentAgreement.estado == "incumplido",
                    PaymentAgreement.id != acuerdo.id,
                )
            )
        ).scalar_one()
    return lectura


@router.post("", response_model=AgreementRead, status_code=status.HTTP_201_CREATED)
async def request_agreement(
    payload: AgreementRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """
    Solicita un acuerdo de pago por una causa justificada. El residente lo hace para su vivienda; tesorería
    captura la de un vecino que entregó su escrito en papel (`property_id`) — F0-12: antes lo capturaba el
    administrador, pero tesorería es quien debe modificar acuerdos (autorizar sigue siendo del comité, ver
    `decide` más abajo). La solicitud pendiente no cambia nada: los efectos empiezan cuando el comité la aprueba.
    """
    es_tesorero = current_user.rol == Rol.tesorero.value
    if current_user.property_id is not None:
        property_id = uuid.UUID(current_user.property_id)
    elif es_tesorero and payload.property_id is not None:
        property_id = payload.property_id
    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Indica la vivienda del acuerdo (solo tesorería captura por otro).")

    propiedad = await db.get(Property, property_id)
    if propiedad is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vivienda no encontrada")
    if not await cargos_sin_pagar(db, property_id):
        raise HTTPException(status.HTTP_409_CONFLICT, "La vivienda no tiene adeudos: no hay nada que acordar.")
    abierto = (
        await db.execute(
            select(func.count()).select_from(PaymentAgreement).where(
                PaymentAgreement.property_id == property_id, PaymentAgreement.estado.in_(["solicitado", "vigente"])
            )
        )
    ).scalar_one()
    if abierto:
        raise HTTPException(status.HTTP_409_CONFLICT, "La vivienda ya tiene un acuerdo de pago solicitado o vigente.")

    hoy = hoy_local()
    reglamento = await get_reglamento(db)
    if payload.primer_pago <= hoy:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "El primer pago debe ser posterior a hoy.")
    ultimo = sumar_meses(payload.primer_pago, payload.numero_de_pagos - 1)
    if ultimo > sumar_meses(hoy, reglamento.prorroga_max_meses):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"El acuerdo debe quedar liquidado en un máximo de {reglamento.prorroga_max_meses} meses "
            f"(el último pago sería el {ultimo:%d/%m/%Y}).",
        )
    if payload.archivo_id is not None:
        archivo = await db.get(StoredFile, payload.archivo_id)
        if archivo is None or archivo.kind != "acuerdo" or str(archivo.uploaded_by) != current_user.user_id:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "El documento adjunto no existe o no es tuyo.")

    acuerdo = PaymentAgreement(
        property_id=property_id, solicitado_por=uuid.UUID(current_user.user_id),
        capturado_por_staff=es_tesorero and current_user.property_id is None, causa=payload.causa.strip(),
        archivo_id=payload.archivo_id, propuesta_pagos=payload.numero_de_pagos, propuesta_primer_pago=payload.primer_pago,
        created_at=_ahora(),
    )
    db.add(acuerdo)
    await db.flush()
    lectura = await _a_lectura(db, acuerdo, current_user.schema_name, es_tesorero, hoy)
    await db.commit()
    return lectura


@router.get("", response_model=list[AgreementRead])
async def list_agreements(
    estado: str | None = None,
    property_id: uuid.UUID | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """El comité, el administrador y tesorería ven todos (los pendientes primero); un residente, los de su vivienda."""
    consulta = select(PaymentAgreement).order_by(PaymentAgreement.created_at.desc())
    ve_staff = current_user.rol in VEN_TODOS
    if ve_staff:
        if property_id is not None:
            consulta = consulta.where(PaymentAgreement.property_id == property_id)
    else:
        if current_user.property_id is None:
            return []
        consulta = consulta.where(PaymentAgreement.property_id == uuid.UUID(current_user.property_id))
    if estado is not None:
        consulta = consulta.where(PaymentAgreement.estado == estado)
    acuerdos = sorted((await db.execute(consulta)).scalars().all(), key=lambda a: _ORDEN.get(a.estado, 2))
    hoy = hoy_local()
    return [await _a_lectura(db, a, current_user.schema_name, ve_staff, hoy) for a in acuerdos]


@router.post("/process", dependencies=[Depends(require_roles(Rol.admin))])
async def process_agreements(db: AsyncSession = Depends(get_tenant_db)):
    """Disparo manual del seguimiento diario (el job real corre a las 00:00, antes del recargo de las 00:01)."""
    return await procesar_acuerdos(db, hoy_local())


async def _acuerdo_visible(db: AsyncSession, agreement_id: uuid.UUID, usuario: CurrentUser) -> PaymentAgreement:
    acuerdo = await db.get(PaymentAgreement, agreement_id)
    propio = usuario.property_id is not None and acuerdo is not None and str(acuerdo.property_id) == usuario.property_id
    if acuerdo is None or not (usuario.rol in VEN_TODOS or propio):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Acuerdo no encontrado")
    return acuerdo


@router.get("/{agreement_id}", response_model=AgreementRead)
async def get_agreement(
    agreement_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    acuerdo = await _acuerdo_visible(db, agreement_id, current_user)
    return await _a_lectura(db, acuerdo, current_user.schema_name, current_user.rol in VEN_TODOS, hoy_local())


@router.post("/{agreement_id}/approve", response_model=AgreementRead, dependencies=decide)
async def approve_agreement(
    agreement_id: uuid.UUID,
    payload: AgreementApprove,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """
    El comité aprueba: se fotografía la deuda de ese momento (los cargos que cubre el acuerdo), se fija el
    calendario (el propuesto o uno propio que sume esa deuda) y desde ahora la vivienda no cuenta como morosa
    por esos cargos. Todo dentro del candado de la vivienda, para no chocar con un pago que se está conciliando.
    """
    acuerdo = await db.get(PaymentAgreement, agreement_id)
    if acuerdo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Acuerdo no encontrado")
    hoy = hoy_local()
    reglamento = await get_reglamento(db)

    async with _locks_por_propiedad[acuerdo.property_id]:
        if acuerdo.estado != "solicitado":
            raise HTTPException(status.HTTP_409_CONFLICT, "Este acuerdo ya fue resuelto")
        cargos = await cargos_sin_pagar(db, acuerdo.property_id)
        if not cargos:
            raise HTTPException(status.HTTP_409_CONFLICT, "La vivienda ya no tiene adeudos: no hay nada que acordar.")
        deuda = round(sum(float(c.monto_base) + float(c.recargo_aplicado) for c in cargos), 2)

        if payload.pagos is not None:
            calendario = [{"fecha": p.fecha.isoformat(), "monto": p.monto} for p in payload.pagos]
        else:
            if acuerdo.propuesta_primer_pago <= hoy:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "La fecha propuesta ya pasó: indica un calendario nuevo al aprobar.",
                )
            calendario = construir_calendario(deuda, acuerdo.propuesta_pagos, acuerdo.propuesta_primer_pago)
        motivo = validar_calendario(calendario, deuda, hoy, reglamento.prorroga_max_meses)
        if motivo:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, motivo)

        acuerdo.estado = "vigente"
        acuerdo.calendario = calendario
        acuerdo.congela_recargo = payload.congela_recargo
        acuerdo.cargos_cubiertos = [str(c.id) for c in cargos]
        acuerdo.pagos_previos = await pagos_confirmados(db, acuerdo.property_id)
        acuerdo.deuda_inicial = deuda
        acuerdo.vigente_desde = _ahora()
        acuerdo.decidido_por = uuid.UUID(current_user.user_id)
        acuerdo.decidido_en = acuerdo.vigente_desde
        await db.flush()
        lectura = await _a_lectura(db, acuerdo, current_user.schema_name, True, hoy)
    await db.commit()
    return lectura


@router.post("/{agreement_id}/reject", response_model=AgreementRead, dependencies=decide)
async def reject_agreement(
    agreement_id: uuid.UUID,
    payload: AgreementReject,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    acuerdo = await db.get(PaymentAgreement, agreement_id)
    if acuerdo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Acuerdo no encontrado")
    if acuerdo.estado != "solicitado":
        raise HTTPException(status.HTTP_409_CONFLICT, "Este acuerdo ya fue resuelto")
    acuerdo.estado = "rechazado"
    acuerdo.motivo_rechazo = payload.motivo.strip()
    acuerdo.decidido_por = uuid.UUID(current_user.user_id)
    acuerdo.decidido_en = acuerdo.cerrado_en = _ahora()
    lectura = await _a_lectura(db, acuerdo, current_user.schema_name, True, hoy_local())
    await db.commit()
    return lectura


@router.post("/{agreement_id}/cancel", response_model=AgreementRead)
async def cancel_agreement(
    agreement_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """
    El residente retira su solicitud pendiente; el comité o el administrador pueden cancelar una solicitud o
    un acuerdo vigente (por ejemplo, si el vecino ya no lo necesita). Al cancelarse, lo cubierto vuelve a
    contar como mora y el recargo vuelve a correr.
    """
    acuerdo = await _acuerdo_visible(db, agreement_id, current_user)
    decide_el_comite = current_user.rol in {r.value for r in DECIDEN}
    if acuerdo.estado == "vigente" and not decide_el_comite:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo el comité o el administrador cancelan un acuerdo vigente.")
    if acuerdo.estado not in ("solicitado", "vigente"):
        raise HTTPException(status.HTTP_409_CONFLICT, "Este acuerdo ya está cerrado")
    if not decide_el_comite and current_user.property_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes permiso para esta acción")
    acuerdo.estado = "cancelado"
    acuerdo.cerrado_en = _ahora()
    lectura = await _a_lectura(db, acuerdo, current_user.schema_name, current_user.rol in VEN_TODOS, hoy_local())
    await db.commit()
    return lectura
