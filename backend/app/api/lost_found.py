import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_tenant_db, require_roles
from app.models.lost_found_item import EstadoObjeto, LostFoundItem
from app.models.user import Rol
from app.schemas.lost_found_item import LostFoundItemCreate, LostFoundItemModerate, LostFoundItemRead

router = APIRouter(prefix="/lost-found", tags=["lost-found"])

admin_only = [Depends(require_roles(Rol.admin))]


@router.post("", response_model=LostFoundItemRead, status_code=status.HTTP_201_CREATED)
async def create_item(
    payload: LostFoundItemCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """HU-C05: cualquier residente puede publicar; queda pendiente de autorización."""
    item = LostFoundItem(
        publicado_por=uuid.UUID(current_user.user_id), descripcion=payload.descripcion, foto_url=payload.foto_url
    )
    db.add(item)
    await db.commit()
    return item


@router.get("", response_model=list[LostFoundItemRead])
async def list_items(current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_tenant_db)):
    """
    HU-C05: no aparece públicamente hasta que el admin la autoriza — solo
    admin ve las pendientes/rechazadas, para poder moderarlas.
    """
    query = select(LostFoundItem)
    if current_user.rol != Rol.admin.value:
        query = query.where(LostFoundItem.estado == EstadoObjeto.autorizado)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{item_id}", response_model=LostFoundItemRead)
async def get_item(
    item_id: uuid.UUID, current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_tenant_db)
):
    item = await db.get(LostFoundItem, item_id)
    if item is None or (current_user.rol != Rol.admin.value and item.estado != EstadoObjeto.autorizado):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Publicación no encontrada")
    return item


@router.patch("/{item_id}/moderate", response_model=LostFoundItemRead, dependencies=admin_only)
async def moderate_item(item_id: uuid.UUID, payload: LostFoundItemModerate, db: AsyncSession = Depends(get_tenant_db)):
    item = await db.get(LostFoundItem, item_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Publicación no encontrada")
    item.estado = payload.estado
    await db.commit()
    return item
