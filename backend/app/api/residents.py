import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_tenant_db, require_roles
from app.core.database import control_session, tenant_session
from app.core.security import create_access_token, hash_password
from app.models.property import Property
from app.models.resident import Resident, ResidentProperty
from app.models.tenant import Tenant
from app.models.user import Rol, UserAccount
from app.schemas.auth import TokenResponse
from app.schemas.resident import (
    LinkResidentToProperty, ResidentActivationPreview, ResidentActivationRequest, ResidentCreate, ResidentRead,
    ResidentUpdate,
)
from app.schemas.resident_import import ResidentImportResult
from app.services.resident_import_service import construir_plantilla, importar_condominos

router = APIRouter(tags=["residents"])

admin_only = [Depends(require_roles(Rol.admin))]
# F2-21: nombre/teléfono/email de TODA la base de residentes del tenant, sin
# acotar por vivienda — un residente no tiene motivo legítimo para ver el
# directorio completo del condominio, a diferencia de tesorero/guardia
# (cobranza y control de acceso, respectivamente).
staff_only = [Depends(require_roles(Rol.admin, Rol.tesorero, Rol.guardia))]


@router.post("/residents", response_model=ResidentRead, status_code=status.HTTP_201_CREATED, dependencies=admin_only)
async def create_resident(payload: ResidentCreate, db: AsyncSession = Depends(get_tenant_db)):
    resident = Resident(nombre=payload.nombre, telefono=payload.telefono, email=payload.email)
    db.add(resident)
    await db.commit()
    # Sin refresh() por la misma razón que en properties.py: el search_path
    # transaccional del tenant ya no aplica después del commit.
    return resident


@router.get("/residents", response_model=list[ResidentRead], dependencies=staff_only)
async def list_residents(db: AsyncSession = Depends(get_tenant_db)):
    result = await db.execute(select(Resident).order_by(Resident.nombre))
    return result.scalars().all()


_XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/residents/import-template", dependencies=admin_only)
async def download_import_template():
    """Excel de ejemplo con los encabezados exactos que reconoce /residents/import."""
    return Response(
        content=construir_plantilla(),
        media_type=_XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": 'attachment; filename="plantilla-condominos.xlsx"'},
    )


@router.post("/residents/import", response_model=ResidentImportResult, dependencies=admin_only)
async def import_residents(archivo: UploadFile = File(...), db: AsyncSession = Depends(get_tenant_db)):
    """
    Sube un Excel (nombre, teléfono, correo, propietario o inquilino, número de casa) y crea o completa las
    viviendas, los residentes y quién vive en cuál — ver resident_import_service.py para las reglas exactas.
    """
    if not archivo.filename or not archivo.filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "El archivo debe ser un Excel (.xlsx)")
    contenido = await archivo.read()
    try:
        return await importar_condominos(db, contenido)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from None



async def _resolver_tenant_por_nombre(control_db: AsyncSession, nombre_condominio: str) -> Tenant:
    """
    Sin sesión todavía (la app no tiene token hasta activarse): resuelve el tenant por el NOMBRE del condominio,
    tal como se lo dieron al residente — igual que /signup, público y sin CAPTCHA (mismo aviso de seguridad).
    Limitación conocida: comparación exacta salvo mayúsculas/espacios, sin tolerar acentos ni typos; y si dos
    condominios llegaran a compartir nombre exacto, se rechaza en vez de adivinar cuál — no hay forma de
    distinguirlos con solo el nombre.
    """
    candidatos = (
        await control_db.execute(select(Tenant).where(func.lower(Tenant.nombre) == nombre_condominio.strip().lower()))
    ).scalars().all()
    if len(candidatos) == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No se encontró un condominio con ese nombre")
    if len(candidatos) > 1:
        raise HTTPException(status.HTTP_409_CONFLICT, "Hay más de un condominio con ese nombre: contacta a tu administrador")
    return candidatos[0]


async def _cuenta_de_casa_sin_activar(db: AsyncSession, numero_de_casa: int) -> UserAccount | None:
    prop = (
        await db.execute(select(Property).where(Property.identificador == f"Casa {numero_de_casa}"))
    ).scalar_one_or_none()
    if prop is None:
        return None
    return (
        await db.execute(
            select(UserAccount).where(
                UserAccount.property_id == prop.id, UserAccount.rol == Rol.residente, UserAccount.activada.is_(False)
            )
        )
    ).scalar_one_or_none()


@router.get("/residents/activar/preview", response_model=ResidentActivationPreview)
async def preview_activacion(
    nombre_condominio: str, numero_de_casa: int, control_db: AsyncSession = Depends(control_session)
):
    """
    Lo que la app pide para mostrar en vivo, antes de llenar el resto del registro: a qué correo/usuario
    quedará ligada esa vivienda, para que el residente confirme que es la suya antes de seguir.
    """
    tenant = await _resolver_tenant_por_nombre(control_db, nombre_condominio)
    async with tenant_session(tenant.schema_name) as db:
        cuenta = await _cuenta_de_casa_sin_activar(db, numero_de_casa)
        if cuenta is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "No hay ninguna vivienda sin activar con ese número")
        return ResidentActivationPreview(email=cuenta.email, identificador=f"Casa {numero_de_casa}")


