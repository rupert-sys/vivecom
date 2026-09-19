import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database_base import TenantBase


class TipoAcceso(str, enum.Enum):
    residente = "residente"
    visitante = "visitante"
    proveedor = "proveedor"


class AccessLog(TenantBase):
    """
    Registro de entrada/salida (F2-01, HU-S01). Ver modelo_datos_vivecom.md.
    property_id es nullable: un proveedor puede no tener vivienda asociada
    (ej. mensajería para el condominio en general). Sin límite de
    visitantes ni restricción de horario — alcance §10.2.
    """

    __tablename__ = "access_log"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # F2-22: filtrado por property_id en GET /access-log (?property_id=).
    property_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("property.id"), nullable=True, index=True)
    tipo: Mapped[TipoAcceso] = mapped_column(Enum(TipoAcceso))
    hora_entrada: Mapped[datetime] = mapped_column(DateTime)
    hora_salida: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # F2-07/F2-11: UUID generado por la app caseta al encolar el registro
    # offline. Permite que un reintento de sincronización (mismo client_id)
    # no cree un duplicado — ver POST /access-log.
    client_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, unique=True, index=True)
    # Reglamento (Art. 17 V.1 y V.3): la bitácora de acceso debe llevar
    # nombre del conductor o peatón, número de acompañantes y una
    # identificación oficial vigente con fotografía (se devuelve a la
    # salida), y contar con autorización previa del condómino (o llamarle si
    # la visita es inesperada).
    nombre_visitante: Mapped[str | None] = mapped_column(String, nullable=True)
    acompanantes: Mapped[int] = mapped_column(Integer, default=0)
    identificacion: Mapped[str | None] = mapped_column(String, nullable=True)  # ej. "INE 1234", "Licencia"
    autorizado_por: Mapped[str | None] = mapped_column(String, nullable=True)  # residente_previo | telefono | otro
