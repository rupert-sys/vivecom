import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_tenant_db, require_roles
from app.core.security import hash_password
from app.models.property import Property
from app.models.user import Rol, UserAccount
from app.models.user_lookup import UserLookup
from app.schemas.user_account import UserAccountCreate, UserAccountRead, UserAccountUpdate

router = APIRouter(prefix="/users", tags=["users"])

admin_only = [Depends(require_roles(Rol.admin))]


@router.post("", response_model=UserAccountRead, status_code=status.HTTP_201_CREATED, dependencies=admin_only)
async def create_user(
    payload: UserAccountCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """
    F2-18: gestión mínima de cuentas de personal (tesorero, vocero, comité,
    guardia, otro admin) — sin esto no había forma de designar un aprobador
    de amenidades (F2-17) que no fuera el admin sembrado al aprovisionar el
    tenant. No hay flujo de invitación por correo: el admin comparte la
    contraseña temporal por fuera de la app.

    También es el único punto para dar de alta un residente (rol=residente)
    con su property_id — bug real encontrado en F1-29 al construir la prueba
    de punta a punta del flujo de cobro: UserAccountCreate no tenía el campo
    property_id (Pydantic lo descartaba en silencio por no estar declarado),
    así que ningún tenant nuevo (ej. vía /signup, F3-06) tenía forma de crear
    una cuenta de residente utilizable — la app residente completa (F1-24 a
    F1-28) quedaba inalcanzable para un condominio recién dado de alta.
    """
    existente = (await db.execute(select(UserAccount).where(UserAccount.email == payload.email))).scalar_one_or_none()
    if existente is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe una cuenta con ese email")

    user = UserAccount(
        email=payload.email,
        password_hash=hash_password(payload.password),
        rol=payload.rol,
        property_id=payload.property_id,
        nombre=payload.nombre,
        telefono=payload.telefono,
    )
    db.add(user)
    await db.flush()  # necesitamos user.id antes de insertar en user_lookup

    # user_lookup vive en el schema de control (public), incluido en el
    # search_path de toda sesión de tenant (ver core/database.py) — sin este
    # registro la cuenta nueva no podría iniciar sesión: login resuelve el
    # tenant a partir del email consultando esta tabla primero.
    db.add(UserLookup(email=payload.email, tenant_id=uuid.UUID(current_user.tenant_id), user_id=user.id))
    await db.commit()
    return user


@router.get("", response_model=list[UserAccountRead], dependencies=admin_only)
async def list_users(rol: Rol | None = None, db: AsyncSession = Depends(get_tenant_db)):
    query = select(UserAccount).order_by(UserAccount.email)
    if rol is not None:
        query = query.where(UserAccount.rol == rol)
    result = await db.execute(query)
    return result.scalars().all()


async def _es_el_ultimo_admin(db: AsyncSession, user: UserAccount) -> bool:
    """Sin ningún admin nadie podría volver a administrar el condominio ni dar de alta cuentas."""
    if user.rol != Rol.admin:
        return False
    total = (await db.execute(select(func.count()).select_from(UserAccount).where(UserAccount.rol == Rol.admin))).scalar_one()
    return total <= 1


@router.patch("/{user_id}", response_model=UserAccountRead, dependencies=admin_only)
async def update_user(
    user_id: uuid.UUID,
    payload: UserAccountUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """
    Edita una cuenta: correo, contraseña, rol o vivienda. Solo cambia lo que se manda. Cambiar la contraseña NO
    cierra las sesiones ya abiertas (el token es sin estado y dura hasta 12 horas).
    """
    user = await db.get(UserAccount, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cuenta no encontrada")
    cambios = payload.model_fields_set

    if payload.email is not None and payload.email != user.email:
        # user_lookup es global (todos los condominios): un correo solo puede vivir en una cuenta de todo Vivecom.
        ocupado = (await db.execute(select(UserLookup).where(UserLookup.email == payload.email))).scalar_one_or_none()
        if ocupado is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe una cuenta con ese email")
        user.email = payload.email
        await db.execute(update(UserLookup).where(UserLookup.user_id == user.id).values(email=payload.email))

    if payload.password is not None:
        user.password_hash = hash_password(payload.password)
        user.debe_cambiar_password = False  # el admin acaba de fijar una contraseña real: la temporal ya no aplica

    if payload.nombre is not None:
        user.nombre = payload.nombre
    if payload.telefono is not None:
        user.telefono = payload.telefono

    if payload.rol is not None and payload.rol != user.rol:
        if str(user.id) == current_user.user_id:
            raise HTTPException(status.HTTP_409_CONFLICT, "No puedes cambiar tu propio rol")
        if await _es_el_ultimo_admin(db, user):
            raise HTTPException(status.HTTP_409_CONFLICT, "Es el único administrador: no se puede cambiar su rol")
        user.rol = payload.rol

    if "property_id" in cambios:
        if payload.property_id is not None and await db.get(Property, payload.property_id) is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Vivienda no encontrada")
        user.property_id = payload.property_id

    if ("rol" in cambios or "property_id" in cambios) and user.rol == Rol.residente and user.property_id is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Un residente necesita una vivienda")

    await db.commit()
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=admin_only)
async def delete_user(
    user_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Da de baja una cuenta (deja de poder iniciar sesión). Un token ya emitido sigue valiendo hasta que expire."""
    user = await db.get(UserAccount, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cuenta no encontrada")
    if str(user.id) == current_user.user_id:
        raise HTTPException(status.HTTP_409_CONFLICT, "No puedes eliminar tu propia cuenta")
    if await _es_el_ultimo_admin(db, user):
        raise HTTPException(status.HTTP_409_CONFLICT, "Es el único administrador: no se puede eliminar")
    try:
        await db.execute(delete(UserLookup).where(UserLookup.user_id == user.id))
        await db.delete(user)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "La cuenta tiene registros asociados y no se puede eliminar") from None