@router.post("/residents/activar", response_model=TokenResponse)
async def activar_residente(
    payload: ResidentActivationRequest, control_db: AsyncSession = Depends(control_session)
):
    """
    Reclama la cuenta de vivienda creada en bloque al aprovisionar el condominio (ver provisioning.py,
    UserAccount.activada) con los datos reales del residente y la contraseña que eligió — a diferencia del
    admin (contraseña temporal = nombre del condominio, forzada a cambiar), aquí no hay paso previo: el
    residente pone su contraseña definitiva desde el primer momento. Auto-login: regresa el token de una vez,
    igual que /signup con el admin.
    """
    tenant = await _resolver_tenant_por_nombre(control_db, payload.nombre_condominio)
    async with tenant_session(tenant.schema_name) as db:
        cuenta = await _cuenta_de_casa_sin_activar(db, payload.numero_de_casa)
        if cuenta is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "No hay ninguna vivienda sin activar con ese número")

        resident = Resident(nombre=payload.nombre_completo, telefono=payload.telefono, email=None)
        db.add(resident)
        await db.flush()  # necesitamos resident.id antes de ligarlo a la vivienda
        db.add(ResidentProperty(resident_id=resident.id, property_id=cuenta.property_id, rol=payload.rol))

        cuenta.resident_id = resident.id
        cuenta.password_hash = hash_password(payload.password)
        cuenta.activada = True
        await db.commit()

        token = create_access_token(
            subject=str(cuenta.id), tenant_id=str(tenant.id), schema_name=tenant.schema_name,
            rol=cuenta.rol.value, property_id=str(cuenta.property_id),
        )
        return TokenResponse(access_token=token)


@router.get("/residents/{resident_id}", response_model=ResidentRead, dependencies=staff_only)
async def get_resident(resident_id: uuid.UUID, db: AsyncSession = Depends(get_tenant_db)):
    resident = await db.get(Resident, resident_id)
    if resident is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Residente no encontrado")
    return resident


@router.patch("/residents/{resident_id}", response_model=ResidentRead, dependencies=admin_only)
async def update_resident(resident_id: uuid.UUID, payload: ResidentUpdate, db: AsyncSession = Depends(get_tenant_db)):
    resident = await db.get(Resident, resident_id)
    if resident is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Residente no encontrado")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(resident, field, value)
    await db.commit()
    return resident


# ---------- Relación N:N con Property ----------
# Ver alcance sección 2: un residente puede tener varias viviendas, cada una
# se administra de forma independiente. Estos endpoints solo gestionan el vínculo.

@router.post(
    "/properties/{property_id}/residents",
    status_code=status.HTTP_201_CREATED,
    dependencies=admin_only,
)
async def link_resident_to_property(
    property_id: uuid.UUID, payload: LinkResidentToProperty, db: AsyncSession = Depends(get_tenant_db)
):
    prop = await db.get(Property, property_id)
    if prop is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vivienda no encontrada")
    resident = await db.get(Resident, payload.resident_id)
    if resident is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Residente no encontrado")

    existing = (
        await db.execute(
            select(ResidentProperty).where(
                ResidentProperty.resident_id == resident.id,
                ResidentProperty.property_id == prop.id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Este residente ya está ligado a esta vivienda")

    link = ResidentProperty(resident_id=resident.id, property_id=prop.id, rol=payload.rol)
    db.add(link)
    await db.commit()
    return {"resident_id": str(resident.id), "property_id": str(prop.id), "rol": payload.rol.value}


@router.get("/properties/{property_id}/residents", response_model=list[ResidentRead])
async def list_property_residents(
    property_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    # Mismo control de acceso que get_property_statement (properties.py):
    # staff ve cualquier vivienda, un residente solo la propia.
    es_staff = current_user.rol in {Rol.admin.value, Rol.tesorero.value, Rol.guardia.value}
    if not es_staff and current_user.property_id != str(property_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes acceso a los residentes de esta vivienda")

    result = await db.execute(
        select(Resident).join(ResidentProperty).where(ResidentProperty.property_id == property_id)
    )
    return result.scalars().all()


@router.delete(
    "/properties/{property_id}/residents/{resident_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=admin_only,
)
async def unlink_resident_from_property(
    property_id: uuid.UUID, resident_id: uuid.UUID, db: AsyncSession = Depends(get_tenant_db)
):
    link = (
        await db.execute(
            select(ResidentProperty).where(
                ResidentProperty.resident_id == resident_id,
                ResidentProperty.property_id == property_id,
            )
        )
    ).scalar_one_or_none()
    if link is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ese residente no está ligado a esta vivienda")
    await db.delete(link)
    await db.commit()
