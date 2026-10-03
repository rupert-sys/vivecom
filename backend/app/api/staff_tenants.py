"""
Portal de administrador principal de Vivecom (staff, no un tenant más): listar, ver detalle, activar/desactivar,
editar y crear condominios desde un solo lugar. Ver la nota de alcance en app/models/vivecom_staff.py sobre por
qué esto vive detrás de get_current_staff y no de un rol dentro de Rol (que es por-tenant).
"""

import asyncio
import re
import uuid
from datetime import date, datetime, timezone
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_staff
from app.core.config import settings
from app.core.database import control_session, tenant_session
from app.core.provisioning import eliminar_tenant_permanentemente, provision_tenant_con_casas
from app.core.security import hash_password, verify_password
from app.models.property import Property
from app.models.tenant import Tenant
from app.models.tenant_payment import TenantPayment, TipoPagoTenant
from app.models.user import Rol, UserAccount
from app.models.vivecom_staff import VivecomStaff
from app.schemas.staff import CurrentStaff
from app.schemas.staff_tenant import (
    AdminPasswordChangeRequest,
    OcupacionResumen,
    TenantCreateRequest,
    TenantCreateResponse,
    TenantDeleteRequest,
    TenantDetail,
    TenantListItem,
    TenantPaymentRead,
    TenantUpdate,
)
from app.services.file_storage import get_storage
from app.services.file_types import MENSAJE_TIPO_NO_ACEPTADO, detectar_tipo
from app.services.residents_summary_service import residentes_principales
from app.services.tenant_domain import generar_dominio_unico

router = APIRouter(prefix="/staff/tenants", tags=["staff"])

# Con 200+ tenants, contar viviendas uno a la vez (como hace executive_report_service, pensado para un
# dashboard financiero mucho más pesado) sería demasiado lento para un listado simple — se limita la
# concurrencia en vez de dispararlas todas a la vez para no agotar el pool de conexiones (ver database.py).
_TENANTS_CONCURRENTES = 20


async def _contar_viviendas(schema_name: str) -> int:
    async with tenant_session(schema_name) as db:
        return (await db.execute(select(func.count(Property.id)))).scalar() or 0


def _nombre_seguro(nombre: str | None) -> str:
    # Mismo saneo que api/files.py: solo el nombre, sin rutas ni caracteres de control.
    limpio = re.sub(r"[\x00-\x1f\x7f\\/]", "_", (nombre or "recibo").split("/")[-1].split("\\")[-1]).strip()
    return (limpio or "recibo")[:120]


async def _detalle_del_tenant(tenant: Tenant) -> TenantDetail:
    """
    Un solo tenant_session para las tres cosas que el detalle necesita del lado del tenant:
    el admin (correo/nombre/teléfono — F0-12, antes solo se exponía el correo) y el resumen de
    ocupación (propietario/inquilino/sin residente — mismo cálculo que PropertiesPage del panel
    normal, reproducido aquí porque el staff no tiene sesión de tenant para llamar GET /properties).
    """
    async with tenant_session(tenant.schema_name) as db:
        propiedades = (await db.execute(select(Property))).scalars().all()
        admin = (await db.execute(select(UserAccount).where(UserAccount.rol == Rol.admin))).scalars().first()
        resumen = await residentes_principales(db, [p.id for p in propiedades])

    total = len(propiedades)
    propietario = sum(1 for _, rol, _ in resumen.values() if rol == "propietario")
    inquilino = sum(1 for _, rol, _ in resumen.values() if rol == "inquilino")
    ocupacion = OcupacionResumen(
        total=total, propietario=propietario, inquilino=inquilino, sin_residente=total - propietario - inquilino
    )
    return TenantDetail(
        **_a_list_item(tenant, total).model_dump(),
        email_admin=admin.email if admin else None,
        nombre_admin=admin.nombre if admin else None,
        telefono_admin=admin.telefono if admin else None,
        ocupacion=ocupacion,
    )


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

    return await _detalle_del_tenant(tenant)


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

    return await _detalle_del_tenant(tenant)


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

    return await _detalle_del_tenant(tenant)


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

    return await _detalle_del_tenant(tenant)


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
    tenant, emails_viviendas, emails_personal = await provision_tenant_con_casas(
        payload.nombre_condominio, payload.cantidad_casas, dominio, payload.nombre_admin, payload.telefono_admin,
    )
    return TenantCreateResponse(
        tenant_id=tenant.id,
        nombre=tenant.nombre,
        email_admin=f"administracion@{dominio}",
        email_tesorero=emails_personal["tesorero"],
        email_guardia=emails_personal["guardia"],
        email_vocero=emails_personal["vocero"],
        emails_viviendas=emails_viviendas,
    )


