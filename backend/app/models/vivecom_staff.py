import uuid

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database_base import ControlBase


class VivecomStaff(ControlBase):
    """
    F3-04: cuenta de un empleado de Vivecom (no de un tenant) con acceso al
    dashboard ejecutivo agregado sobre TODOS los condominios. Vive en el
    schema de control, no en el de ningún tenant — a propósito: mezclar
    esto con UserAccount (que sí vive por tenant) haría trivial que un
    admin de un condominio se auto-otorgara acceso cross-tenant. No hay
    endpoint público para crear una cuenta de este tipo (ver
    app/core/crear_staff.py) — habilitar un /staff/signup abierto sería
    el mismo tipo de hueco de control de acceso que F2-21 encontró en otro
    lado, pero mucho peor (acceso a TODOS los condominios en vez de uno).
    """

    __tablename__ = "vivecom_staff"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String)
