import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_tenant_db, require_roles
from app.models.access_log import AccessLog, TipoAcceso
from app.models.property import Property
from app.models.user import Rol
from app.models.vehicle import Vehicle
from app.schemas.access_log import AccessLogCreate, AccessLogRead, EstacionamientoVisitas
from app.services.incident_broadcast import manager
from app.services.reglamento_service import get_reglamento

router = APIRouter(prefix="/access-log", tags=["access-log"])

guardia_only = [Depends(require_roles(Rol.guardia, Rol.admin))]


def _leer(log: AccessLog, placas: list[str]) -> AccessLogRead:
    return AccessLogRead(
        id=log.id, property_id=log.property_id, tipo=log.tipo,
        hora_entrada=log.hora_entrada, hora_salida=log.hora_salida, placas=placas,
        nombre_visitante=log.nombre_visitante, acompanantes=log.acompanantes or 0,
        identificacion=log.identificacion, autorizado_por=log.autorizado_por,
    )


async def _to_read(db: AsyncSession, log: AccessLog) -> AccessLogRead:
    placas = (await db.execute(select(Vehicle.placa).where(Vehicle.access_log_id == log.id))).scalars().all()
    return _leer(log, list(placas))


@router.post(
    "",
    response_model=AccessLogRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=guardia_only,
)
async def register_entry(
    payload: AccessLogCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """
    HU-S01: registro de entrada. Sin límite de visitantes ni horario (alcance §10.2).

    F2-07/F2-11: la app caseta manda `client_id` (generado en el dispositivo
    al encolar el registro offline) para que un reintento de sincronización
    sea idempotente. Si ya existe un registro con ese client_id: mismo
    payload → se regresa el registro existente (replay legítimo de un
    reintento); payload distinto → es un conflicto real (dos registros
    distintos compitiendo por el mismo client_id), se alerta al admin por el
    mismo canal de WebSocket de incidencias (F2-06) y se responde 409.
    """
    if payload.client_id is not None:
        existente = (await db.execute(select(AccessLog).where(AccessLog.client_id == payload.client_id))).scalar_one_or_none()
        if existente is not None:
            placas_existentes = sorted(
                (await db.execute(select(Vehicle.placa).where(Vehicle.access_log_id == existente.id))).scalars().all()
            )
            if (
                existente.property_id == payload.property_id
                and existente.tipo == payload.tipo
                and placas_existentes == sorted(payload.placas)
                and existente.nombre_visitante == payload.nombre_visitante
                and (existente.acompanantes or 0) == payload.acompanantes
                and existente.identificacion == payload.identificacion
                and existente.autorizado_por == payload.autorizado_por
            ):
                return await _to_read(db, existente)

            await manager.broadcast(
                current_user.schema_name,
                {
                    "evento": "sync_conflicto",
                    "recurso": "access_log",
                    "client_id": str(payload.client_id),
                    "motivo": "Ya existe un registro de acceso con este client_id pero con datos distintos.",
                },
            )
            raise HTTPException(status.HTTP_409_CONFLICT, "Conflicto de sincronización: este client_id ya existe con otros datos.")

    if payload.property_id is not None:
        propiedad = await db.get(Property, payload.property_id)
        if propiedad is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Vivienda no encontrada")

    log = AccessLog(
        property_id=payload.property_id,
        tipo=payload.tipo,
        hora_entrada=datetime.now(timezone.utc).replace(tzinfo=None),
        client_id=payload.client_id,
        nombre_visitante=payload.nombre_visitante,
        acompanantes=payload.acompanantes,
        identificacion=payload.identificacion,
        autorizado_por=payload.autorizado_por,
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
    return _leer(log, list(payload.placas))


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

    return [_leer(log, placas_por_log.get(log.id, [])) for log in logs]


@router.get("/estacionamiento-visitas", response_model=EstacionamientoVisitas, dependencies=guardia_only)
async def visitor_parking(db: AsyncSession = Depends(get_tenant_db)):
    """
    Cajones de visitas libres ahora mismo (reglamento Art. 2 IX-XI y Art. 17
    V.7): el vigilante decide si deja entrar un vehículo más o si el visitado
    tiene lugar propio. Cuenta un cajón por cada acceso de visitante o
    proveedor con vehículo que aún no registra salida.
    """
    reglamento = await get_reglamento(db)
    abiertos = (
        await db.execute(
            select(AccessLog.id, AccessLog.hora_entrada)
            .join(Vehicle, Vehicle.access_log_id == AccessLog.id)
            .where(AccessLog.hora_salida.is_(None), AccessLog.tipo != TipoAcceso.residente)
            .distinct()
        )
    ).all()
    limite = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=reglamento.horas_max_estacionamiento_visitas)
    ocupados = len(abiertos)
    return EstacionamientoVisitas(
        total_cajones=reglamento.cajones_visitas,
        ocupados=ocupados,
        libres=max(0, reglamento.cajones_visitas - ocupados),
        horas_maximas=reglamento.horas_max_estacionamiento_visitas,
        excedidos=[fila.id for fila in abiertos if fila.hora_entrada < limite],
    )


@router.get("/{access_log_id}", response_model=AccessLogRead, dependencies=guardia_only)
async def get_access_log(access_log_id: uuid.UUID, db: AsyncSession = Depends(get_tenant_db)):
    log = await db.get(AccessLog, access_log_id)
    if log is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Registro de acceso no encontrado")
    return await _to_read(db, log)
