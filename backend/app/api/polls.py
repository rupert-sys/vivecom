import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_tenant_db, require_roles
from app.core.config import settings
from app.models.poll import Poll, PollOption
from app.models.user import Rol
from app.schemas.poll import PollCreate, PollOptionRead, PollRead, PollResultOption, PollResults, VoteCreate
from app.services.notification_providers.twilio_provider import TwilioProvider
from app.services.poll_service import VotoInvalido, cast_vote, create_poll, get_poll_results, process_poll_closures

router = APIRouter(prefix="/polls", tags=["polls"])

vocero_only = [Depends(require_roles(Rol.vocero, Rol.admin))]
admin_only = [Depends(require_roles(Rol.admin))]

_notification_provider = TwilioProvider(
    account_sid=settings.twilio_account_sid,
    auth_token=settings.twilio_auth_token,
    whatsapp_from=settings.twilio_whatsapp_from,
    sms_from=settings.twilio_sms_from,
)


async def _to_read(db: AsyncSession, poll: Poll) -> PollRead:
    opciones = (await db.execute(select(PollOption).where(PollOption.poll_id == poll.id))).scalars().all()
    return PollRead(
        id=poll.id,
        pregunta=poll.pregunta,
        fecha_cierre=poll.fecha_cierre,
        resultados_en_vivo=poll.resultados_en_vivo,
        quorum_alcanzado=poll.quorum_alcanzado,
        reactivada=poll.reactivada,
        opciones=[PollOptionRead(id=o.id, texto=o.texto) for o in opciones],
    )


@router.post("", response_model=PollRead, status_code=status.HTTP_201_CREATED, dependencies=vocero_only)
async def create_poll_endpoint(
    payload: PollCreate, current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_tenant_db)
):
    """HU-C02: solo el vocero crea votaciones."""
    poll, opciones = await create_poll(
        db, uuid.UUID(current_user.user_id), payload.pregunta, payload.opciones, payload.fecha_cierre,
        payload.resultados_en_vivo,
    )
    # No se usa _to_read() aquí a propósito: create_poll() ya comiteó, y
    # _to_read() vuelve a consultar poll_option en la misma sesión — revienta
    # contra Postgres real (ver docstring de create_poll). Las opciones ya
    # están en memoria, así que se arma la respuesta directo desde ahí.
    return PollRead(
        id=poll.id, pregunta=poll.pregunta, fecha_cierre=poll.fecha_cierre,
        resultados_en_vivo=poll.resultados_en_vivo, quorum_alcanzado=poll.quorum_alcanzado,
        reactivada=poll.reactivada,
        opciones=[PollOptionRead(id=o.id, texto=o.texto) for o in opciones],
    )


@router.get("", response_model=list[PollRead])
async def list_polls(db: AsyncSession = Depends(get_tenant_db)):
    polls = (await db.execute(select(Poll).order_by(Poll.fecha_cierre.desc()))).scalars().all()
    return [await _to_read(db, poll) for poll in polls]


@router.get("/{poll_id}", response_model=PollRead)
async def get_poll(poll_id: uuid.UUID, db: AsyncSession = Depends(get_tenant_db)):
    poll = await db.get(Poll, poll_id)
    if poll is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Votación no encontrada")
    return await _to_read(db, poll)


@router.post("/{poll_id}/vote", status_code=status.HTTP_204_NO_CONTENT)
async def vote(
    poll_id: uuid.UUID,
    payload: VoteCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """HU-C03: un voto por vivienda."""
    if current_user.property_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Esta acción es solo para residentes ligados a una vivienda")

    poll = await db.get(Poll, poll_id)
    if poll is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Votación no encontrada")

    try:
        await cast_vote(db, poll_id, uuid.UUID(current_user.property_id), payload.option_id)
    except VotoInvalido as exc:
        detalle = "Ya se registró un voto de esta vivienda" if exc.motivo == "ya_voto" else "Opción inválida"
        codigo = status.HTTP_409_CONFLICT if exc.motivo == "ya_voto" else status.HTTP_400_BAD_REQUEST
        raise HTTPException(codigo, detalle) from exc


@router.get("/{poll_id}/results", response_model=PollResults)
async def poll_results(poll_id: uuid.UUID, db: AsyncSession = Depends(get_tenant_db)):
    """
    HU-C02: los resultados se muestran en tiempo real solo si resultados_en_vivo
    lo permite; si no, hasta que la votación cierre.
    """
    poll = await db.get(Poll, poll_id)
    if poll is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Votación no encontrada")

    cerrada = poll.fecha_cierre <= date.today() or poll.quorum_alcanzado
    if not poll.resultados_en_vivo and not cerrada:
        raise HTTPException(status.HTTP_409_CONFLICT, "Los resultados de esta votación se muestran hasta el cierre")

    filas = await get_poll_results(db, poll_id)
    resultados = [PollResultOption(option_id=oid, texto=texto, votos=votos) for oid, texto, votos in filas]
    return PollResults(poll_id=poll_id, total_votos=sum(r.votos for r in resultados), resultados=resultados)


@router.post("/process-closures", dependencies=admin_only)
async def trigger_process_closures(hoy: date | None = None, db: AsyncSession = Depends(get_tenant_db)):
    """Disparo manual del cierre/quorum de votaciones (F2-14). El job real corre vía Celery Beat."""
    fecha_referencia = hoy or datetime.now(timezone.utc).date()
    resultado = await process_poll_closures(db, _notification_provider, fecha_referencia)
    return resultado
