from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import control_session, tenant_session
from app.core.security import create_access_token, verify_password
from app.models.tenant import Tenant
from app.models.user import UserAccount
from app.models.user_lookup import UserLookup
from app.schemas.auth import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, control_db: AsyncSession = Depends(control_session)):
    # 1. Resolver a qué tenant pertenece este email (tabla de control).
    lookup = (
        await control_db.execute(select(UserLookup).where(UserLookup.email == payload.email))
    ).scalar_one_or_none()
    if lookup is None:
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

        if user is None or not verify_password(payload.password, user.password_hash):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales inválidas")

        token = create_access_token(
            subject=str(user.id),
            tenant_id=str(tenant.id),
            schema_name=tenant.schema_name,
            rol=user.rol.value,
            property_id=str(user.property_id) if user.property_id else None,
        )
        return TokenResponse(access_token=token)
