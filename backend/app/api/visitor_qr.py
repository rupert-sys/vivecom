import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_tenant_db, require_roles
from app.models.resident import Resident, ResidentProperty
from app.models.user import Rol
from app.models.visitor_qr import VisitorQR
from app.models.property import Property
from app.schemas.visitor_qr import ProviderQRCreate, VisitorQRCreate, VisitorQRRead, VisitorQRValidateResult
from app.services.visitor_qr_service import generate_visitor_qr, validate_and_consume_qr

router = APIRouter(prefix="/visitor-qr", tags=["visitor-qr"])

guardia_only = [Depends(require_roles(Rol.guardia, Rol.admin))]


@router.post("", response_model=VisitorQRRead, status_code=status.HTTP_201_CREATED)
async def create_visitor_qr(
    payload: VisitorQRCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """HU-S02: el residente genera el QR para que su visita entre sin recibirla en la caseta."""
    if current_user.property_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Esta acción es solo para residentes ligados a una vivienda")
    property_id = uuid.UUID(current_user.property_id)
    propiedad = await db.get(Property, property_id)
    # Por ResidentProperty (quién vive en esta vivienda), no por UserAccount.resident_id: ese campo solo se
    # llena al activarse por /residents/activar (F4-02) — un residente real, importado por Excel antes de
    # que existiera ese flujo, con su acceso dado de alta a mano por el administrador desde Usuarios, nunca
    # lo tiene, y su código de visita se quedaba sin nombre/teléfono de a quién llamar. Si la vivienda tiene
    # más de un residente ligado (dueño + inquilino), se usa el primero — es solo un dato de contacto.
    residente = (
        await db.execute(select(Resident).join(ResidentProperty).where(ResidentProperty.property_id == property_id))
    ).scalars().first()
    return await generate_visitor_qr(
        db,
        property_id,
        nombre_visitante=payload.nombre_visitante.strip(),
        numero_personas=payload.numero_personas,
        horario_esperado=payload.horario_esperado,
        vivienda_nombre=propiedad.identificador if propiedad else None,
        residente_nombre=residente.nombre if residente else None,
        residente_telefono=residente.telefono if residente else None,
    )


@router.post(
    "/provider", response_model=VisitorQRRead, status_code=status.HTTP_201_CREATED, dependencies=guardia_only
)
async def create_provider_qr(payload: ProviderQRCreate, db: AsyncSession = Depends(get_tenant_db)):
    """El guardia emite un código de un solo uso para un proveedor (a una vivienda, o al condominio en general)."""
    if payload.property_id is not None and await db.get(Property, payload.property_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vivienda no encontrada")
    return await generate_visitor_qr(db, payload.property_id, tipo="proveedor", descripcion=payload.descripcion.strip())


@router.get("", response_model=list[VisitorQRRead])
async def list_my_visitor_qrs(
    current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_tenant_db)
):
    """Los códigos que la propia vivienda ha generado (los últimos 20), para mostrarlos otra vez o ver si ya se usaron."""
    if current_user.property_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Esta acción es solo para residentes ligados a una vivienda")
    resultado = await db.execute(
        select(VisitorQR)
        .where(VisitorQR.property_id == uuid.UUID(current_user.property_id))
        .order_by(VisitorQR.fecha_generado.desc())
        .limit(20)
    )
    return resultado.scalars().all()


@router.post("/{codigo}/validate", response_model=VisitorQRValidateResult, dependencies=guardia_only)
async def validate_visitor_qr(codigo: str, db: AsyncSession = Depends(get_tenant_db)):
    """HU-S03: el guardia escanea el QR del visitante para autorizar su acceso."""
    resultado = await validate_and_consume_qr(db, codigo)
    return VisitorQRValidateResult(**vars(resultado))
