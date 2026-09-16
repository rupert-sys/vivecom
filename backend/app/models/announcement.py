import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database_base import TenantBase


class Announcement(TenantBase):
    """
    Aviso/circular oficial (F1-30, HU-C01). Ver modelo_datos_vivecom.md.
    "Programar" un aviso (parte del alcance de F1-30) es simplemente poner
    fecha_publicacion en el futuro: no aparece en el listado para
    residentes ni se notifica hasta que esa fecha llega — no hace falta un
    campo de estado aparte para eso.
    """

    __tablename__ = "announcement"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    titulo: Mapped[str] = mapped_column(String)
    contenido: Mapped[str] = mapped_column(Text)
    fecha_publicacion: Mapped[datetime] = mapped_column(DateTime)
    # F1-32: si ya se mandó la notificación de "se publicó este aviso" por
    # WhatsApp/SMS a los residentes. Una sola vez, cuando fecha_publicacion
    # ya pasó — igual de idea que FeeCharge.confirmacion_enviada (F1-13).
    notificacion_enviada: Mapped[bool] = mapped_column(Boolean, default=False)


class ReadReceipt(TenantBase):
    """
    Confirmación de lectura por vivienda (F1-31, HU-C01: "el administrador
    puede ver qué viviendas ya leyeron cada aviso"). Se registra por
    property_id, no por resident_id — igual que el resto del modelo
    financiero, todo se ancla a la vivienda, nunca directamente a la persona.
    """

    __tablename__ = "read_receipt"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    announcement_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("announcement.id"))
    property_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("property.id"))
    leido_at: Mapped[datetime] = mapped_column(DateTime)
