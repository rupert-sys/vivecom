import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_tenant_db, require_roles
from app.core.business_rules import RESERVACION_ANTICIPACION_MINIMA_DIAS
from app.core.config import settings
from app.models.amenity import Amenity
from app.models.reservation import Reservation
from app.models.user import Rol
from app.schemas.reservation import ReservationCreate, ReservationRead
from app.services.notification_providers.twilio_provider import TwilioProvider
from app.services.reservation_service import (
    ReservaInvalida, create_reservation, is_amenity_approver, process_reservation_timeouts, resolve_reservation,
    telefonos_de_aprobadores, telefonos_de_vivienda,
)

router = APIRouter(prefix="/reservations", tags=["reservations"])

logger = logging.getLogger(__name__)

admin_only = [Depends(require_roles(Rol.admin))]

_notification_provider = TwilioProvider(
    account_sid=settings.twilio_account_sid,
    auth_token=settings.twilio_auth_token,
    whatsapp_from=settings.twilio_whatsapp_from,
    sms_from=settings.twilio_sms_from,
)

_MOTIVO_A_MENSAJE = {
    "rango_invalido": "El rango de fechas no es válido (fecha_fin debe ser posterior a fecha_inicio)",
    "fecha_pasada": "No se puede reservar en el pasado",
    "horario_ocupado": "Ese horario ya está ocupado por otra reservación",
}


async def _notificar_sin_romper_la_respuesta(telefonos: list[str], mensaje: str) -> None:
    """
    Revisión: este envío corre DESPUÉS de que la reservación (o su
    aprobación/rechazo) ya se guardó — antes, cualquier excepción aquí
    (un fallo de red hacia Twilio, un error inesperado) tumbaba la
    respuesta con un 500 aunque la acción ya hubiera tenido éxito,
    confundiendo a quien llamó al endpoint sobre si de verdad se aplicó.
    Una notificación fallida se registra, no se vuelve a intentar (a
    diferencia de F1-13/F1-32/F2-04, este envío es síncrono e inmediato
    por el reloj de periodo_limite_horas — ver la nota en request_reservation).
    """
    for telefono in telefonos:
        try:
            await _notification_provider.send(telefono, mensaje)
        except Exception:  # noqa: BLE001 — una notificación fallida no debe tumbar una acción ya guardada
            logger.exception("No se pudo notificar a %s sobre una reservación", telefono)


@router.get("/global-rules")
async def get_global_rules():
    """
    HU-C06: la anticipación mínima es solo una referencia informativa, no
    una regla de rechazo — ver la nota en reservation_service.create_reservation.
    Se expone aquí para que el panel/app la muestren como sugerencia.
    """
    return {"anticipacion_minima_dias_sugerida": RESERVACION_ANTICIPACION_MINIMA_DIAS}


@router.post("", response_model=ReservationRead, status_code=status.HTTP_201_CREATED)
async def request_reservation(
    payload: ReservationCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """HU-C06: el residente solicita la reservación; queda pendiente de aprobación (HU-C07)."""
    if current_user.property_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Esta acción es solo para residentes ligados a una vivienda")

    amenidad = await db.get(Amenity, payload.amenity_id)
    if amenidad is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Amenidad no encontrada")

    try:
        reserva = await create_reservation(
            db, payload.amenity_id, uuid.UUID(current_user.property_id), payload.fecha_inicio, payload.fecha_fin,
            datetime.now(timezone.utc).replace(tzinfo=None),
        )
    except ReservaInvalida as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, _MOTIVO_A_MENSAJE[exc.motivo]) from exc

    # HU-C07: notificación a los aprobadores al momento de solicitarse — no
    # se manda por un barrido periódico como en F1-13/F1-32, porque aquí sí
    # importa que llegue de inmediato: arranca el reloj de periodo_limite_horas.
    mensaje = f"Vivecom: nueva solicitud de reservación de {amenidad.nombre} pendiente de tu aprobación."
    await _notificar_sin_romper_la_respuesta(await telefonos_de_aprobadores(db, payload.amenity_id), mensaje)

    return reserva


@router.get("", response_model=list[ReservationRead])
async def list_reservations(current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_tenant_db)):
    """Admin/comité aprobador ven todas; un residente solo ve las de su propia vivienda."""
    query = select(Reservation).order_by(Reservation.fecha_inicio.desc())
    if current_user.rol not in {Rol.admin.value, Rol.comite_aprobador.value}:
        if current_user.property_id is None:
            return []
        query = query.where(Reservation.property_id == uuid.UUID(current_user.property_id))
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{reservation_id}", response_model=ReservationRead)
async def get_reservation(
    reservation_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    reserva = await db.get(Reservation, reservation_id)
    es_staff = current_user.rol in {Rol.admin.value, Rol.comite_aprobador.value}
    if reserva is None or (not es_staff and current_user.property_id != str(reserva.property_id)):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reservación no encontrada")
    return reserva


async def _resolve(reservation_id: uuid.UUID, aprobar: bool, current_user: CurrentUser, db: AsyncSession) -> ReservationRead:
    reserva_previa = await db.get(Reservation, reservation_id)
    if reserva_previa is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reservación no encontrada")

    es_aprobador_designado = await is_amenity_approver(db, reserva_previa.amenity_id, uuid.UUID(current_user.user_id))
    if current_user.rol != Rol.admin.value and not es_aprobador_designado:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No eres aprobador designado de esta amenidad")

    reserva = await resolve_reservation(db, reservation_id, uuid.UUID(current_user.user_id), aprobar)
    if reserva is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Esta reservación ya no está pendiente")

    # HU-C07: "el residente ve el estado ... notificado por los mismos 3 canales" — inmediato, mismo criterio que arriba.
    amenidad = await db.get(Amenity, reserva.amenity_id)
    veredicto = "aprobada" if aprobar else "rechazada"
    mensaje = f"Vivecom: tu reservación de {amenidad.nombre} fue {veredicto}."
    await _notificar_sin_romper_la_respuesta(await telefonos_de_vivienda(db, reserva.property_id), mensaje)

    return reserva


@router.post("/{reservation_id}/approve", response_model=ReservationRead)
async def approve_reservation(
    reservation_id: uuid.UUID, current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_tenant_db)
):
    return await _resolve(reservation_id, True, current_user, db)


@router.post("/{reservation_id}/reject", response_model=ReservationRead)
async def reject_reservation(
    reservation_id: uuid.UUID, current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_tenant_db)
):
    return await _resolve(reservation_id, False, current_user, db)


@router.post("/process-timeouts", dependencies=admin_only)
async def trigger_process_timeouts(db: AsyncSession = Depends(get_tenant_db)):
    """Disparo manual del rechazo/expiración automática (F2-17). El job real corre vía Celery Beat."""
    return await process_reservation_timeouts(db, datetime.now(timezone.utc).replace(tzinfo=None))
