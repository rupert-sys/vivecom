"""
Portal de administrador principal de Vivecom (staff, no un tenant más): listar, ver detalle, activar/desactivar,
editar y crear condominios desde un solo lugar. Ver la nota de alcance en app/models/vivecom_staff.py sobre por
qué esto vive detrás de get_current_staff y no de un rol dentro de Rol (que es por-tenant).
"""

import asyncio
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_staff
from app.core.database import control_session, tenant_session
from app.core.provisioning import eliminar_tenant_permanentemente, provision_tenant_con_casas
from app.core.security import verify_password
from app.models.property import Property
from app.models.tenant import Tenant
from app.models.user import Rol, UserAccount
from app.models.vivecom_staff import VivecomStaff
from app.schemas.staff import CurrentStaff
from app.schemas.staff_tenant import (
    TenantCreateRequest,
    TenantCreateResponse,
    TenantDeleteRequest,
    TenantDetail,
    TenantListItem,
    TenantUpdate,
)
from app.services.tenant_domain import generar_dominio_unico

router = APIRouter(prefix="/staff/tenants", tags=["staff"])

# Con 200+ tenants, contar viviendas uno a la vez (como hace executive_report_service, pensado para un
# dashboard financiero mucho más pesado) sería demasiado lento para un listado simple — se limita la
# concurrencia en vez de dispararlas todas a la vez para no agotar el pool de conexiones (ver database.py).
_TENANTS_CONCURRENTES = 20


async def _contar_viviendas(schema_name: str) -> int:
    async with tenant_session(schema_name) as db:
        return (await db.execute(select(func.count(Property.id)))).scalar() or 0


async def _email_del_admin(schema_name: str) -> str | None:
    async with tenant_session(schema_name) as db:
        admin = (await db.execute(select(UserAccount).where(UserAccount.rol == Rol.admin))).scalars().first()
        return admin.email if admin else None


def _a_list_item(tenant: Tenant, viviendas: int) -> TenantListItem:
    return TenantListItem(
        tenant_id=tenant.id,
        nombre=tenant.nombre,
        activo=tenant.activo,
        fecha_creacion=tenant.fecha_creacion,
        precio_por_vivienda=float(tenant.precio_por_vivienda),
        viviendas=viviendas,
        en_papelera=tenant.en_papelera,
        papelera_en=tenant.papelera_en,
    )


async def _listar_con_viviendas(tenants: list[Tenant]) -> list[TenantListItem]:
    semaforo = asyncio.Semaphore(_TENANTS_CONCURRENTES)

    async def _con_limite(tenant: Tenant) -> int:
        async with semaforo:
            return await _contar_viviendas(tenant.schema_name)

    viviendas_por_tenant = await asyncio.gather(*(_con_limite(t) for t in tenants))
    return [_a_list_item(t, viviendas) for t, viviendas in zip(tenants, viviendas_por_tenant)]


@router.get("", response_model=list[TenantListItem])
async def listar_tenants(
    current_staff: CurrentStaff = Depends(get_current_staff),
    control_db: AsyncSession = Depends(control_session),
):
    # Un tenant en la papelera no aparece aquí — solo en GET /staff/tenants/papelera (ver esa ruta abajo).
    tenants = (
        await control_db.execute(select(Tenant).where(Tenant.en_papelera.is_(False)).order_by(Tenant.nombre))
    ).scalars().all()
    return await _listar_con_viviendas(tenants)


@router.get("/papelera", response_model=list[TenantListItem])
async def listar_papelera(
    current_staff: CurrentStaff = Depends(get_current_staff),
    control_db: AsyncSession = Depends(control_session),
):
    # Registrada ANTES de GET /{tenant_id}: FastAPI empareja rutas en el orden en que se registran, y
    # "papelera" no es un UUID válido — si esta ruta fuera después, /staff/tenants/papelera intentaría
    # resolverse como /staff/tenants/{tenant_id} y tronaría con un 422 en vez de llegar aquí.
    tenants = (
        await control_db.execute(
            select(Tenant).where(Tenant.en_papelera.is_(True)).order_by(Tenant.papelera_en.desc())
        )
    ).scalars().all()
    return await _listar_con_viviendas(tenants)


@router.get("/{tenant_id}", response_model=TenantDetail)
async def obtener_tenant(
    tenant_id: uuid.UUID,
    current_staff: CurrentStaff = Depends(get_current_staff),
    control_db: AsyncSession = Depends(control_session),
):
    tenant = await control_db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Condominio no encontrado")

    viviendas = await _contar_viviendas(tenant.schema_name)
    email_admin = await _email_del_admin(tenant.schema_name)
    return TenantDetail(**_a_list_item(tenant, viviendas).model_dump(), email_admin=email_admin)


