import uuid

from datetime import time

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database_base import TenantBase


class Amenity(TenantBase):
    """Amenidad reservable (F2-16, HU-C06). Ver modelo_datos_vivecom.md."""

    __tablename__ = "amenity"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String)
    # Tiempo límite de respuesta para aprobar/rechazar una reservación de
    # esta amenidad (HU-C07): si nadie responde dentro de este plazo, se
    # rechaza automáticamente. Configurable por amenidad, no global.
    periodo_limite_horas: Mapped[int] = mapped_column(Integer)

    # Reglas propias de cada condominio para reservar esta amenidad — salen de
    # su reglamento interior (ej. Condominio Arequipa, Art. 2: 8 días de
    # anticipación, uso hasta la 01:00 am, cuota de $1,000 por el área
    # adoquinada). Los defaults reproducen el comportamiento anterior (sin
    # restricciones extra), así que una amenidad sin configurar se sigue
    # comportando igual que antes.
    dias_anticipacion_minimos: Mapped[int] = mapped_column(Integer, default=0)
    # Ventana horaria permitida (hora LOCAL del condominio, America/Mexico_City).
    # hora_fin_maxima puede ser menor que hora_inicio_permitida (o que la de
    # inicio de la reservación) para cruzar la medianoche: "hasta la 01:00 am".
    hora_inicio_permitida: Mapped[time | None] = mapped_column(Time, nullable=True)
    hora_fin_maxima: Mapped[time | None] = mapped_column(Time, nullable=True)
    # Días de la semana permitidos, 0=lunes … 6=domingo, separados por coma
    # ("0,1,2,3,4" = lunes a viernes). None = todos los días.
    dias_semana_permitidos: Mapped[str | None] = mapped_column(String, nullable=True)
    # Cuántas reservaciones pueden coexistir en el mismo horario (ej. 7 cajones
    # de estacionamiento). 1 = uso exclusivo, como antes.
    capacidad: Mapped[int] = mapped_column(Integer, default=1)
    # Cuota que el condómino paga a tesorería al solicitar el uso (0 = gratis).
    cuota: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    max_duracion_horas: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Texto libre que se le muestra al residente (referencia al artículo del reglamento).
    notas_reglamento: Mapped[str | None] = mapped_column(Text, nullable=True)


class AmenityApprover(TenantBase):
    """
    Qué miembros del comité (rol comite_aprobador) pueden aprobar
    reservaciones de esta amenidad (F2-17, HU-C07): "el administrador
    designa a uno o más miembros del comité como aprobadores".
    """

    __tablename__ = "amenity_approver"

    amenity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("amenity.id"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user_account.id"), primary_key=True)
