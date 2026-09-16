import uuid
from datetime import date

from sqlalchemy import Date, Numeric, String
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
