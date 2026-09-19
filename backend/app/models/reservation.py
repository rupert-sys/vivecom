import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database_base import TenantBase


class EstadoReserva(str, enum.Enum):
    pendiente = "pendiente"
    aprobada = "aprobada"
    rechazada = "rechazada"
    expirada = "expirada"


class Reservation(TenantBase):
    """
    Reservación de una amenidad (F2-16/F2-17, HU-C06/HU-C07). Ver
    modelo_datos_vivecom.md. solicitada_en no está en esa tabla documentada,
    pero el propio documento aclara en "Notas de implementación" que los
    campos de auditoría se omitieron por brevedad y deben incluirse en
    todas las tablas — aquí además es necesario para poder calcular el
    plazo de periodo_limite_horas (HU-C07), que se cuenta desde que se
    solicitó, no desde fecha_inicio.

    `rechazada` vs `expirada`: rechazada es una decisión (de un aprobador o
    automática por vencer el periodo_limite_horas); expirada es cuando el
    bloque de tiempo reservado (fecha_inicio) ya pasó sin que nadie
    resolviera la solicitud siquiera.
    """

    __tablename__ = "reservation"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # F2-22: amenity_id se filtra en cada solicitud nueva (chequeo de
    # traslape, create_reservation) y en /amenities/{id}/availability —
    # ambos en el camino caliente de "solicitar una reservación".
    amenity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("amenity.id"), index=True)
    # property_id se filtra al listar las reservaciones propias de un residente.
    property_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("property.id"), index=True)
    fecha_inicio: Mapped[datetime] = mapped_column(DateTime)
    fecha_fin: Mapped[datetime] = mapped_column(DateTime)
    estado: Mapped[EstadoReserva] = mapped_column(Enum(EstadoReserva), default=EstadoReserva.pendiente)
    aprobador_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("user_account.id"), nullable=True)
    solicitada_en: Mapped[datetime] = mapped_column(DateTime)
    # Reglamento (Condominio Arequipa, Art. 2 VI): la cuota por uso del área
    # se entrega a tesorería al solicitar el uso — el tesorero la marca aquí.
    cuota_pagada: Mapped[bool] = mapped_column(Boolean, default=False)
    # Cuota de uso de la amenidad AL MOMENTO de solicitar (si el admin la cambia
    # después, las reservaciones ya hechas conservan la que se les cobró).
    cuota: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
