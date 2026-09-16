from sqlalchemy.orm import DeclarativeBase


class ControlBase(DeclarativeBase):
    """Tablas del schema de control (tenant, clabe_change_log) — no viven dentro de ningún tenant."""
    pass


class TenantBase(DeclarativeBase):
    """Tablas que se replican dentro de cada schema de tenant (user_account, property, etc.)."""
    pass
