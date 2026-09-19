import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text
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
    # Dudas de los residentes sobre este aviso (AnnouncementQuestion): las activa el administrador al
    # publicarlo (o el condominio por defecto, ver ReglamentoConfig.dudas_en_avisos_por_defecto) y
    # pueden tener una fecha límite. Los avisos anteriores quedan sin dudas.
    permite_dudas: Mapped[bool] = mapped_column(Boolean, default=False)
    dudas_hasta: Mapped[date | None] = mapped_column(Date, nullable=True)


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


class AnnouncementQuestion(TenantBase):
    """
    Duda de un residente sobre un aviso — un canal ACOTADO con la administración, no un chat: una
    pregunta recibe una respuesta (si quiere seguir, pregunta otra vez), y no es visible para los
    demás vecinos salvo que la administración la publique como aclaración, sin nombre ni vivienda.
    Se ancla a la vivienda, como el resto del modelo.
    """

    __tablename__ = "announcement_question"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    announcement_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("announcement.id"), index=True)
    property_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("property.id"), index=True)
    asked_by: Mapped[uuid.UUID] = mapped_column()
    texto: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    # abierta (sin responder) | respondida
    estado: Mapped[str] = mapped_column(String, default="abierta")
    respuesta: Mapped[str | None] = mapped_column(Text, nullable=True)
    respondido_por: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    respondido_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Aclaración pública: la pregunta y su respuesta se muestran a todos debajo del aviso, sin vivienda.
    publica: Mapped[bool] = mapped_column(Boolean, default=False)
    # El residente ya vio la respuesta: mientras no, la app la marca como nueva (es el aviso "dentro
    # de la app" de que ya le contestaron).
    respuesta_vista: Mapped[bool] = mapped_column(Boolean, default=False)
