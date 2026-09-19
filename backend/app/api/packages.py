import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_tenant_db, require_roles
from app.core.config import settings
from app.models.package import Package
from app.models.property import Property
from app.models.user import Rol
from app.schemas.package import PackageCreate, PackageRead
from app.services.notification_providers.twilio_provider import TwilioProvider
from app.services.package_notification_service import send_package_notifications

router = APIRouter(prefix="/packages", tags=["packages"])

guardia_only = [Depends(require_roles(Rol.guardia, Rol.admin))]

_notification_provider = TwilioProvider(
    account_sid=settings.twilio_account_sid,
    auth_token=settings.twilio_auth_token,
    whatsapp_from=settings.twilio_whatsapp_from,
    sms_from=settings.twilio_sms_from,
)


@router.post("", response_model=PackageRead, status_code=status.HTTP_201_CREATED, dependencies=guardia_only)
async def register_package(payload: PackageCreate, db: AsyncSession = Depends(get_tenant_db)):
    """HU-S05: el guardia registra la llegada de un paquete."""
    propiedad = await db.get(Property, payload.property_id)
    if propiedad is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vivienda no encontrada")

    paquete = Package(property_id=payload.property_id, fecha_llegada=datetime.now(timezone.utc).replace(tzinfo=None))
    db.add(paquete)
    await db.commit()
    return paquete


@router.get("", response_model=list[PackageRead], dependencies=guardia_only)
async def list_packages(pendientes: bool | None = None, db: AsyncSession = Depends(get_tenant_db)):
    query = select(Package).order_by(Package.fecha_llegada.desc())
    if pendientes is True:
        query = query.where(Package.fecha_recogido.is_(None))
    elif pendientes is False:
        query = query.where(Package.fecha_recogido.is_not(None))
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/mine", response_model=list[PackageRead])
async def list_my_packages(
    current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_tenant_db)
):
    """Los paquetes de la propia vivienda del residente: primero los que aún están en la caseta."""
    if current_user.property_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Esta acción es solo para residentes ligados a una vivienda")
    resultado = await db.execute(
        select(Package)
        .where(Package.property_id == uuid.UUID(current_user.property_id))
        .order_by(Package.fecha_recogido.is_not(None), Package.fecha_llegada.desc())
        .limit(50)
    )
    return resultado.scalars().all()


@router.post("/{package_id}/pickup", response_model=PackageRead, dependencies=guardia_only)
async def mark_package_picked_up(package_id: uuid.UUID, db: AsyncSession = Depends(get_tenant_db)):
    """HU-S05: al recogerse, se cierra el registro y se dispara la segunda notificación."""
    paquete = await db.get(Package, package_id)
    if paquete is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Paquete no encontrado")
    if paquete.fecha_recogido is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Este paquete ya fue recogido")

    paquete.fecha_recogido = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    return paquete


@router.post("/send-notifications", dependencies=guardia_only)
async def trigger_send_package_notifications(db: AsyncSession = Depends(get_tenant_db)):
    """Disparo manual de notificaciones de paquetería. El job real corre vía Celery Beat."""
    enviados = await send_package_notifications(db, _notification_provider)
    return {"paquetes_notificados": enviados}
