import enum
import uuid

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database_base import TenantBase


class EstadoObjeto(str, enum.Enum):
    pendiente_autorizacion = "pendiente_autorizacion"
    autorizado = "autorizado"
    rechazado = "rechazado"


class LostFoundItem(TenantBase):
    """
    Objeto perdido/encontrado, moderado por el admin antes de mostrarse
    (F2-15, HU-C05). Ver modelo_datos_vivecom.md.
    """

    __tablename__ = "lost_found_item"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    publicado_por: Mapped[uuid.UUID] = mapped_column(ForeignKey("user_account.id"))
    descripcion: Mapped[str] = mapped_column(Text)
    foto_url: Mapped[str | None] = mapped_column(String, nullable=True)
    estado: Mapped[EstadoObjeto] = mapped_column(Enum(EstadoObjeto), default=EstadoObjeto.pendiente_autorizacion)
