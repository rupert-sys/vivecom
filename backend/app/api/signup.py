from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import control_session
from app.core.provisioning import provision_tenant
from app.models.user_lookup import UserLookup
from app.schemas.signup import TenantSignupRequest, TenantSignupResponse

router = APIRouter(prefix="/signup", tags=["signup"])


@router.post("", response_model=TenantSignupResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: TenantSignupRequest, control_db: AsyncSession = Depends(control_session)):
    """
    F3-06: alta de un condominio nuevo sin intervención manual del equipo —
    hasta ahora la única forma de crear un tenant era el script de CLI
    app.core.provisioning, que alguien del equipo tenía que correr a mano.

    AVISO DE SEGURIDAD (decisión explícita del usuario, ver bitácora F3-06):
    este endpoint es PÚBLICO, sin autenticación, y crea un schema de
    Postgres completo por cada llamada exitosa. NO tiene rate-limiting,
    CAPTCHA ni verificación de identidad — el proyecto no tiene canal de
    correo (alcance: solo WhatsApp+SMS), así que no hay una verificación de
    email fácil de construir sin infraestructura nueva. Válido para probar
    el flujo y para demos; antes de exponerlo en producción real hace
    falta agregar al menos una de esas protecciones.
    """
    existente = (
        await control_db.execute(select(UserLookup).where(UserLookup.email == payload.admin_email))
    ).scalar_one_or_none()
    if existente is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe una cuenta con ese email")

    try:
        tenant = await provision_tenant(
            payload.nombre_condominio, payload.clabe_destino, payload.admin_email, payload.admin_password
        )
    except IntegrityError as exc:
        # Carrera real pero angosta: dos registros con el mismo email casi
        # simultáneos pasan el chequeo de arriba antes de que cualquiera
        # termine — provision_tenant() no es atómico de punta a punta (crea
        # el schema/tabla/tenant y el admin en transacciones separadas), así
        # que en ese caso exacto quedaría un schema y un Tenant huérfanos sin
        # admin utilizable. No se resuelve aquí: requeriría rehacer
        # provision_tenant() como una sola transacción, fuera del alcance de
        # F3-06 — se documenta como limitación conocida, igual que otras de
        # esta sesión (con_for_update no verificable en SQLite, etc.).
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe una cuenta con ese email") from exc

    return TenantSignupResponse(tenant_id=tenant.id, nombre=tenant.nombre, admin_email=payload.admin_email)
