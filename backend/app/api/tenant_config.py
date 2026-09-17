import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_tenant_db, require_roles
from app.models.clabe_change_log import ClabeChangeLog
from app.models.tenant import Tenant
from app.models.user import Rol
from app.schemas.tenant_config import ClabeChangeLogRead, ClabeChangeRequest, TenantClabeRead

router = APIRouter(prefix="/tenant", tags=["tenant-config"])

admin_only = [Depends(require_roles(Rol.admin))]


@router.get("/clabe", response_model=TenantClabeRead)
async def get_clabe(
    current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_tenant_db)
):
    """
    `public` está incluido en el search_path de toda sesión de tenant (ver
    core/database.py), así que se puede consultar `tenant` (que vive en el
    schema de control) usando la misma sesión sin abrir una conexión aparte.
    """
    tenant = await db.get(Tenant, uuid.UUID(current_user.tenant_id))
    if tenant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Condominio no encontrado")
    return tenant


@router.patch("/clabe", response_model=TenantClabeRead, dependencies=admin_only)
async def change_clabe(
    payload: ClabeChangeRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    tenant = await db.get(Tenant, uuid.UUID(current_user.tenant_id))
    if tenant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Condominio no encontrado")

    clabe_anterior = tenant.clabe_destino
    tenant.clabe_destino = payload.clabe_nueva

    log = ClabeChangeLog(
        tenant_id=tenant.id,
        clabe_anterior=clabe_anterior,
        clabe_nueva=payload.clabe_nueva,
        cambiado_por=uuid.UUID(current_user.user_id),
        # Revisión: ClabeChangeLog.fecha es un DateTime naive (igual que el
        # resto del proyecto, ver announcement_service.py). Guardar un
        # datetime aware aquí funcionaba "por accidente" contra SQLite
        # (las pruebas), pero truena contra Postgres real: "can't subtract
        # offset-naive and offset-aware datetimes".
        fecha=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(log)
    await db.commit()
    return tenant


@router.get("/clabe/historial", response_model=list[ClabeChangeLogRead], dependencies=admin_only)
async def clabe_change_history(db: AsyncSession = Depends(get_tenant_db)):
    result = await db.execute(select(ClabeChangeLog).order_by(ClabeChangeLog.fecha.desc()))
    return result.scalars().all()
