"""
F2-14: votaciones con quorum (HU-C02 crear, HU-C03 votar, HU-C04 quorum y
reactivación automática).
"""

import uuid
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.business_rules import VOTACION_QUORUM_MINIMO, VOTACION_REACTIVACION_DIAS
from app.models.poll import Poll, PollOption, Vote
from app.models.property import Property
from app.models.resident import Resident
from app.services.notification_providers.base import NotificationProvider


class VotoInvalido(Exception):
    def __init__(self, motivo: str):
        self.motivo = motivo
        super().__init__(motivo)


async def create_poll(
    db: AsyncSession, creado_por: uuid.UUID, pregunta: str, opciones: list[str], fecha_cierre: date,
    resultados_en_vivo: bool,
) -> tuple[Poll, list[PollOption]]:
    """
    Regresa también las PollOption creadas (no solo el Poll): el endpoint
    las necesita para armar la respuesta, y volver a consultarlas DESPUÉS
    de este commit revienta contra Postgres real — el search_path del
    tenant se fija con is_local=true (ver core/database.py), así que una
    consulta en la MISMA sesión después de comitear ya no lo tiene y
    "relation poll_option does not exist". Invisible en SQLite (las
    pruebas), que no distingue schemas. Se evita por completo re-consultando:
    las PollOption ya están en memoria con su id (Python-side default,
    poblado en el flush) antes de comitear.
    """
    poll = Poll(creado_por=creado_por, pregunta=pregunta, fecha_cierre=fecha_cierre, resultados_en_vivo=resultados_en_vivo)
    db.add(poll)
    await db.flush()  # para tener poll.id antes de crear las PollOption

    poll_options = [PollOption(poll_id=poll.id, texto=texto) for texto in opciones]
    db.add_all(poll_options)
    await db.flush()  # para tener cada PollOption.id en memoria antes del commit

    await db.commit()
    return poll, poll_options


async def cast_vote(db: AsyncSession, poll_id: uuid.UUID, property_id: uuid.UUID, option_id: uuid.UUID) -> Vote:
    """
    HU-C03: un voto por vivienda. Rechaza si la opción no pertenece a esta
    votación o si ya votó. El SELECT de abajo detecta el caso normal
    (secuencial), pero el que de verdad lo garantiza es el UniqueConstraint
    (poll_id, property_id) en el modelo Vote — por eso el commit va
    protegido: bajo una carrera real (dos votos de la misma vivienda casi
    simultáneos), el SELECT puede no alcanzar a ver el otro voto todavía,
    y es la base de datos la que rechaza el segundo INSERT.
    """
    opcion = await db.get(PollOption, option_id)
    if opcion is None or opcion.poll_id != poll_id:
        raise VotoInvalido("opcion_invalida")

    existente = (
        await db.execute(select(Vote).where(Vote.poll_id == poll_id, Vote.property_id == property_id))
    ).scalar_one_or_none()
    if existente is not None:
        raise VotoInvalido("ya_voto")

    voto = Vote(poll_id=poll_id, property_id=property_id, option_id=option_id)
    db.add(voto)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise VotoInvalido("ya_voto") from exc
    return voto


async def get_poll_results(db: AsyncSession, poll_id: uuid.UUID) -> list[tuple[uuid.UUID, str, int]]:
    opciones = (await db.execute(select(PollOption).where(PollOption.poll_id == poll_id))).scalars().all()
    conteo = dict(
        (await db.execute(select(Vote.option_id, func.count(Vote.id)).where(Vote.poll_id == poll_id).group_by(Vote.option_id))).all()
    )
    return [(opcion.id, opcion.texto, conteo.get(opcion.id, 0)) for opcion in opciones]


async def _telefonos_de_todos_los_residentes(db: AsyncSession) -> list[str]:
    result = await db.execute(select(Resident.telefono))
    return [telefono for telefono in result.scalars().all() if telefono]


async def process_poll_closures(db: AsyncSession, provider: NotificationProvider, hoy: date) -> dict[str, int]:
    """
    HU-C04: al llegar fecha_cierre, si la participación (votos / total de
    viviendas) alcanzó VOTACION_QUORUM_MINIMO se marca quorum_alcanzado.
    Si no, y todavía no se había reactivado una vez, se corre fecha_cierre
    VOTACION_REACTIVACION_DIAS y se avisa a todos los residentes.
    """
    total_propiedades = (await db.execute(select(func.count(Property.id)))).scalar() or 0

    candidatas = (
        await db.execute(select(Poll).where(Poll.fecha_cierre <= hoy, Poll.quorum_alcanzado.is_(False)))
    ).scalars().all()

    quorum_alcanzado = 0
    reactivadas = 0
    for poll in candidatas:
        votos = (await db.execute(select(func.count(Vote.id)).where(Vote.poll_id == poll.id))).scalar() or 0
        participacion = votos / total_propiedades if total_propiedades else 0.0

        if participacion >= VOTACION_QUORUM_MINIMO:
            poll.quorum_alcanzado = True
            quorum_alcanzado += 1
        elif not poll.reactivada:
            poll.fecha_cierre = poll.fecha_cierre + timedelta(days=VOTACION_REACTIVACION_DIAS)
            poll.reactivada = True
            reactivadas += 1
            mensaje = f'Vivecom: la votación "{poll.pregunta}" no alcanzó quorum y se reabrió una semana más. ¡Participa!'
            for telefono in await _telefonos_de_todos_los_residentes(db):
                await provider.send(telefono, mensaje)
        # si ya se había reactivado y sigue sin quorum, se queda así: una sola reactivación (alcance HU-C04).

    if candidatas:
        await db.commit()
    return {"quorum_alcanzado": quorum_alcanzado, "reactivadas": reactivadas}
