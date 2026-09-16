import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database_base import ControlBase


class ClabeChangeLog(ControlBase):
    """
    Bitácora de auditoría de cambios a la cuenta CLABE de destino de un
    tenant. Vive en el schema de control, junto a `tenant`. Ver alcance
    sección 4 (Requisitos no funcionales) y HU-A07.
    """

    __tablename__ = "clabe_change_log"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id"))
    clabe_anterior: Mapped[str] = mapped_column(String(18))
    clabe_nueva: Mapped[str] = mapped_column(String(18))
    cambiado_por: Mapped[uuid.UUID] = mapped_column()  # user_account.id (vive en otro schema, sin FK cruzada)
    fecha: Mapped[datetime] = mapped_column(DateTime)
