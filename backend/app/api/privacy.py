import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_tenant_db
from app.models.user import UserAccount
from app.schemas.privacy import PrivacyAcceptanceRead, PrivacyNoticeRead
from app.schemas.resident import ResidentRead
from app.services.privacy_service import PRIVACY_NOTICE_TEXT, accept_privacy_notice, erase_personal_data, export_personal_data

router = APIRouter(tags=["privacy"])


@router.get("/privacy-notice", response_model=PrivacyNoticeRead)
async def get_privacy_notice():
    """Público, sin autenticación: cualquiera debe poder leerlo antes de darse de alta."""
    return PrivacyNoticeRead(texto=PRIVACY_NOTICE_TEXT)


async def _resident_id_de(current_user: CurrentUser, db: AsyncSession) -> uuid.UUID:
    cuenta = await db.get(UserAccount, uuid.UUID(current_user.user_id))
    if cuenta is None or cuenta.resident_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Esta cuenta no tiene un perfil de residente asociado")
    return cuenta.resident_id


@router.post("/me/privacy-notice/accept", response_model=PrivacyAcceptanceRead)
async def accept_notice(current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_tenant_db)):
    resident_id = await _resident_id_de(current_user, db)
    resident = await accept_privacy_notice(db, resident_id)
    if resident is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Perfil de residente no encontrado")
    return PrivacyAcceptanceRead(aviso_privacidad_aceptado_en=resident.aviso_privacidad_aceptado_en)


@router.get("/me/data-export")
async def export_my_data(current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_tenant_db)):
    """Derecho de Acceso (ARCO): todo lo que Vivecom tiene ligado a esta persona."""
    resident_id = await _resident_id_de(current_user, db)
    return await export_personal_data(db, resident_id, uuid.UUID(current_user.user_id))


@router.post("/me/request-erasure", response_model=ResidentRead)
async def request_erasure(current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_tenant_db)):
    """
    Derecho de Cancelación (ARCO): anonimiza los datos personales. No borra
    la fila — ver privacy_service.erase_personal_data sobre por qué.
    """
    resident_id = await _resident_id_de(current_user, db)
    resident = await erase_personal_data(db, resident_id)
    if resident is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Perfil de residente no encontrado")
    return resident