@router.patch("/{tenant_id}", response_model=TenantDetail)
async def actualizar_tenant(
    tenant_id: uuid.UUID,
    payload: TenantUpdate,
    current_staff: CurrentStaff = Depends(get_current_staff),
    control_db: AsyncSession = Depends(control_session),
):
    tenant = await control_db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Condominio no encontrado")

    if payload.activo is not None:
        tenant.activo = payload.activo
    if payload.nombre is not None:
        tenant.nombre = payload.nombre
    if payload.precio_por_vivienda is not None:
        tenant.precio_por_vivienda = payload.precio_por_vivienda
    await control_db.commit()

    viviendas = await _contar_viviendas(tenant.schema_name)
    email_admin = await _email_del_admin(tenant.schema_name)
    return TenantDetail(**_a_list_item(tenant, viviendas).model_dump(), email_admin=email_admin)


@router.post("/{tenant_id}/papelera", response_model=TenantDetail)
async def enviar_a_papelera(
    tenant_id: uuid.UUID,
    current_staff: CurrentStaff = Depends(get_current_staff),
    control_db: AsyncSession = Depends(control_session),
):
    """Paso previo y reversible a borrar un condominio — ver Tenant.en_papelera. También lo desactiva
    (mismo bloqueo de login que "Suspender"), por si alguien no lo había desactivado antes."""
    tenant = await control_db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Condominio no encontrado")

    tenant.en_papelera = True
    tenant.papelera_en = datetime.now(timezone.utc).replace(tzinfo=None)  # columna sin timezone, ver Tenant.fecha_creacion
    tenant.activo = False
    await control_db.commit()

    viviendas = await _contar_viviendas(tenant.schema_name)
    email_admin = await _email_del_admin(tenant.schema_name)
    return TenantDetail(**_a_list_item(tenant, viviendas).model_dump(), email_admin=email_admin)


@router.post("/{tenant_id}/restaurar", response_model=TenantDetail)
async def restaurar_de_papelera(
    tenant_id: uuid.UUID,
    current_staff: CurrentStaff = Depends(get_current_staff),
    control_db: AsyncSession = Depends(control_session),
):
    """Saca al condominio de la papelera y lo reactiva — lo contrario exacto de enviar_a_papelera()."""
    tenant = await control_db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Condominio no encontrado")

    tenant.en_papelera = False
    tenant.papelera_en = None
    tenant.activo = True
    await control_db.commit()

    viviendas = await _contar_viviendas(tenant.schema_name)
    email_admin = await _email_del_admin(tenant.schema_name)
    return TenantDetail(**_a_list_item(tenant, viviendas).model_dump(), email_admin=email_admin)


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def borrar_tenant_permanentemente(
    tenant_id: uuid.UUID,
    payload: TenantDeleteRequest,
    current_staff: CurrentStaff = Depends(get_current_staff),
    control_db: AsyncSession = Depends(control_session),
):
    """
    Borrado IRREVERSIBLE: el schema completo del condominio (viviendas, residentes, pagos, todo) desaparece.
    Dos candados antes de llegar ahí: (1) el tenant debe estar ya en la papelera — nadie puede borrar de un
    tiro sin pasar por ese paso intermedio; (2) quien lo pide debe volver a escribir SU PROPIA contraseña de
    staff (no la del condominio) — confirma que de verdad es él y no una pestaña abierta sin vigilancia.
    """
    tenant = await control_db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Condominio no encontrado")
    if not tenant.en_papelera:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Primero hay que enviarlo a la papelera")

    staff = await control_db.get(VivecomStaff, uuid.UUID(current_staff.staff_id))
    if staff is None or not verify_password(payload.password, staff.password_hash):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Contraseña incorrecta")

    await eliminar_tenant_permanentemente(control_db, tenant)


@router.post("", response_model=TenantCreateResponse, status_code=status.HTTP_201_CREATED)
async def crear_tenant(
    payload: TenantCreateRequest,
    current_staff: CurrentStaff = Depends(get_current_staff),
    control_db: AsyncSession = Depends(control_session),
):
    """
    Mismo flujo que la landing pública (/signup, ver api/signup.py) pero disparado por el staff de Vivecom en
    vez de por quien se registra solo — útil cuando Vivecom da de alta un condominio por su cuenta (ventas,
    soporte) en vez de que el propio administrador lo haga desde el link público.
    """
    dominio = await generar_dominio_unico(control_db, payload.nombre_condominio)
    tenant, emails_viviendas = await provision_tenant_con_casas(
        payload.nombre_condominio, payload.cantidad_casas, dominio, payload.nombre_admin, payload.telefono_admin,
    )
    return TenantCreateResponse(
        tenant_id=tenant.id,
        nombre=tenant.nombre,
        email_admin=f"administracion@{dominio}",
        emails_viviendas=emails_viviendas,
    )