@router.post("/{tenant_id}/admin/password", status_code=status.HTTP_204_NO_CONTENT)
async def cambiar_password_del_admin(
    tenant_id: uuid.UUID,
    payload: AdminPasswordChangeRequest,
    current_staff: CurrentStaff = Depends(get_current_staff),
    control_db: AsyncSession = Depends(control_session),
):
    """
    Resetea la contraseña del administrador del condominio — para cuando el admin la olvida y no hay otro
    canal de soporte. El staff fija una nueva, nunca puede ver la actual (solo está hasheada).
    """
    tenant = await control_db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Condominio no encontrado")

    async with tenant_session(tenant.schema_name) as db:
        admin = (await db.execute(select(UserAccount).where(UserAccount.rol == Rol.admin))).scalars().first()
        if admin is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Este condominio no tiene una cuenta de administrador")
        admin.password_hash = hash_password(payload.password)
        admin.debe_cambiar_password = False
        await db.commit()


def _a_payment_read(pago: TenantPayment) -> TenantPaymentRead:
    return TenantPaymentRead(
        id=pago.id, tenant_id=pago.tenant_id, fecha=pago.fecha, monto=float(pago.monto), tipo_pago=pago.tipo_pago,
        notas=pago.notas, tiene_recibo=pago.recibo_storage_key is not None, registrado_en=pago.registrado_en,
    )


@router.get("/{tenant_id}/payments", response_model=list[TenantPaymentRead])
async def listar_pagos_del_tenant(
    tenant_id: uuid.UUID,
    current_staff: CurrentStaff = Depends(get_current_staff),
    control_db: AsyncSession = Depends(control_session),
):
    """Historial de pagos de ESTE condominio a Vivecom (la cuota del servicio) — no son pagos de residentes."""
    if await control_db.get(Tenant, tenant_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Condominio no encontrado")

    pagos = (
        await control_db.execute(
            select(TenantPayment).where(TenantPayment.tenant_id == tenant_id).order_by(TenantPayment.fecha.desc())
        )
    ).scalars().all()
    return [_a_payment_read(p) for p in pagos]


@router.post("/{tenant_id}/payments", response_model=TenantPaymentRead, status_code=status.HTTP_201_CREATED)
async def registrar_pago_del_tenant(
    tenant_id: uuid.UUID,
    fecha: date = Form(...),
    monto: float = Form(...),
    tipo_pago: TipoPagoTenant = Form(...),
    notas: str | None = Form(None),
    recibo: UploadFile | None = File(None),
    current_staff: CurrentStaff = Depends(get_current_staff),
    control_db: AsyncSession = Depends(control_session),
):
    """
    Registra un pago de este condominio a Vivecom, con su recibo de comprobación (opcional: foto o PDF,
    mismas reglas de tipo/tamaño que api/files.py). El recibo vive en el almacenamiento de archivos con una
    llave fuera de cualquier schema de tenant — este pago no es de ningún tenant desde ese punto de vista,
    solo por tenant_id en esta tabla (ver TenantPayment, schema de control).
    """
    tenant = await control_db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Condominio no encontrado")

    pago = TenantPayment(
        tenant_id=tenant_id, fecha=fecha, monto=monto, tipo_pago=tipo_pago, notas=notas,
        registrado_por=uuid.UUID(current_staff.staff_id),
        registrado_en=datetime.now(timezone.utc).replace(tzinfo=None),
    )

    if recibo is not None:
        datos = await recibo.read(settings.max_upload_bytes + 1)
        if len(datos) > settings.max_upload_bytes:
            raise HTTPException(
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                f"El archivo pesa más de {settings.max_upload_bytes // (1024 * 1024)} MB.",
            )
        if not datos:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "El archivo está vacío.")
        tipo = detectar_tipo(datos)
        if tipo is None:
            raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, MENSAJE_TIPO_NO_ACEPTADO)
        key = f"_control/tenant-payments/{pago.id}"
        await get_storage().save(key, datos, tipo)
        pago.recibo_storage_key = key
        pago.recibo_content_type = tipo
        pago.recibo_nombre_original = _nombre_seguro(recibo.filename)

    control_db.add(pago)
    await control_db.commit()
    return _a_payment_read(pago)


@router.get("/{tenant_id}/payments/{payment_id}/recibo")
async def descargar_recibo_de_pago(
    tenant_id: uuid.UUID,
    payment_id: uuid.UUID,
    current_staff: CurrentStaff = Depends(get_current_staff),
    control_db: AsyncSession = Depends(control_session),
):
    """
    El contenido del recibo. A diferencia de GET /files/{id}/content (enlace firmado, pensado para un
    residente anónimo-al-backend), aquí basta el propio JWT de staff como credencial: quien lo pide ya
    está autenticado contra este mismo endpoint.
    """
    pago = await control_db.get(TenantPayment, payment_id)
    if pago is None or pago.tenant_id != tenant_id or pago.recibo_storage_key is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recibo no encontrado")

    datos = await get_storage().read(pago.recibo_storage_key)
    return Response(
        content=datos,
        media_type=pago.recibo_content_type,
        headers={
            "Content-Disposition": f"inline; filename*=UTF-8''{quote(pago.recibo_nombre_original or 'recibo')}",
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, max-age=300",
        },
    )
