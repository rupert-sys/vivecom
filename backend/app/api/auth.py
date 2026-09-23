from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import control_session, tenant_session
from app.core.security import create_access_token, hash_password, verify_password
from app.models.tenant import Tenant
from app.models.user import UserAccount
from app.models.user_lookup import UserLookup
from app.schemas.auth import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])

# F2-21: hash bcrypt de un valor fijo, sin usuario real detrás. Cuando el
# email no existe (o no tiene UserAccount en su tenant), igual se corre un
# verify_password() contra ESTE hash antes de responder 401 — así el tiempo
# de respuesta no delata si el email está registrado. Sin esto, un email
# inexistente respondía de inmediato (sin bcrypt) mientras uno real siempre
# corría el hash (~decenas de ms), un canal lateral de timing para enumerar
# cuentas pese a que el mensaje de error ya es idéntico en ambos casos.
_DUMMY_PASSWORD_HASH = hash_password("no-existe-ningun-usuario-con-este-password")


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, control_db: AsyncSession = Depends(control_session)):
    # 1. Resolver a qué tenant pertenece este email (tabla de control).
    lookup = (
        await control_db.execute(select(UserLookup).where(UserLookup.email == payload.email))
    ).scalar_one_or_none()
    if lookup is None:
        verify_password(payload.password, _DUMMY_PASSWORD_HASH)
        # Mismo mensaje que credenciales inválidas: no revelar si el email existe o no.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales inválidas")

    tenant = (
        await control_db.execute(select(Tenant).where(Tenant.id == lookup.tenant_id))
    ).scalar_one()

    # 2. Dentro del schema de ese tenant, verificar la contraseña.
    async with tenant_session(tenant.schema_name) as tenant_db:
        user = (
            await tenant_db.execute(select(UserAccount).where(UserAccount.email == payload.email))
        ).scalar_one_or_none()

        if user is None:
            verify_password(payload.password, _DUMMY_PASSWORD_HASH)
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales inválidas")

        # Cuenta de vivienda creada en bloque por /signup, sin activar todavía (ver UserAccount.activada): su
        # password_hash es un centinela que ningún password real produce — antes de comparar contra él, un
        # mensaje claro es mejor que "credenciales inválidas" (el residente no escribió mal su contraseña, es
        # que todavía no puso ninguna). No es una cuenta secreta: el administrador ya conoce esta vivienda.
        if not user.activada:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Esta cuenta todavía no se activó: complete el registro en la app.")

        if not verify_password(payload.password, user.password_hash):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales inválidas")

        token = create_access_token(
            subject=str(user.id),
            tenant_id=str(tenant.id),
            schema_name=tenant.schema_name,
            rol=user.rol.value,
            property_id=str(user.property_id) if user.property_id else None,
            debe_cambiar_password=user.debe_cambiar_password,
        )
        return TokenResponse(access_token=token)
