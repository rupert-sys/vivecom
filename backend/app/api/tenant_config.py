import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_tenant_db, require_roles
from app.models.clabe_change_log import ClabeChangeLog
from app.models.tenant import Tenant
from app.models.user import Rol
from app.services.file_storage import get_storage
from app.services.file_types import MENSAJE_TIPO_NO_ACEPTADO, detectar_tipo
from app.schemas.tenant_config import (
    ClabeChangeLogRead, ClabeChangeRequest, TenantClabeRead, TenantConfigRead, TenantNombreUpdate,
)

router = APIRouter(prefix="/tenant", tags=["tenant-config"])

admin_only = [Depends(require_roles(Rol.admin))]



_MAX_LOGO_BYTES = 3 * 1024 * 1024  # un logo no necesita más: mantiene el header liviano en cualquier conexión


def _logo_key(schema_name: str) -> str:
    # Llave fija por tenant (no un uuid por subida): re-subir un logo pisa al anterior, sin dejar huérfanos.
    return f"{schema_name}/logo"


async def _tenant_o_404(current_user: CurrentUser, db: AsyncSession) -> Tenant:
    tenant = await db.get(Tenant, uuid.UUID(current_user.tenant_id))
    if tenant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Condominio no encontrado")
    return tenant


@router.get("", response_model=TenantConfigRead)
async def get_tenant_config(
    current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_tenant_db)
):
    tenant = await _tenant_o_404(current_user, db)
    return TenantConfigRead(id=tenant.id, nombre=tenant.nombre, tiene_logo=tenant.logo_content_type is not None)


@router.patch("", response_model=TenantConfigRead, dependencies=admin_only)
async def update_tenant_config(
    payload: TenantNombreUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    tenant = await _tenant_o_404(current_user, db)
    tenant.nombre = payload.nombre.strip()
    await db.commit()
    return TenantConfigRead(id=tenant.id, nombre=tenant.nombre, tiene_logo=tenant.logo_content_type is not None)


@router.get("/logo")
async def get_logo(
    current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_tenant_db)
):
    """Cualquier rol autenticado del tenant lo puede ver: es lo que se muestra en el encabezado del panel."""
    tenant = await _tenant_o_404(current_user, db)
    if tenant.logo_content_type is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Este condominio no tiene logo")
    datos = await get_storage().read(_logo_key(current_user.schema_name))
    return Response(content=datos, media_type=tenant.logo_content_type, headers={"Cache-Control": "private, max-age=300"})


@router.post("/logo", response_model=TenantConfigRead, dependencies=admin_only)
async def upload_logo(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    tenant = await _tenant_o_404(current_user, db)
    datos = await file.read(_MAX_LOGO_BYTES + 1)
    if len(datos) > _MAX_LOGO_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, f"El logo pesa más de {_MAX_LOGO_BYTES // (1024 * 1024)} MB.")
    if not datos:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "El archivo está vacío.")
    tipo = detectar_tipo(datos)
    if tipo is None or tipo == "application/pdf":
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, MENSAJE_TIPO_NO_ACEPTADO.replace(" o PDF", ""))

    await get_storage().save(_logo_key(current_user.schema_name), datos, tipo)
    tenant.logo_content_type = tipo
    await db.commit()
    return TenantConfigRead(id=tenant.id, nombre=tenant.nombre, tiene_logo=True)


@router.delete("/logo", status_code=status.HTTP_204_NO_CONTENT, dependencies=admin_only)
async def delete_logo(
    current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_tenant_db)
):
    tenant = await _tenant_o_404(current_user, db)
    if tenant.logo_content_type is not None:
        await get_storage().delete(_logo_key(current_user.schema_name))
        tenant.logo_content_type = None
        await db.commit()


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

    # Mismo chequeo que /signup (F1-29): sin esto, dos tenants con la misma
    # CLABE rompen el enrutamiento de depósitos SPEI para ambos.
    clabe_en_uso = (
        await db.execute(
            select(Tenant).where(Tenant.clabe_destino == payload.clabe_nueva, Tenant.id != tenant.id).limit(1)
        )
    ).scalar_one_or_none()
    if clabe_en_uso is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Esa CLABE ya está configurada para otro condominio")

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
