import uuid
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database_base import TenantBase


class Poll(TenantBase):
    """
    Votación con quorum (F2-14, HU-C02/C03/C04). Ver modelo_datos_vivecom.md.
    reactivada es un flag de un solo uso: si no alcanza quorum, fecha_cierre
    se corre VOTACION_REACTIVACION_DIAS y se marca reactivada=True; si al
    llegar esa nueva fecha TAMPOCO alcanza quorum, se queda así — el alcance
    describe una sola reactivación, no un ciclo indefinido.
    """

    __tablename__ = "poll"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    creado_por: Mapped[uuid.UUID] = mapped_column(ForeignKey("user_account.id"))
    pregunta: Mapped[str] = mapped_column(String)
    fecha_cierre: Mapped[date] = mapped_column(Date)
    resultados_en_vivo: Mapped[bool] = mapped_column(Boolean, default=False)
    quorum_alcanzado: Mapped[bool] = mapped_column(Boolean, default=False)
    reactivada: Mapped[bool] = mapped_column(Boolean, default=False)


class PollOption(TenantBase):
    __tablename__ = "poll_option"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # F2-22: filtrado por poll_id en list_polls (F2-22, batch tras el fix de
    # N+1), get_poll_results y cast_vote — sin cubrir por ningún otro índice.
    poll_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("poll.id"), index=True)
    texto: Mapped[str] = mapped_column(String)


class Vote(TenantBase):
    """
    Un voto por vivienda por votación (HU-C03), forzado con UNIQUE(poll_id,
    property_id) — esa restricción ya deja un índice sobre (poll_id,
    property_id) con poll_id como columna izquierda, así que las consultas
    que solo filtran por poll_id (conteo de votos, quorum) ya están
    cubiertas; no hace falta un índice aparte aquí (F2-22).
    """

    __tablename__ = "vote"
    __table_args__ = (UniqueConstraint("poll_id", "property_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    poll_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("poll.id"))
    property_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("property.id"))
    option_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("poll_option.id"))
