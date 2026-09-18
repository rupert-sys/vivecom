"""
F3-04: login de un empleado de Vivecom (VivecomStaff), separado por completo
del login de tenant (auth.py) — ver la nota de alcance en
app/models/vivecom_staff.py. No existe un endpoint de registro: la única
forma de crear una cuenta de staff es app/core/crear_staff.py, corrido a
mano por un operador con acceso al servidor.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import control_session
from app.core.security import create_staff_access_token, hash_password, verify_password
from app.models.vivecom_staff import VivecomStaff
from app.schemas.auth import TokenResponse
from app.schemas.staff import StaffLoginRequest

router = APIRouter(prefix="/staff", tags=["staff"])

# Mismo criterio de F2-21 (timing side-channel en /auth/login): se corre un
# verify_password() contra ESTE hash señuelo también cuando el email no
# existe, para que el tiempo de respuesta no delate si un email de staff
# está registrado.
_DUMMY_PASSWORD_HASH = hash_password("no-existe-ningun-staff-con-este-password")


@router.post("/login", response_model=TokenResponse)
async def staff_login(payload: StaffLoginRequest, control_db: AsyncSession = Depends(control_session)):
    staff = (
        await control_db.execute(select(VivecomStaff).where(VivecomStaff.email == payload.email))
    ).scalar_one_or_none()

    if staff is None:
        verify_password(payload.password, _DUMMY_PASSWORD_HASH)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales inválidas")

    if not verify_password(payload.password, staff.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales inválidas")

    token = create_staff_access_token(subject=str(staff.id))
    return TokenResponse(access_token=token)
