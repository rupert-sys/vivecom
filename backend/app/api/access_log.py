import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_tenant_db, require_roles
from app.models.access_log import AccessLog, TipoAcceso
from app.models.property import Property
from app.models.user import Rol
from app.models.vehicle import Vehicle
from app.schemas.access_log import AccessLogCreate, AccessLogRead

router = APIRouter(prefix="/access-log", tags=["access-log"])

guardia_only = [Depends(require_roles(Rol.guardia, Rol.admin))]


async def _to_read(db: AsyncSession, log: AccessLog) -> AccessLogRead:
    placas = (await db.execute(select(Vehicle.placa).where(Vehicle.access_log_id == log.id))).scalars().all()
    return AccessLogRead(
        id=log.id,
        property_id=log.property_id,
        tipo=log.tipo,
        hora_entrada=log.hora_entrada,
        hora_salida=log.hora_salida,
        placas=list(placas),
    )


@router.post("", response_model=AccessLogRead, status_code=status.HTTP_201_CREATED, dependencies=guardia_only)
async def register_entry(payload: AccessLogCreate, db: AsyncSession = Depends(get_tenant_db)):
    """HU-S01: registro de entrada. Sin límite de visitantes ni horario (alcance §10.2)."""
    if payload.property_id is not None:
        propiedad = await db.get(Property, payload.property_id)
        if propiedad is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Vivienda no encontrada")

    log = AccessLog(
        property_id=payload.property_id,
        tipo=payload.tipo,
        hora_entrada=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(log)
    await db.flush()  # para tener log.id antes de crear los Vehicle (F2-03)

    for placa in payload.placas:
        db.add(Vehicle(access_log_id=log.id, placa=placa))

    # La lectura va ANTES del commit a propósito: el search_path del tenant
    # es transaccional (is_local=true, ver core/database.py) y ya no aplica
    # después de comitear — una consulta posterior en la misma sesión
    # revienta contra Postgres real con "relation ... does not exist".
    # Invisible en SQLite (las pruebas no distinguen schemas).
    resultado = await _to_read(db, log)
    await db.commit()
    return resultado


@router.post("/{access_log_id}/exit", response_model=AccessLogRead, dependencies=guardia_only)
async def register_exit(access_log_id: uuid.UUID, db: AsyncSession = Depends(get_tenant_db)):
    """HU-S01: registro de salida sobre un acceso ya abierto."""
    log = await db.get(AccessLog, access_log_id)
    if log is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Registro de acceso no encontrado")
    if log.hora_salida is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Este acceso ya tiene salida registrada")

    log.hora_salida = datetime.now(timezone.utc).replace(tzinfo=None)
    # Ver la nota en register_entry(): la lectura debe ir antes del commit,
    # no después.
    resultado = await _to_read(db, log)
    await db.commit()
    return resultado


@router.get("", response_model=list[AccessLogRead], dependencies=guardia_only)
async def list_access_logs(
    property_id: uuid.UUID | None = None,
    tipo: TipoAcceso | None = None,
    db: AsyncSession = Depends(get_tenant_db),
):
    query = select(AccessLog).order_by(AccessLog.hora_entrada.desc())
    if property_id is not None:
        query = query.where(AccessLog.property_id == property_id)
    if tipo is not None:
        query = query.where(AccessLog.tipo == tipo)
    logs = (await db.execute(query)).scalars().all()
    return [await _to_read(db, log) for log in logs]


@router.get("/{access_log_id}", response_model=AccessLogRead, dependencies=guardia_only)
async def get_access_log(access_log_id: uuid.UUID, db: AsyncSession = Depends(get_tenant_db)):
    log = await db.get(AccessLog, access_log_id)
    if log is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Registro de acceso no encontrado")
    return await _to_read(db, log)
