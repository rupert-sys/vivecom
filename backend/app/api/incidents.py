import uuid
from datetime import datetime, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_tenant_db, require_roles
from app.core.security import decode_access_token
from app.models.incident import EstadoIncidencia, Incident, IncidentUpdate
from app.models.property import Property
from app.models.stored_file import StoredFile
from app.models.user import Rol
from app.schemas.incident import (
    IncidentCommentCreate, IncidentCommentRead, IncidentCreate, IncidentRead, IncidentStatusChange,
)
from app.services.file_links import referencia_interna, resolver_url
from app.services.incident_broadcast import manager

router = APIRouter(prefix="/incidents", tags=["incidents"])

# HU-S06: visible para admin y comité (lectura y aprobador), y guardia —
# quien las reporta. comite_lectura solo lee, no escribe (ver nota abajo).
ver_incidencias = [Depends(require_roles(Rol.admin, Rol.comite_lectura, Rol.comite_aprobador, Rol.guardia))]
gestionar_incidencias = [Depends(require_roles(Rol.admin, Rol.comite_aprobador, Rol.guardia))]


def _a_lectura(incidencia: Incident, schema_name: str) -> IncidentRead:
    """Una foto subida se guarda como referencia interna (/files/<id>): se entrega como enlace firmado."""
    lectura = IncidentRead.model_validate(incidencia)
    lectura.foto_url = resolver_url(lectura.foto_url, schema_name)
    return lectura


