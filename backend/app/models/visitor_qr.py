import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database_base import TenantBase


class VisitorQR(TenantBase):
    """
    QR de acceso temporal de un solo uso (F2-02, HU-S02). Ver
    modelo_datos_vivecom.md. "Expira automáticamente al usarse" (no por
    fecha/hora): por eso no hay campo de vigencia, solo `usado`.
    """

    __tablename__ = "visitor_qr"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # Nullable: un código de proveedor que da servicio al condominio en general
    # (jardinería, mensajería) no tiene una vivienda que visitar.
    property_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("property.id"), nullable=True)
    # visitante (lo genera el residente) | proveedor (lo emite el guardia).
    tipo: Mapped[str] = mapped_column(String, default="visitante")
    descripcion: Mapped[str | None] = mapped_column(String, nullable=True)  # ej. "Jardinería López"
    codigo: Mapped[str] = mapped_column(String, unique=True)
    usado: Mapped[bool] = mapped_column(Boolean, default=False)
    fecha_generado: Mapped[datetime] = mapped_column(DateTime)
    fecha_usado: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Datos de la visita esperada (solo tipo="visitante", capturados por el residente al generar el
    # código): nullable porque un código de proveedor no los usa y un código viejo no los tiene.
    nombre_visitante: Mapped[str | None] = mapped_column(String, nullable=True)
    horario_esperado: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    numero_personas: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # JSON con todo lo anterior + vivienda/residente que lo generó + el propio código, congelado al
    # momento de generarse: es lo que la app residente codifica en la imagen del QR (en vez del código
    # pelón), para que el guardia pueda leer quién es el visitante y a quién llamar SIN conexión — la
    # validación real de "ya se usó" sigue necesitando estar en línea (ver validate_and_consume_qr).
    qr_payload: Mapped[str | None] = mapped_column(String, nullable=True)
