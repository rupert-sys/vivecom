import uuid
from typing import AsyncIterator

import jwt
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import tenant_session
from app.core.security import decode_access_token
from app.services.file_links import verificar_enlace
from app.models.user import Rol
from app.schemas.auth import CurrentUser
from app.schemas.staff import CurrentStaff

security_scheme = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security_scheme)) -> CurrentUser:
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesión expirada")
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido")

    return CurrentUser(
        user_id=payload["sub"],
        tenant_id=payload["tenant_id"],
        schema_name=payload["schema"],
        rol=payload["rol"],
        property_id=payload.get("property_id"),
    )


async def get_tenant_db(current_user: CurrentUser = Depends(get_current_user)) -> AsyncIterator[AsyncSession]:
    """Sesión de base de datos ya aislada al schema del tenant del usuario autenticado."""
    async with tenant_session(current_user.schema_name) as db:
        yield db


def get_current_staff(credentials: HTTPAuthorizationCredentials = Depends(security_scheme)) -> CurrentStaff:
    """
    F3-04: análogo a get_current_user(), pero para un token de VivecomStaff
    (create_staff_access_token) — el claim `staff: true` es lo único que lo
    distingue de un token normal de tenant. Un token de tenant normal (sin
    ese claim) se rechaza aquí con 403: por diseño, ningún UserAccount de
    ningún condominio (ni siquiera admin) puede llegar al dashboard agregado
    de esta forma — ese acceso es exclusivamente de VivecomStaff.
    """
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesión expirada")
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido")

    if payload.get("staff") is not True:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes permiso para esta acción")

    return CurrentStaff(staff_id=payload["sub"])


def require_roles(*allowed: Rol):
    """
    Guarda de autorización por rol. Uso en un endpoint:
    `@router.post(..., dependencies=[Depends(require_roles(Rol.tesorero, Rol.admin))])`
    """

    def _guard(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current_user.rol not in {r.value for r in allowed}:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes permiso para esta acción")
        return current_user

    return _guard


def enlace_de_archivo(t: str = Query(...)) -> tuple[uuid.UUID, str]:
    """Un enlace firmado a un archivo (ver file_links.py): (file_id, schema del tenant). Sin Authorization."""
    try:
        return verificar_enlace(t)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "El enlace expiró: pide uno nuevo")
    except (jwt.InvalidTokenError, ValueError, KeyError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Enlace inválido")


async def get_link_tenant_db(enlace: tuple[uuid.UUID, str] = Depends(enlace_de_archivo)) -> AsyncIterator[AsyncSession]:
    """Sesión aislada al tenant que firmó el enlace (el enlace hace de credencial, no hay usuario)."""
    async with tenant_session(enlace[1]) as db:
        yield db
