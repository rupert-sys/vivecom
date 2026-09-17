import uuid

from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database_base import ControlBase


class Tenant(ControlBase):
    """Vive en el schema público de control. Ver modelo_datos_vivecom.md."""

    __tablename__ = "tenant"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String)
    # unique=True: la CLABE es el ÚNICO mecanismo para enrutar un depósito
    # SPEI entrante al tenant correcto (ver deposit_processing_service.py) —
    # dos tenants con la misma CLABE hacen que ese enrutamiento truene con
    # MultipleResultsFound. Bug real encontrado en F1-29 al construir la
    # prueba de punta a punta del flujo de cobro. La restricción se valida
    # también a mano en /signup y en PATCH /tenant/clabe antes de escribir,
    # porque agregar el índice único aquí no lo aplica retroactivamente a
    # una base ya existente con duplicados (mismo límite que
    # migrate_add_tables.py: solo crea tablas, no altera columnas ni
    # restricciones de tablas ya existentes).
    clabe_destino: Mapped[str] = mapped_column(String(18), unique=True)
    precio_por_vivienda: Mapped[float] = mapped_column(Numeric(10, 2), default=25.00)
    schema_name: Mapped[str] = mapped_column(String, unique=True)
