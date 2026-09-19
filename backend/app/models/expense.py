import uuid
from datetime import date

from sqlalchemy import JSON, Boolean, Date, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database_base import TenantBase


class Expense(TenantBase):
    """
    Gasto del condominio (F1-15, HU-A09). Ver modelo_datos_vivecom.md.
    comprobante_url es obligatorio (no nullable): "No se puede guardar un
    gasto sin adjuntar comprobante" — alcance §3.1. El archivo en sí se sube
    aparte (no hay infraestructura de storage todavía, ver infra/); aquí solo
    se guarda la URL resultante.
    """

    __tablename__ = "expense"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    categoria: Mapped[str] = mapped_column(String)
    monto: Mapped[float] = mapped_column(Numeric(10, 2))
    comprobante_url: Mapped[str] = mapped_column(String)
    fecha: Mapped[date] = mapped_column(Date)
    # Reglamento (Art. 8): operativo | programado | extraordinario. Los
    # programados y extraordinarios que superen el umbral del condominio
    # (Arequipa: $10,000) requieren aprobación de asamblea y al menos 3
    # cotizaciones de distintos proveedores.
    tipo: Mapped[str] = mapped_column(String, default="operativo")
    aprobado_en_asamblea: Mapped[bool] = mapped_column(Boolean, default=False)
    acta_referencia: Mapped[str | None] = mapped_column(String, nullable=True)
    # Lista de {"proveedor": str, "monto": float, "url": str}.
    cotizaciones: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # remision | factura — el reglamento pide "remisiones o facturas a nombre
    # del condominio" (Art. 8 VIII).
    tipo_comprobante: Mapped[str | None] = mapped_column(String, nullable=True)