@router.post("", response_model=IncidentRead, status_code=status.HTTP_201_CREATED, dependencies=gestionar_incidencias)
async def create_incident(
    payload: IncidentCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """
    F2-07/F2-11: mismo esquema de idempotencia de sync que POST /access-log —
    ver la nota en access_log.register_entry(). `client_id` viene de la app
    caseta al encolar la incidencia offline.
    """
    # Lo que se guarda como foto: la referencia interna del archivo subido, o el enlace de texto de siempre.
    foto = referencia_interna(payload.foto_archivo_id) if payload.foto_archivo_id is not None else payload.foto_url

    if payload.client_id is not None:
        existente = (await db.execute(select(Incident).where(Incident.client_id == payload.client_id))).scalar_one_or_none()
        if existente is not None:
            if (
                existente.descripcion == payload.descripcion
                and existente.foto_url == foto
                and existente.tipo == payload.tipo
                and existente.property_id == payload.property_id
                and existente.persona_involucrada == payload.persona_involucrada
            ):
                return _a_lectura(existente, current_user.schema_name)

            await manager.broadcast(
                current_user.schema_name,
                {
                    "evento": "sync_conflicto",
                    "recurso": "incident",
                    "client_id": str(payload.client_id),
                    "motivo": "Ya existe una incidencia con este client_id pero con datos distintos.",
                },
            )
            raise HTTPException(status.HTTP_409_CONFLICT, "Conflicto de sincronización: este client_id ya existe con otros datos.")

    if payload.property_id is not None and await db.get(Property, payload.property_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vivienda no encontrada")
    if payload.foto_archivo_id is not None:
        archivo = await db.get(StoredFile, payload.foto_archivo_id)
        # Solo una foto propia y subida como foto de incidencia: nadie cuelga el archivo de otro.
        if archivo is None or archivo.kind != "incidencia" or str(archivo.uploaded_by) != current_user.user_id:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "La foto adjunta no existe o no es tuya.")

    incidencia = Incident(
        tipo=payload.tipo,
        property_id=payload.property_id,
        persona_involucrada=payload.persona_involucrada,
        reportado_por=uuid.UUID(current_user.user_id),
        descripcion=payload.descripcion,
        foto_url=foto,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        client_id=payload.client_id,
    )
    db.add(incidencia)
    await db.commit()

    await manager.broadcast(
        current_user.schema_name,
        {
            "evento": "incidencia_creada", "incident_id": str(incidencia.id),
            "descripcion": incidencia.descripcion, "tipo": incidencia.tipo,
        },
    )
    return _a_lectura(incidencia, current_user.schema_name)


@router.get("", response_model=list[IncidentRead], dependencies=ver_incidencias)
async def list_incidents(
    estado: str | None = None,
    tipo: str | None = None,
    property_id: uuid.UUID | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    query = select(Incident).order_by(Incident.created_at.desc())
    if estado is not None:
        query = query.where(Incident.estado == estado)
    if tipo is not None:
        query = query.where(Incident.tipo == tipo)
    if property_id is not None:
        query = query.where(Incident.property_id == property_id)
    result = await db.execute(query)
    return [_a_lectura(i, current_user.schema_name) for i in result.scalars().all()]


@router.get("/{incident_id}", response_model=IncidentRead, dependencies=ver_incidencias)
async def get_incident(
    incident_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    incidencia = await db.get(Incident, incident_id)
    if incidencia is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Incidencia no encontrada")
    return _a_lectura(incidencia, current_user.schema_name)


@router.patch("/{incident_id}/status", response_model=IncidentRead, dependencies=gestionar_incidencias)
async def change_incident_status(
    incident_id: uuid.UUID,
    payload: IncidentStatusChange,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """HU-S06: máquina de estados abierta → en proceso → resuelta."""
    incidencia = await db.get(Incident, incident_id)
    if incidencia is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Incidencia no encontrada")

    # F2-12: resolved_at refleja la transición A resuelta más reciente — se
    # limpia si se reabre, ya que la máquina de estados es deliberadamente
    # permisiva (puede ir hacia atrás, ver nota de F2-05).
    if payload.estado == EstadoIncidencia.resuelta and incidencia.estado != EstadoIncidencia.resuelta:
        incidencia.resolved_at = datetime.now(timezone.utc).replace(tzinfo=None)
    elif payload.estado != EstadoIncidencia.resuelta:
        incidencia.resolved_at = None

    incidencia.estado = payload.estado
    await db.commit()

    await manager.broadcast(
        current_user.schema_name,
        {"evento": "incidencia_actualizada", "incident_id": str(incidencia.id), "estado": incidencia.estado.value},
    )
    return _a_lectura(incidencia, current_user.schema_name)


@router.post(
    "/{incident_id}/comments",
    response_model=IncidentCommentRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=gestionar_incidencias,
)
async def add_incident_comment(
    incident_id: uuid.UUID,
    payload: IncidentCommentCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    incidencia = await db.get(Incident, incident_id)
    if incidencia is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Incidencia no encontrada")

    comentario = IncidentUpdate(
        incident_id=incident_id,
        user_id=uuid.UUID(current_user.user_id),
        comentario=payload.comentario,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(comentario)
    await db.commit()

    await manager.broadcast(
        current_user.schema_name,
        {"evento": "incidencia_comentada", "incident_id": str(incident_id), "comentario": comentario.comentario},
    )
    return comentario


@router.get("/{incident_id}/comments", response_model=list[IncidentCommentRead], dependencies=ver_incidencias)
async def list_incident_comments(incident_id: uuid.UUID, db: AsyncSession = Depends(get_tenant_db)):
    result = await db.execute(
        select(IncidentUpdate).where(IncidentUpdate.incident_id == incident_id).order_by(IncidentUpdate.created_at)
    )
    return result.scalars().all()


@router.websocket("/ws")
async def incident_alerts_ws(websocket: WebSocket, token: str = Query(...)):
    """
    F2-06: canal en tiempo real para admin/comité. El token va como query
    param (?token=...) porque el handshake de WebSocket desde un browser no
    permite mandar un header Authorization personalizado.
    """
    try:
        payload = decode_access_token(token)
    except jwt.InvalidTokenError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    if payload.get("rol") not in {Rol.admin.value, Rol.comite_lectura.value, Rol.comite_aprobador.value}:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    schema_name = payload["schema"]
    await manager.connect(schema_name, websocket)
    try:
        while True:
            await websocket.receive_text()  # el cliente no manda nada; solo detecta la desconexión
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(schema_name, websocket)
