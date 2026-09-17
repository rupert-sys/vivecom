import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_tenant_db, require_roles
from app.core.security import hash_password
from app.models.user import Rol, UserAccount
from app.models.user_lookup import UserLookup
from app.schemas.user_account import UserAccountCreate, UserAccountRead

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
