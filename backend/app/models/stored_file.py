import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database_base import TenantBase


class StoredFile(TenantBase):
    """
    Archivo subido a Vivecom (foto o PDF): comprobantes de gastos y de pagos. Los
    bytes viven en el almacenamiento (disco local o S3, ver file_storage.py); aquí
    solo queda quién lo subió, de qué tipo es y dónde está. Vive en el schema del
    tenant, así que un archivo nunca es visible desde otro condominio.
    """

    __tablename__ = "stored_file"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    uploaded_by: Mapped[uuid.UUID] = mapped_column()
    # gasto | pago | incidencia — decide quién puede subirlo y quién puede verlo.
    kind: Mapped[str] = mapped_column(String)
    nombre_original: Mapped[str] = mapped_column(String)
    content_type: Mapped[str] = mapped_column(String)  # detectado por los bytes, no por lo que diga el cliente
    size: Mapped[int] = mapped_column(Integer)
    storage_key: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime)
