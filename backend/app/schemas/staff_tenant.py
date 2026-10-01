"""Portal de administrador principal (staff Vivecom): listar/crear/editar condominios. Ver api/staff_tenants.py."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

# Mismo tope que la landing pública (/signup, ver schemas/signup.py) — el equipo de Vivecom crea condominios
# de 30 a 80 viviendas, no hay motivo para permitir más desde aquí que desde el propio /signup.
from app.schemas.signup import MAX_CASAS_POR_SIGNUP


class TenantListItem(BaseModel):
    tenant_id: uuid.UUID
    nombre: str
    activo: bool
    fecha_creacion: datetime
    precio_por_vivienda: float
    viviendas: int
    en_papelera: bool
    papelera_en: datetime | None


class TenantDetail(TenantListItem):
    email_admin: str | None  # None si el tenant no tiene ningún UserAccount con rol=admin todavía


class TenantUpdate(BaseModel):
    activo: bool | None = None
    nombre: str | None = Field(default=None, min_length=1, max_length=200)
    precio_por_vivienda: float | None = Field(default=None, gt=0)


class TenantCreateRequest(BaseModel):
    nombre_condominio: str = Field(min_length=1, max_length=200)
    cantidad_casas: int = Field(ge=1, le=MAX_CASAS_POR_SIGNUP)
    nombre_admin: str = Field(min_length=1, max_length=200)
    telefono_admin: str = Field(min_length=1, max_length=30)


class TenantCreateResponse(BaseModel):
    tenant_id: uuid.UUID
    nombre: str
    email_admin: str
    # casa1@dominio, casa2@dominio... para que el staff se los pase al admin recién creado (no hay canal de
    # correo real, ver alcance: solo WhatsApp+SMS) — mismo campo que ya regresa /signup.
    emails_viviendas: list[str]


class TenantDeleteRequest(BaseModel):
    # La contraseña de quien está pidiendo el borrado (el staff logueado, NO la del condominio) — confirma
    # que de verdad es él antes de una acción irreversible. Ver api/staff_tenants.py.
    password: str = Field(min_length=1)
