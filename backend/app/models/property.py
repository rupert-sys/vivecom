import uuid

from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database_base import TenantBase


class Property(TenantBase):
    """Una vivienda dentro del condominio. Vive en el schema del tenant."""

    __tablename__ = "property"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    identificador: Mapped[str] = mapped_column(String)  # ej. "Casa 14", "Depto 302"
    # Referencia numérica de SPEI (7 dígitos) para identificar de qué vivienda
    # es un depósito cuando todas transfieren a la misma CLABE del condominio.
    # Ver alcance F1-06: se le pide al residente que la capture al transferir.
    referencia_pago: Mapped[str] = mapped_column(String(7), unique=True)
    # Excedente cuando un depósito conciliado (ver F1-07) supera lo debido —
    # se guarda aquí y se aplica automáticamente al siguiente FeeCharge que se
    # genere para esta vivienda (ver F1-09, alcance sección "HU-A06").
    saldo_a_favor: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
