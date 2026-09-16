import enum
import uuid

from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database_base import TenantBase


class Rol(str, enum.Enum):
    """Roles definidos en el documento de alcance, sección 2."""

    admin = "admin"
    tesorero = "tesorero"
    comite_lectura = "comite_lectura"
    comite_aprobador = "comite_aprobador"
    vocero = "vocero"
    residente = "residente"
    guardia = "guardia"


class UserAccount(TenantBase):
    """Vive dentro del schema de cada tenant. Ver modelo_datos_vivecom.md."""

    __tablename__ = "user_account"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    resident_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String)
    rol: Mapped[Rol] = mapped_column(Enum(Rol))
    property_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
