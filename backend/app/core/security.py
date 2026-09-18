from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(*, subject: str, tenant_id: str, schema_name: str, rol: str, property_id: str | None) -> str:
    """
    El JWT lleva todo lo necesario para resolver el tenant y el rol sin volver a
    consultar la base de datos de control en cada request: tenant_id, schema_name
    (para fijar el search_path) y rol (para autorización).
    """
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,  # user_account.id
        "tenant_id": tenant_id,
        "schema": schema_name,
        "rol": rol,
        "property_id": property_id,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def create_staff_access_token(*, subject: str) -> str:
    """
    F3-04: token de un empleado de Vivecom (VivecomStaff), deliberadamente
    SIN tenant_id/schema/rol/property_id — a diferencia de create_access_token(),
    este NO da acceso a ningún tenant individual, solo al dashboard agregado
    (ver deps.get_current_staff). El claim `staff: true` es lo que distingue
    este tipo de token de uno normal de UserAccount al decodificarlo.
    """
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,  # vivecom_staff.id
        "staff": True,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
