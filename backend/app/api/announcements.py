import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

# NOTA: fecha_publicacion vive en una columna DateTime plana (sin
# timezone=True), igual que fecha_deteccion en Payment — así que se guarda y
# se compara siempre en UTC "naive" (sin tzinfo). Un datetime con tzinfo
# (aware) rompe la comparación `>`/`<=` contra otro naive.
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_tenant_db, require_roles
from app.core.config import settings
from app.models.announcement import Announcement, ReadReceipt
from app.models.user import Rol
from app.schemas.announcement import AnnouncementCreate, AnnouncementRead, AnnouncementUpdate, ReadStatusEntry
from app.services.announcement_question_service import dudas_abiertas
from app.services.announcement_service import get_read_status, mark_announcement_read, send_announcement_notifications
from app.services.notification_providers.twilio_provider import TwilioProvider
from app.services.reglamento_service import get_reglamento, hoy_local

router = APIRouter(prefix="/announcements", tags=["announcements"])

admin_only = [Depends(require_roles(Rol.admin))]

_notification_provider = TwilioProvider(
    account_sid=settings.twilio_account_sid,
    auth_token=settings.twilio_auth_token,
    whatsapp_from=settings.twilio_whatsapp_from,
    sms_from=settings.twilio_sms_from,
    api_base=settings.twilio_api_base,
)


def _a_naive_utc(fecha: datetime) -> datetime:
    if fecha.tzinfo is not None:
        return fecha.astimezone(timezone.utc).replace(tzinfo=None)
    return fecha


def _ahora_naive_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _a_lectura(aviso: Announcement, leido: bool | None = None) -> AnnouncementRead:
    """Suma a lo guardado lo que se calcula al leer: si el aviso admite dudas HOY (activadas y dentro del plazo)."""
    lectura = AnnouncementRead.model_validate(aviso, from_attributes=True)
    return lectura.model_copy(update={"leido": leido, "dudas_abiertas": dudas_abiertas(aviso, hoy_local())})


@router.post("", response_model=AnnouncementRead, status_code=status.HTTP_201_CREATED, dependencies=admin_only)
async def create_announcement(payload: AnnouncementCreate, db: AsyncSession = Depends(get_tenant_db)):
    # Sin decirlo al publicar, las dudas siguen el valor por defecto del reglamento del condominio.
    permite_dudas = (
        payload.permite_dudas
        if payload.permite_dudas is not None
        else (await get_reglamento(db)).dudas_en_avisos_por_defecto
    )
    aviso = Announcement(
        titulo=payload.titulo,
        contenido=payload.contenido,
        fecha_publicacion=_a_naive_utc(payload.fecha_publicacion) if payload.fecha_publicacion else _ahora_naive_utc(),
        permite_dudas=permite_dudas,
        dudas_hasta=payload.dudas_hasta if permite_dudas else None,
    )
    db.add(aviso)
    await db.commit()
    return _a_lectura(aviso)


async def _ids_leidos(db: AsyncSession, property_id: str | None, announcement_ids: list[uuid.UUID]) -> set[uuid.UUID]:
    """
    IDs de aviso que la vivienda del usuario actual ya confirmó como
    leídos — una sola consulta por lote (F2-22: mismo criterio anti-N+1
    que list_access_logs()/list_polls()), no una por aviso.
    """
    if property_id is None or not announcement_ids:
        return set()
    receipts = (
        await db.execute(
            select(ReadReceipt.announcement_id).where(
                ReadReceipt.property_id == uuid.UUID(property_id), ReadReceipt.announcement_id.in_(announcement_ids)
            )
        )
    ).scalars().all()
    return set(receipts)


@router.get("", response_model=list[AnnouncementRead])
async def list_announcements(
    current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_tenant_db)
):
    """
    Un aviso "programado" (fecha_publicacion en el futuro) solo lo ve admin,
    para poder gestionarlo antes de que se publique — el resto de roles solo
    ve lo que ya está publicado.
    """
    query = select(Announcement).order_by(Announcement.fecha_publicacion.desc())
    if current_user.rol != Rol.admin.value:
        query = query.where(Announcement.fecha_publicacion <= _ahora_naive_utc())
    avisos = (await db.execute(query)).scalars().all()

    leidos = await _ids_leidos(db, current_user.property_id, [a.id for a in avisos])
    es_residente = current_user.property_id is not None
    return [_a_lectura(aviso, (aviso.id in leidos) if es_residente else None) for aviso in avisos]


@router.get("/{announcement_id}", response_model=AnnouncementRead)
async def get_announcement(
    announcement_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    aviso = await db.get(Announcement, announcement_id)
    if aviso is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aviso no encontrado")
    if current_user.rol != Rol.admin.value and aviso.fecha_publicacion > _ahora_naive_utc():
        # Se responde 404, no 403: para quien no es admin, un aviso todavía
        # no publicado no debe ni confirmar que existe.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aviso no encontrado")

    leidos = await _ids_leidos(db, current_user.property_id, [aviso.id])
    es_residente = current_user.property_id is not None
    return _a_lectura(aviso, (aviso.id in leidos) if es_residente else None)


@router.patch("/{announcement_id}", response_model=AnnouncementRead, dependencies=admin_only)
async def update_announcement(
    announcement_id: uuid.UUID, payload: AnnouncementUpdate, db: AsyncSession = Depends(get_tenant_db)
):
    aviso = await db.get(Announcement, announcement_id)
    if aviso is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aviso no encontrado")
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "fecha_publicacion" and value is not None:
            value = _a_naive_utc(value)
        setattr(aviso, field, value)
    if not aviso.permite_dudas:
        aviso.dudas_hasta = None  # sin dudas no tiene sentido un plazo
    await db.commit()
    return _a_lectura(aviso)


@router.post("/{announcement_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_read(
    announcement_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    if current_user.property_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Esta acción es solo para residentes ligados a una vivienda")
    aviso = await db.get(Announcement, announcement_id)
    if aviso is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aviso no encontrado")
    await mark_announcement_read(db, announcement_id, uuid.UUID(current_user.property_id))


@router.get("/{announcement_id}/read-status", response_model=list[ReadStatusEntry], dependencies=admin_only)
async def read_status(announcement_id: uuid.UUID, db: AsyncSession = Depends(get_tenant_db)):
    """HU-C01: qué viviendas ya leyeron este aviso."""
    aviso = await db.get(Announcement, announcement_id)
    if aviso is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aviso no encontrado")
    entradas = await get_read_status(db, announcement_id)
    return [
        ReadStatusEntry(property_id=e.property_id, identificador=e.identificador, leido=e.leido, leido_at=e.leido_at)
        for e in entradas
    ]


@router.post("/send-notifications", dependencies=admin_only)
async def trigger_send_notifications(db: AsyncSession = Depends(get_tenant_db)):
    """
    Disparo manual de notificaciones de avisos publicados (F1-32). El job
    real corre vía Celery Beat.
    """
    enviados = await send_announcement_notifications(db, _notification_provider, _ahora_naive_utc())
    return {"avisos_notificados": enviados}
