import uuid
from collections import defaultdict
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

    await db.commit()
    # No se usa _to_read() aquí a propósito: re-consultar Vehicle en la MISMA
    # sesión después de este commit revienta contra Postgres real (el
    # search_path del tenant, fijado con is_local=true, ya no aplica — ver
    # core/database.py y el mismo bug ya corregido en polls.py). Las placas
    # ya se conocen del propio payload, no hace falta volver a pedirlas.
    return AccessLogRead(
        id=log.id, property_id=log.property_id, tipo=log.tipo,
        hora_entrada=log.hora_entrada, hora_salida=log.hora_salida,
        placas=list(payload.placas),
    )


@router.post("/{access_log_id}/exit", response_model=AccessLogRead, dependencies=guardia_only)
async def register_exit(access_log_id: uuid.UUID, db: AsyncSession = Depends(get_tenant_db)):
    """HU-S01: registro de salida sobre un acceso ya abierto."""
    log = await db.get(AccessLog, access_log_id)
    if log is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Registro de acceso no encontrado")
    if log.hora_salida is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Este acceso ya tiene salida registrada")

    log.hora_salida = datetime.now(timezone.utc).replace(tzinfo=None)
    # _to_read() consulta Vehicle — hay que hacerlo ANTES del commit (mismo
    # motivo que en register_entry): después de comitear, el search_path del
    # tenant ya no aplica en esta sesión. hora_salida ya está en memoria en
    # `log`, así que la respuesta sale completa aunque se arme antes de comitear.
    respuesta = await _to_read(db, log)
    await db.commit()
    return respuesta


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
    if not logs:
        return []

    # F2-22: antes hacía una consulta a Vehicle POR CADA log (N+1) llamando
    # _to_read() en el loop — con volumen real de accesos (guardia registra
    # decenas al día) esto escala linealmente en número de queries en vez de
    # quedarse en 2 fijas. Una sola consulta con IN (...) agrupa las placas
    # por access_log_id en memoria.
    log_ids = [log.id for log in logs]
    filas_vehiculo = (
        await db.execute(select(Vehicle.access_log_id, Vehicle.placa).where(Vehicle.access_log_id.in_(log_ids)))
    ).all()
    placas_por_log: dict[uuid.UUID, list[str]] = defaultdict(list)
    for access_log_id, placa in filas_vehiculo:
        placas_por_log[access_log_id].append(placa)

    return [
        AccessLogRead(
            id=log.id, property_id=log.property_id, tipo=log.tipo,
            hora_entrada=log.hora_entrada, hora_salida=log.hora_salida,
            placas=placas_por_log.get(log.id, []),
        )
        for log in logs
    ]


@router.get("/{access_log_id}", response_model=AccessLogRead, dependencies=guardia_only)
async def get_access_log(access_log_id: uuid.UUID, db: AsyncSession = Depends(get_tenant_db)):
    log = await db.get(AccessLog, access_log_id)
    if log is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Registro de acceso no encontrado")
    return await _to_read(db, log)
