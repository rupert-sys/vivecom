"""
Dudas de los residentes sobre un aviso: un canal acotado con la administración, NO un chat entre
vecinos. La pregunta va solo a administración y comité; responden el administrador y el comité
aprobador; y al responder pueden publicarla como aclaración (sin nombre ni vivienda) para que los
demás no vuelvan a preguntar lo mismo. El residente se entera de la respuesta dentro de la app.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_tenant_db, require_roles
from app.models.announcement import Announcement, AnnouncementQuestion
from app.models.property import Property
from app.models.user import Rol
from app.schemas.announcement_question import QuestionAnswer, QuestionCreate, QuestionRead, QuestionUpdate
from app.services.announcement_question_service import MAX_DUDAS_ABIERTAS_POR_VIVIENDA, dudas_abiertas
from app.services.reglamento_service import hoy_local

router = APIRouter(tags=["announcement-questions"])

# Quién VE todas las dudas, y quién las RESPONDE (el comité de solo lectura no responde).
VEN_DUDAS = {Rol.admin.value, Rol.comite_lectura.value, Rol.comite_aprobador.value}
RESPONDEN = (Rol.admin, Rol.comite_aprobador)
puede_responder = [Depends(require_roles(*RESPONDEN))]
ve_dudas = [Depends(require_roles(Rol.admin, Rol.comite_lectura, Rol.comite_aprobador))]


def _ahora() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _a_lectura(
    duda: AnnouncementQuestion,
    usuario: CurrentUser,
    aviso_titulo: str | None = None,
    vivienda: str | None = None,
) -> QuestionRead:
    """La misma duda se ve distinto según quién la mire: el staff ve la vivienda; un vecino ajeno, nada."""
    es_staff = usuario.rol in VEN_DUDAS
    propia = usuario.property_id is not None and str(duda.property_id) == usuario.property_id
    return QuestionRead(
        id=duda.id, announcement_id=duda.announcement_id, aviso_titulo=aviso_titulo, texto=duda.texto,
        estado=duda.estado, respuesta=duda.respuesta, respondido_en=duda.respondido_en, publica=duda.publica,
        created_at=duda.created_at, propia=propia,
        vivienda=vivienda if es_staff else None,
        respuesta_nueva=propia and duda.estado == "respondida" and not duda.respuesta_vista,
    )


async def _aviso_visible(db: AsyncSession, announcement_id: uuid.UUID, usuario: CurrentUser) -> Announcement:
    aviso = await db.get(Announcement, announcement_id)
    # Un aviso programado (aún sin publicar) solo lo ve el admin; para los demás ni existe.
    if aviso is None or (usuario.rol != Rol.admin.value and aviso.fecha_publicacion > _ahora()):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aviso no encontrado")
    return aviso


async def _nombres_de_viviendas(db: AsyncSession, ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
    if not ids:
        return {}
    filas = (await db.execute(select(Property.id, Property.identificador).where(Property.id.in_(ids)))).all()
    return {fila.id: fila.identificador for fila in filas}


@router.post(
    "/announcements/{announcement_id}/questions", response_model=QuestionRead, status_code=status.HTTP_201_CREATED
)
async def ask_question(
    announcement_id: uuid.UUID,
    payload: QuestionCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """El residente manda una duda sobre un aviso. Llega solo a la administración y al comité."""
    if current_user.property_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Esta acción es solo para residentes ligados a una vivienda")
    aviso = await _aviso_visible(db, announcement_id, current_user)
    if not aviso.permite_dudas:
        raise HTTPException(status.HTTP_409_CONFLICT, "Este aviso no recibe dudas.")
    if not dudas_abiertas(aviso, hoy_local()):
        raise HTTPException(status.HTTP_409_CONFLICT, "El plazo para mandar dudas sobre este aviso ya cerró.")

    property_id = uuid.UUID(current_user.property_id)
    abiertas = (
        await db.execute(
            select(func.count()).select_from(AnnouncementQuestion).where(
                AnnouncementQuestion.announcement_id == announcement_id,
                AnnouncementQuestion.property_id == property_id,
                AnnouncementQuestion.estado == "abierta",
            )
        )
    ).scalar_one()
    if abiertas >= MAX_DUDAS_ABIERTAS_POR_VIVIENDA:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Ya tienes {MAX_DUDAS_ABIERTAS_POR_VIVIENDA} dudas sin responder sobre este aviso; espera a que te contesten.",
        )

    duda = AnnouncementQuestion(
        announcement_id=announcement_id, property_id=property_id, asked_by=uuid.UUID(current_user.user_id),
        texto=payload.texto.strip(), created_at=_ahora(),
    )
    if not duda.texto:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Escribe tu duda.")
    db.add(duda)
    await db.commit()
    return _a_lectura(duda, current_user, aviso.titulo)


@router.get("/announcements/{announcement_id}/questions", response_model=list[QuestionRead])
async def list_questions(
    announcement_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """
    La administración y el comité ven todas las dudas del aviso. Un residente ve las suyas más las
    aclaraciones públicas (de cualquiera, sin nombre ni vivienda). Cualquier otro rol, solo las públicas.
    """
    aviso = await _aviso_visible(db, announcement_id, current_user)
    query = select(AnnouncementQuestion).where(AnnouncementQuestion.announcement_id == announcement_id)
    if current_user.rol not in VEN_DUDAS:
        publicas = (AnnouncementQuestion.publica.is_(True)) & (AnnouncementQuestion.estado == "respondida")
        if current_user.property_id is not None:
            query = query.where(publicas | (AnnouncementQuestion.property_id == uuid.UUID(current_user.property_id)))
        else:
            query = query.where(publicas)
    dudas = (await db.execute(query.order_by(AnnouncementQuestion.created_at))).scalars().all()
    nombres = await _nombres_de_viviendas(db, {d.property_id for d in dudas}) if current_user.rol in VEN_DUDAS else {}
    return [_a_lectura(d, current_user, aviso.titulo, nombres.get(d.property_id)) for d in dudas]


@router.get("/announcement-questions/pending", response_model=list[QuestionRead], dependencies=ve_dudas)
async def pending_questions(
    current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_tenant_db)
):
    """La bandeja de la administración: las dudas sin responder de todos los avisos, las más viejas primero."""
    filas = (
        await db.execute(
            select(AnnouncementQuestion, Announcement.titulo)
            .join(Announcement, Announcement.id == AnnouncementQuestion.announcement_id)
            .where(AnnouncementQuestion.estado == "abierta")
            .order_by(AnnouncementQuestion.created_at)
        )
    ).all()
    nombres = await _nombres_de_viviendas(db, {duda.property_id for duda, _ in filas})
    return [_a_lectura(duda, current_user, titulo, nombres.get(duda.property_id)) for duda, titulo in filas]


@router.get("/announcement-questions/answered", response_model=list[QuestionRead], dependencies=ve_dudas)
async def answered_questions(
    current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_tenant_db)
):
    """Las ya respondidas (las más recientes primero), para publicarlas o retirarlas como aclaración."""
    filas = (
        await db.execute(
            select(AnnouncementQuestion, Announcement.titulo)
            .join(Announcement, Announcement.id == AnnouncementQuestion.announcement_id)
            .where(AnnouncementQuestion.estado == "respondida")
            .order_by(AnnouncementQuestion.respondido_en.desc())
            .limit(100)
        )
    ).all()
    nombres = await _nombres_de_viviendas(db, {duda.property_id for duda, _ in filas})
    return [_a_lectura(duda, current_user, titulo, nombres.get(duda.property_id)) for duda, titulo in filas]


@router.get("/announcement-questions/mine", response_model=list[QuestionRead])
async def my_questions(
    current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_tenant_db)
):
    """Las dudas de la vivienda del residente, con las respuestas que aún no ha visto marcadas como nuevas."""
    if current_user.property_id is None:
        return []
    filas = (
        await db.execute(
            select(AnnouncementQuestion, Announcement.titulo)
            .join(Announcement, Announcement.id == AnnouncementQuestion.announcement_id)
            .where(AnnouncementQuestion.property_id == uuid.UUID(current_user.property_id))
            .order_by(AnnouncementQuestion.created_at.desc())
        )
    ).all()
    return [_a_lectura(duda, current_user, titulo) for duda, titulo in filas]


@router.post("/announcement-questions/mine/seen", status_code=status.HTTP_204_NO_CONTENT)
async def mark_my_answers_seen(
    announcement_id: uuid.UUID | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """
    El residente abrió sus dudas: las respuestas dejan de marcarse como nuevas. Con `announcement_id` solo las
    de ese aviso (la app las marca al abrir el aviso, para no apagar las de otros que aún no ha visto).
    """
    if current_user.property_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Esta acción es solo para residentes ligados a una vivienda")
    consulta = select(AnnouncementQuestion).where(
        AnnouncementQuestion.property_id == uuid.UUID(current_user.property_id),
        AnnouncementQuestion.estado == "respondida",
        AnnouncementQuestion.respuesta_vista.is_(False),
    )
    if announcement_id is not None:
        consulta = consulta.where(AnnouncementQuestion.announcement_id == announcement_id)
    pendientes = (await db.execute(consulta)).scalars().all()
    for duda in pendientes:
        duda.respuesta_vista = True
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/announcement-questions/{question_id}/answer", response_model=QuestionRead, dependencies=puede_responder
)
async def answer_question(
    question_id: uuid.UUID,
    payload: QuestionAnswer,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Responde una duda (solo una vez: para cambiar lo publicado o corregir la respuesta, PATCH). Opcionalmente la publica."""
    duda = await db.get(AnnouncementQuestion, question_id)
    if duda is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Duda no encontrada")
    if duda.estado != "abierta":
        raise HTTPException(status.HTTP_409_CONFLICT, "Esta duda ya fue respondida")
    duda.estado = "respondida"
    duda.respuesta = payload.respuesta.strip()
    duda.respondido_por = uuid.UUID(current_user.user_id)
    duda.respondido_en = _ahora()
    duda.publica = payload.publicar
    duda.respuesta_vista = False
    # El aviso se consulta ANTES del commit: después, el search_path del tenant ya no aplica en esta
    # sesión y la consulta revienta contra Postgres real (ver core/database.py).
    aviso = await db.get(Announcement, duda.announcement_id)
    titulo = aviso.titulo if aviso else None
    await db.commit()
    return _a_lectura(duda, current_user, titulo)


@router.patch("/announcement-questions/{question_id}", response_model=QuestionRead, dependencies=puede_responder)
async def update_question(
    question_id: uuid.UUID,
    payload: QuestionUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Publica o retira la aclaración, o corrige la respuesta. Solo aplica a una duda ya respondida."""
    duda = await db.get(AnnouncementQuestion, question_id)
    if duda is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Duda no encontrada")
    if duda.estado != "respondida":
        raise HTTPException(status.HTTP_409_CONFLICT, "Primero hay que responder la duda")
    if payload.publica is not None:
        duda.publica = payload.publica
    if payload.respuesta is not None:
        duda.respuesta = payload.respuesta.strip()
        duda.respuesta_vista = False  # el residente vuelve a ver que cambió
    await db.commit()
    return _a_lectura(duda, current_user)
