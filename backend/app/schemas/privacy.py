from datetime import datetime

from pydantic import BaseModel


class PrivacyNoticeRead(BaseModel):
    texto: str


class PrivacyAcceptanceRead(BaseModel):
    aviso_privacidad_aceptado_en: datetime
