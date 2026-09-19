import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
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
