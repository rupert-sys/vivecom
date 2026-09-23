import uuid

from pydantic import BaseModel, Field

# Tope de la landing de bienvenida: el endpoint es público y sin CAPTCHA (ver AVISO DE SEGURIDAD en api/signup.py)
# — sin un límite razonable, una sola llamada podría pedir crear miles de viviendas/cuentas de un golpe.
MAX_CASAS_POR_SIGNUP = 500


class TenantSignupRequest(BaseModel):
    nombre_condominio: str = Field(min_length=1, max_length=200)
    cantidad_casas: int = Field(ge=1, le=MAX_CASAS_POR_SIGNUP)
    nombre_admin: str = Field(min_length=1, max_length=200)
    telefono_admin: str = Field(min_length=1, max_length=30)


class TenantSignupResponse(BaseModel):
    tenant_id: uuid.UUID
    nombre: str
    admin_email: str
    # casa1@dominio, casa2@dominio... el panel se los muestra al admin recién registrado — es la única forma
    # que tiene de dárselos a sus residentes (no hay canal de correo, ver alcance: solo WhatsApp+SMS).
    emails_viviendas: list[str]
