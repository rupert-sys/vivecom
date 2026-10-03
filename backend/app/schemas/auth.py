from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    # F0-12: checkbox "Recordarme" en el login — una sesión mucho más larga (ver
    # core/config.remembered_session_expire_minutes) en vez de guardar la contraseña.
    recordar: bool = False


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CurrentUser(BaseModel):
    user_id: str
    tenant_id: str
    schema_name: str
    rol: str
    property_id: str | None
