import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database_base import ControlBase


class UserLookup(ControlBase):
    """
    Vive en el schema de control. Como cada usuario vive dentro del schema de SU
    tenant, no hay forma de hacer 'SELECT * FROM user_account WHERE email = X'
    a través de todos los tenants de una sola vez. Esta tabla resuelve ese
    problema: se escribe (o actualiza) cada vez que se crea/borra un user_account,
    y el login la consulta primero para saber en qué schema buscar.
    """

    __tablename__ = "user_lookup"

    email: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id"))
    user_id: Mapped[uuid.UUID] = mapped_column(unique=True)
