import enum
import uuid

from sqlalchemy import Boolean, Enum, String
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
    # Nombre/teléfono de quien usa la cuenta — solo para personal (admin, tesorero, comité, guardia); un
    # residente tiene los suyos en Resident (nombre/telefono), ligado por resident_id. Nace null en toda
    # cuenta anterior a esto: nadie los capturaba (POST /users tampoco los pide todavía).
    nombre: Mapped[str | None] = mapped_column(String, nullable=True)
    telefono: Mapped[str | None] = mapped_column(String, nullable=True)
    # Alta por /signup (F3-06 ampliado): la contraseña inicial del admin es el
    # nombre del condominio, temporal por diseño — se le pide cambiarla en su
    # primer login (ver create_access_token). Un usuario dado de alta a mano
    # (POST /users) nace en False: su contraseña la eligió quien lo creó.
    debe_cambiar_password: Mapped[bool] = mapped_column(Boolean, default=False)
    # Cuenta de vivienda creada en bloque al aprovisionar el tenant (casa<n>@dominio,
    # ver provisioning.py): nace SIN contraseña utilizable (activada=False, hash
    # centinela que ningún password real puede producir) hasta que el residente se
    # registra desde la app (POST /residents/activar) con sus propios datos y
    # contraseña. Una cuenta creada por otros caminos (POST /users, el admin de
    # /signup) nace activada=True: no hay una segunda activación que completar.
    activada: Mapped[bool] = mapped_column(Boolean, default=True)
